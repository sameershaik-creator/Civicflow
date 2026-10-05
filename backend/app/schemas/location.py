from typing import Optional
from pydantic import BaseModel, Field


class LocationVerificationResponse(BaseModel):
    """
    Structured response for complaint geographic verification.
    Preserves separation between telemetry, citizen-entered text, and derived geographic evidence.
    """
    location_status: str = Field(
        ...,
        description="Geographic status (VERIFIED, MISMATCH, GEOCODED, COORDINATES_ATTACHED, NO_LOCATION, GEOCODING_FAILED, REVERSE_GEOCODING_FAILED)"
    )
    latitude: Optional[float] = Field(
        None,
        description="Canonical geographic latitude used for map display and routing"
    )
    longitude: Optional[float] = Field(
        None,
        description="Canonical geographic longitude used for map display and routing"
    )
    place_id: Optional[str] = Field(
        None,
        description="OpenStreetMap / Nominatim unique place identifier"
    )
    map_url: Optional[str] = Field(
        None,
        description="Deterministic OpenStreetMap marker URL"
    )
    distance_meters: Optional[float] = Field(
        None,
        description="Geodesic distance between forward-geocoded address and device GPS coordinates in meters"
    )
    address_match: Optional[bool] = Field(
        None,
        description="True if distance <= threshold, False if discrepancy detected, None if comparison unavailable"
    )
    geocoded_address: Optional[str] = Field(
        None,
        description="Normalized display address returned by forward geocoding citizen address"
    )
    reverse_geocoded_address: Optional[str] = Field(
        None,
        description="Display address returned by reverse geocoding device GPS coordinates"
    )
    message: Optional[str] = Field(
        None,
        description="Neutral informational description for citizen and administrative review"
    )
