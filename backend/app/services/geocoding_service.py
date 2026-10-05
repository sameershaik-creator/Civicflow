"""
Geocoding & Geographic Verification Service for CivicFlow (Phase 6).

Responsibilities:
- Forward geocoding of citizen-entered addresses via OpenStreetMap / Nominatim.
- Reverse geocoding of device GPS coordinates via OpenStreetMap / Nominatim.
- Geodesic distance calculation via the Haversine formula.
- Mismatch detection between reported address and physical device coordinates.
- Generation of deterministic OpenStreetMap marker URLs.
- Location status evaluation for human administrative review.
"""

import math
import logging
from typing import Optional, Dict, Any, Tuple
import httpx

from app.config import settings
from app.models.complaint import LocationStatus

logger = logging.getLogger("civicflow.services.geocoding")

# Radius of Earth in meters for Haversine calculation
EARTH_RADIUS_METERS = 6371000.0


# ---------------------------------------------------------------------------
# Custom Exceptions for Safe Diagnostic Classification
# ---------------------------------------------------------------------------

class GeocodingException(Exception):
    """Base exception for geographic operations."""
    pass


class InvalidCoordinatesError(GeocodingException):
    """Raised when coordinates fall outside valid latitude/longitude ranges."""
    pass


class GeocodingServiceError(GeocodingException):
    """Raised when external geocoding service encounters HTTP or network failure."""
    pass


class GeocodingTimeoutError(GeocodingServiceError):
    """Raised when external geocoding service times out."""
    pass


# ---------------------------------------------------------------------------
# Coordinate Validation & Mathematical Functions
# ---------------------------------------------------------------------------

def validate_coordinates(latitude: Optional[float], longitude: Optional[float]) -> bool:
    """
    Validates whether latitude and longitude are valid numeric geographic coordinates.
    - Latitude must be between -90 and 90 degrees.
    - Longitude must be between -180 and 180 degrees.
    - Neither may be NaN or infinite.
    """
    if latitude is None or longitude is None:
        return False

    try:
        lat = float(latitude)
        lon = float(longitude)
    except (ValueError, TypeError):
        return False

    if math.isnan(lat) or math.isinf(lat) or math.isnan(lon) or math.isinf(lon):
        return False

    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0


