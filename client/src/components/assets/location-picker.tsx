"use client";

import "leaflet/dist/leaflet.css";
import { useEffect, useState } from "react";
import L from "leaflet";
import { MapContainer, TileLayer, Marker, useMap, useMapEvents } from "react-leaflet";

// Leaflet's default marker icons resolve relative to the webpack bundle path and
// 404 under Next.js unless pointed at real URLs explicitly.
delete (L.Icon.Default.prototype as unknown as { _getIconUrl?: unknown })._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

export interface LocationValue {
  address: string;
  lat: number | null;
  lng: number | null;
}

interface LocationPickerProps {
  value: LocationValue;
  onChange: (value: LocationValue) => void;
}

interface NominatimResult {
  display_name: string;
  lat: string;
  lon: string;
}

const DEFAULT_CENTER: [number, number] = [20, 0];

function ClickToPlace({ onPick }: { onPick: (lat: number, lng: number) => void }) {
  useMapEvents({
    click(e) {
      onPick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

// react-leaflet's `center` prop only applies on mount — typing coordinates or
// picking a search result otherwise never moves the already-rendered map.
function RecenterMap({ lat, lng }: { lat: number; lng: number }) {
  const map = useMap();
  useEffect(() => {
    map.setView([lat, lng], Math.max(map.getZoom(), 14));
  }, [lat, lng, map]);
  return null;
}

export default function LocationPicker({ value, onChange }: LocationPickerProps) {
  const [query, setQuery] = useState(value.address || "");
  const [results, setResults] = useState<NominatimResult[]>([]);
  const [searching, setSearching] = useState(false);

  const hasPin = value.lat != null && value.lng != null;
  const center: [number, number] = hasPin ? [value.lat as number, value.lng as number] : DEFAULT_CENTER;

  // OpenStreetMap's free Nominatim geocoder — no API key, fair-use rate limited.
  const search = async () => {
    if (!query.trim()) return;
    setSearching(true);
    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&limit=5&q=${encodeURIComponent(query)}`
      );
      setResults(await res.json());
    } catch {
      setResults([]);
    } finally {
      setSearching(false);
    }
  };

  const pick = (lat: number, lng: number, address?: string) => {
    onChange({ address: address ?? value.address, lat, lng });
    setResults([]);
  };

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), search())}
          placeholder="Search an address (OpenStreetMap)"
          className="flex-1 bg-secondary/50 border border-border/50 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary/40"
        />
        <button
          type="button"
          onClick={search}
          disabled={searching}
          className="px-3 py-2 text-xs text-foreground border border-border/50 rounded-lg hover:border-primary/40 disabled:opacity-40"
        >
          {searching ? "..." : "Search"}
        </button>
      </div>

      {results.length > 0 && (
        <ul className="border border-border/50 rounded-lg divide-y divide-border/40 overflow-hidden">
          {results.map((r, i) => (
            <li key={i}>
              <button
                type="button"
                onClick={() => {
                  setQuery(r.display_name);
                  pick(parseFloat(r.lat), parseFloat(r.lon), r.display_name);
                }}
                className="w-full text-left px-3 py-2 text-xs hover:bg-secondary/50 transition-colors"
              >
                {r.display_name}
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* Coordinates are the value of record — address is a convenience for
          finding them. Editable directly for surveys/deeds that already give
          precise lat/lng, rather than relying only on geocoded search. */}
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-[11px] text-muted-foreground uppercase tracking-wider block mb-1">Latitude</label>
          <input
            type="number"
            step="any"
            required
            value={value.lat ?? ""}
            onChange={(e) => onChange({ ...value, lat: e.target.value === "" ? null : Number(e.target.value) })}
            placeholder="25.20480"
            className="w-full bg-secondary/50 border border-border/50 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:border-primary/40"
          />
        </div>
        <div>
          <label className="text-[11px] text-muted-foreground uppercase tracking-wider block mb-1">Longitude</label>
          <input
            type="number"
            step="any"
            required
            value={value.lng ?? ""}
            onChange={(e) => onChange({ ...value, lng: e.target.value === "" ? null : Number(e.target.value) })}
            placeholder="55.27080"
            className="w-full bg-secondary/50 border border-border/50 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:border-primary/40"
          />
        </div>
      </div>

      <div className="rounded-lg overflow-hidden border border-border/50 h-56">
        <MapContainer center={center} zoom={hasPin ? 15 : 2} className="h-full w-full" scrollWheelZoom>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {hasPin && <Marker position={center} />}
          {hasPin && <RecenterMap lat={value.lat as number} lng={value.lng as number} />}
          <ClickToPlace onPick={(lat, lng) => pick(lat, lng)} />
        </MapContainer>
      </div>
      <p className="text-[11px] text-muted-foreground">
        {hasPin
          ? "Search, click the map, or type coordinates directly — all three stay in sync."
          : "Search an address, click the map, or enter coordinates to drop a pin."}
      </p>
    </div>
  );
}
