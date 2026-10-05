import React, { useEffect, useRef, useState } from 'react';
import { MapPin, ExternalLink, AlertCircle, CheckCircle, Navigation, AlertTriangle } from 'lucide-react';
import StatusBadge from './ui/StatusBadge';

export default function InteractiveMap({
  latitude,
  longitude,
  mapUrl,
  status,
  distanceMeters,
  message,
  geocodedAddress,
  reverseAddress,
}) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const [mapReady, setMapReady] = useState(false);

  const hasCoords = (
    latitude !== null &&
    latitude !== undefined &&
    longitude !== null &&
    longitude !== undefined &&
    !isNaN(Number(latitude)) &&
    !isNaN(Number(longitude)) &&
    Number(latitude) >= -90 &&
    Number(latitude) <= 90 &&
    Number(longitude) >= -180 &&
    Number(longitude) <= 180
  );

  const numLat = Number(latitude);
  const numLon = Number(longitude);

  useEffect(() => {
    if (!hasCoords || !mapContainerRef.current) return;

    const L = window.L;
    if (!L) {
      console.warn("Leaflet (L) is not loaded on window.");
      return;
    }

    if (mapInstanceRef.current) {
      try {
        mapInstanceRef.current.remove();
      } catch {
        // Ignored
      }
      mapInstanceRef.current = null;
    }

    try {
      const map = L.map(mapContainerRef.current, {
        zoomControl: true,
        scrollWheelZoom: false,
      }).setView([numLat, numLon], 15);

      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors',
      }).addTo(map);

      const marker = L.marker([numLat, numLon]).addTo(map);
      marker.bindPopup(`
        <div style="font-size: 12px; line-height: 1.4;">
          <strong>Incident Location</strong><br/>
          Lat: ${numLat.toFixed(6)}<br/>
          Lon: ${numLon.toFixed(6)}
        </div>
      `);

      mapInstanceRef.current = map;
      setMapReady(true);
    } catch (err) {
      console.error("Failed to initialize Leaflet map:", err);
    }

    return () => {
      if (mapInstanceRef.current) {
        try {
          mapInstanceRef.current.remove();
        } catch {
          // Ignored
        }
        mapInstanceRef.current = null;
      }
    };
  }, [hasCoords, numLat, numLon]);

  const osmLink = mapUrl || (hasCoords ? `https://www.openstreetmap.org/?mlat=${numLat.toFixed(6)}&mlon=${numLon.toFixed(6)}#map=16/${numLat.toFixed(6)}/${numLon.toFixed(6)}` : null);

  const isVerified = status === 'VERIFIED';
  const isMismatch = status === 'MISMATCH' || status === 'MISMATCH_SUSPECTED';

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
      {/* Header */}
      <div className="px-5 py-3.5 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Navigation className="w-4 h-4 text-blue-600" aria-hidden="true" />
          <h4 className="text-sm font-semibold text-slate-900">
            Geographic Verification & Map
          </h4>
        </div>

        {status && <StatusBadge status={status} />}
      </div>

      <div className="p-5 space-y-4">
        {/* Verification Status Banner */}
        {isMismatch ? (
          <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-900 flex items-start gap-2.5">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" aria-hidden="true" />
            <div>
              <div className="font-semibold">Location information differs</div>
              <p className="mt-0.5 text-amber-800 leading-relaxed">
                The entered street address and supplied device coordinates do not closely correspond
                {distanceMeters !== undefined && distanceMeters !== null && ` (discrepancy: ${Math.round(distanceMeters)}m)`}.
                Please review the details before submitting. This information is preserved for administrative review.
              </p>
            </div>
          </div>
        ) : isVerified ? (
          <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-800 flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" aria-hidden="true" />
            <span>
              Location verified. Entered address corresponds to device GPS coordinates
              {distanceMeters !== undefined && distanceMeters !== null && ` (distance: ${Math.round(distanceMeters)}m)`}.
            </span>
          </div>
        ) : null}

        {/* Map Container */}
        {hasCoords ? (
          <div className="relative">
            <div
              ref={mapContainerRef}
              className="w-full h-64 rounded-lg border border-slate-200 shadow-inner z-0"
              style={{ minHeight: '260px' }}
            />
            <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
              <span className="flex items-center gap-1 font-mono">
                <MapPin className="w-3.5 h-3.5 text-slate-400" aria-hidden="true" />
                <span>{numLat.toFixed(6)}, {numLon.toFixed(6)}</span>
              </span>
              {osmLink && (
                <a
                  href={osmLink}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:text-blue-800 font-medium inline-flex items-center gap-1 hover:underline focus:outline-none focus:ring-1 focus:ring-blue-500 rounded"
                >
                  <span>View on OpenStreetMap</span>
                  <ExternalLink className="w-3 h-3" aria-hidden="true" />
                </a>
              )}
            </div>
          </div>
        ) : (
          <div className="h-44 bg-slate-50 border border-dashed border-slate-300 rounded-lg flex flex-col items-center justify-center text-xs text-slate-500">
            <MapPin className="w-6 h-6 text-slate-400 mb-2" aria-hidden="true" />
            <span>No coordinates available to render map</span>
          </div>
        )}

        {/* Informational Details */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs pt-1">
          {geocodedAddress && (
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
              <span className="font-semibold text-slate-700 block mb-0.5">Geocoded Address (from entered text):</span>
              <span className="text-slate-600">{geocodedAddress}</span>
            </div>
          )}
          {reverseAddress && (
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
              <span className="font-semibold text-slate-700 block mb-0.5">Reverse-Geocoded (from device GPS):</span>
              <span className="text-slate-600">{reverseAddress}</span>
            </div>
          )}
        </div>

        {message && !isMismatch && !isVerified && (
          <p className="text-xs text-slate-500 italic">
            {message}
          </p>
        )}

        <div className="pt-2 border-t border-slate-100 text-[11px] text-slate-400 italic">
          Geographic verification is determined through external OpenStreetMap / Nominatim geocoding and device telemetry.
        </div>
      </div>
    </div>
  );
}