def calculate_haversine_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float
) -> float:
    """
    Calculates the geodesic distance between two points on the Earth's surface
    in meters using the Haversine formula.
    """
    if not validate_coordinates(lat1, lon1) or not validate_coordinates(lat2, lon2):
        raise InvalidCoordinatesError(
            f"Invalid coordinate pairs provided for distance calculation: ({lat1}, {lon1}), ({lat2}, {lon2})"
        )

    # Convert decimal degrees to radians
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    # Haversine formula
    a = (
        math.sin(delta_phi / 2.0) ** 2 +
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    # Clamp 'a' to [0, 1] to avoid domain error in sqrt due to floating point imprecision
    a = min(1.0, max(0.0, a))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    distance = EARTH_RADIUS_METERS * c
    return round(distance, 2)


def build_map_url(latitude: float, longitude: float, zoom: int = 16) -> str:
    """
    Constructs a deterministic OpenStreetMap marker URL for the canonical coordinates.
    """
    if not validate_coordinates(latitude, longitude):
        raise InvalidCoordinatesError(f"Cannot generate map URL for invalid coordinates: {latitude}, {longitude}")

    return f"https://www.openstreetmap.org/?mlat={latitude:.6f}&mlon={longitude:.6f}#map={zoom}/{latitude:.6f}/{longitude:.6f}"


# ---------------------------------------------------------------------------
# External Nominatim Geocoding Client
# ---------------------------------------------------------------------------

def forward_geocode(
    address: str,
    base_url: Optional[str] = None,
    user_agent: Optional[str] = None,
    timeout: Optional[float] = None
) -> Optional[Dict[str, Any]]:
    """
    Resolves a street address or descriptive locality into geographic coordinates
    using the configured OpenStreetMap / Nominatim service.
    """
    if not address or not address.strip():
        return None

    cleaned_address = address.strip()
    api_url = (base_url or settings.GEOCODING_BASE_URL).rstrip("/") + "/search"
    headers = {
        "User-Agent": user_agent or settings.GEOCODING_USER_AGENT,
        "Accept": "application/json",
    }
    params = {
        "q": cleaned_address,
        "format": "jsonv2",
        "limit": 1,
        "addressdetails": 1,
    }
    req_timeout = timeout if timeout is not None else float(settings.GEOCODING_TIMEOUT_SECONDS)

    logger.info("Forward geocoding address via Nominatim: '%s'", cleaned_address)

    try:
        with httpx.Client(timeout=req_timeout) as client:
            response = client.get(api_url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

            if not data or not isinstance(data, list) or len(data) == 0:
                logger.info("Nominatim forward geocoding returned zero matches for '%s'", cleaned_address)
                return None

            first_match = data[0]
            lat = float(first_match.get("lat"))
            lon = float(first_match.get("lon"))
            display_name = first_match.get("display_name", "")
            place_id = str(first_match.get("place_id", ""))

            if not validate_coordinates(lat, lon):
                logger.warning("Nominatim returned coordinates out of bounds: %s, %s", lat, lon)
                return None

            return {
                "latitude": lat,
                "longitude": lon,
                "display_name": display_name,
                "place_id": place_id,
                "raw": first_match
            }
    except httpx.TimeoutException as exc:
        logger.warning("Nominatim forward geocode request timed out after %ss: %s", req_timeout, exc)
        return None
    except httpx.HTTPStatusError as exc:
        logger.warning("Nominatim forward geocode returned HTTP %s: %s", exc.response.status_code, exc)
        return None
    except Exception as exc:
        logger.warning("Nominatim forward geocode encountered unexpected error: %s: %s", type(exc).__name__, exc)
        return None


def reverse_geocode(
    latitude: float,
    longitude: float,
    base_url: Optional[str] = None,
    user_agent: Optional[str] = None,
    timeout: Optional[float] = None
) -> Optional[Dict[str, Any]]:
    """
    Resolves geographic coordinates into a human-readable address and place description
    using OpenStreetMap / Nominatim reverse geocoding.
    """
    if not validate_coordinates(latitude, longitude):
        logger.warning("Cannot reverse geocode invalid coordinates: %s, %s", latitude, longitude)
        return None

    api_url = (base_url or settings.GEOCODING_BASE_URL).rstrip("/") + "/reverse"
    headers = {
        "User-Agent": user_agent or settings.GEOCODING_USER_AGENT,
        "Accept": "application/json",
    }
    params = {
        "lat": f"{latitude:.6f}",
        "lon": f"{longitude:.6f}",
        "format": "jsonv2",
        "addressdetails": 1,
    }
    req_timeout = timeout if timeout is not None else float(settings.GEOCODING_TIMEOUT_SECONDS)

    logger.info("Reverse geocoding coordinates via Nominatim: (%f, %f)", latitude, longitude)

    try:
        with httpx.Client(timeout=req_timeout) as client:
            response = client.get(api_url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

            if not data or not isinstance(data, dict):
                logger.info("Nominatim reverse geocode returned empty data for (%f, %f)", latitude, longitude)
                return None

            if "error" in data:
                logger.info("Nominatim reverse geocode error response: %s", data.get("error"))
                return None

            display_name = data.get("display_name", "")
            place_id = str(data.get("place_id", ""))
            address_details = data.get("address", {})

            return {
                "latitude": latitude,
                "longitude": longitude,
                "display_name": display_name,
                "place_id": place_id,
                "address_details": address_details,
                "raw": data
            }
    except httpx.TimeoutException as exc:
        logger.warning("Nominatim reverse geocode request timed out after %ss: %s", req_timeout, exc)
        return None
    except httpx.HTTPStatusError as exc:
        logger.warning("Nominatim reverse geocode returned HTTP %s: %s", exc.response.status_code, exc)
        return None
    except Exception as exc:
        logger.warning("Nominatim reverse geocode encountered unexpected error: %s: %s", type(exc).__name__, exc)
        return None


# ---------------------------------------------------------------------------
# High-Level Verification Orchestrator
# ---------------------------------------------------------------------------

def verify_complaint_location(
    original_address: Optional[str] = None,
    original_latitude: Optional[float] = None,
    original_longitude: Optional[float] = None,
    threshold_meters: Optional[float] = None
) -> Dict[str, Any]:
    """
    Executes the comprehensive geographic verification pipeline for a complaint:
    1. Distinguishes raw device telemetry from citizen-typed text.
    2. Performs forward geocoding on address (if supplied).
    3. Performs reverse geocoding on coordinates (if supplied).
    4. Evaluates geodesic discrepancy if both exist against threshold.
    5. Returns canonical coordinates and verification results for persistence.
    """
    has_gps = validate_coordinates(original_latitude, original_longitude)
    has_address = bool(original_address and original_address.strip())
    threshold = threshold_meters if threshold_meters is not None else float(settings.LOCATION_MISMATCH_THRESHOLD_METERS)

    # Case 4: Neither address nor GPS was provided
    if not has_gps and not has_address:
        return {
            "location_status": LocationStatus.NO_LOCATION.value,
            "latitude": None,
            "longitude": None,
            "place_id": None,
            "map_url": None,
            "distance_meters": None,
            "address_match": None,
            "geocoded_address": None,
            "reverse_geocoded_address": None,
            "message": "No geographic coordinates or street address were supplied with this complaint."
        }

    # Case 2: Address only (no GPS telemetry)
    if not has_gps and has_address:
        fwd_res = forward_geocode(original_address)
        if fwd_res:
            canonical_lat = fwd_res["latitude"]
            canonical_lon = fwd_res["longitude"]
            place_id = fwd_res.get("place_id")
            map_url = build_map_url(canonical_lat, canonical_lon)
            return {
                "location_status": LocationStatus.GEOCODED.value,
                "latitude": canonical_lat,
                "longitude": canonical_lon,
                "place_id": place_id,
                "map_url": map_url,
                "distance_meters": None,
                "address_match": None,
                "geocoded_address": fwd_res.get("display_name"),
                "reverse_geocoded_address": None,
                "message": "Location resolved via forward geocoding of the citizen-provided address."
            }
        else:
            return {
                "location_status": LocationStatus.GEOCODING_FAILED.value,
                "latitude": None,
                "longitude": None,
                "place_id": None,
                "map_url": None,
                "distance_meters": None,
                "address_match": None,
                "geocoded_address": None,
                "reverse_geocoded_address": None,
                "message": "The citizen-provided address could not be resolved by the geocoding service."
            }

    # Case 3: GPS only (no citizen-entered address)
    if has_gps and not has_address:
        canonical_lat = float(original_latitude)
        canonical_lon = float(original_longitude)
        map_url = build_map_url(canonical_lat, canonical_lon)
        rev_res = reverse_geocode(canonical_lat, canonical_lon)

        place_id = rev_res.get("place_id") if rev_res else None
        rev_address = rev_res.get("display_name") if rev_res else None
        status_val = (
            LocationStatus.COORDINATES_ATTACHED.value
            if rev_res is None
            else LocationStatus.REVERSE_GEOCODED.value
        )

        return {
            "location_status": status_val,
            "latitude": canonical_lat,
            "longitude": canonical_lon,
            "place_id": place_id,
            "map_url": map_url,
            "distance_meters": None,
            "address_match": None,
            "geocoded_address": None,
            "reverse_geocoded_address": rev_address,
            "message": "Location established from device GPS telemetry."
        }

    # Case 1: Both GPS telemetry and citizen address are provided
    canonical_lat = float(original_latitude)
    canonical_lon = float(original_longitude)
    map_url = build_map_url(canonical_lat, canonical_lon)

    # 1. Forward geocode the address
    fwd_res = forward_geocode(original_address)

    # 2. Reverse geocode the device GPS
    rev_res = reverse_geocode(canonical_lat, canonical_lon)

    geocoded_addr = fwd_res.get("display_name") if fwd_res else None
    rev_addr = rev_res.get("display_name") if rev_res else None
    place_id = (rev_res.get("place_id") if rev_res else None) or (fwd_res.get("place_id") if fwd_res else None)

    if not fwd_res:
        # Address couldn't be forward geocoded, but GPS is valid
        return {
            "location_status": LocationStatus.COORDINATES_ATTACHED.value,
            "latitude": canonical_lat,
            "longitude": canonical_lon,
            "place_id": place_id,
            "map_url": map_url,
            "distance_meters": None,
            "address_match": None,
            "geocoded_address": None,
            "reverse_geocoded_address": rev_addr,
            "message": "Device GPS recorded, but the entered address could not be resolved by geocoding."
        }

    # 3. Calculate Haversine distance between geocoded address and device GPS
    distance = calculate_haversine_distance(
        canonical_lat, canonical_lon,
        fwd_res["latitude"], fwd_res["longitude"]
    )

    if distance <= threshold:
        location_status = LocationStatus.VERIFIED.value
        address_match = True
        message = (
            f"Location verified. Entered address corresponds to device GPS coordinates "
            f"(distance: {int(distance)}m, within {int(threshold)}m threshold)."
        )
    else:
        # Detected significant discrepancy between entered address and device coordinates
        location_status = LocationStatus.MISMATCH.value
        address_match = False
        message = (
            f"The citizen-entered address and supplied device coordinates do not closely correspond "
            f"(discrepancy: {int(distance)}m exceeds {int(threshold)}m threshold) and require human review."
        )

    return {
        "location_status": location_status,
        "latitude": canonical_lat,
        "longitude": canonical_lon,
        "place_id": place_id,
        "map_url": map_url,
        "distance_meters": distance,
        "address_match": address_match,
        "geocoded_address": geocoded_addr,
        "reverse_geocoded_address": rev_addr,
        "message": message
    }
