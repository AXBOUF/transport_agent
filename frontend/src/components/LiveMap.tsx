import { useEffect, useMemo, useRef, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap, GeoJSON } from "react-leaflet";
import L from "leaflet";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Locate, Navigation, MapIcon, Search, Loader2, X, TrainFront } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";

type ThemeKey = "light" | "dark" | "satellite" | "terrain" | "voyager" | "watercolor";

const THEMES: Record<ThemeKey, { name: string; url: string; attribution: string; swatch: string }> = {
  light: {
    name: "Light",
    url: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
    attribution: "© OpenStreetMap © CARTO",
    swatch: "linear-gradient(135deg,#f8fafc,#e2e8f0)",
  },
  dark: {
    name: "Dark",
    url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    attribution: "© OpenStreetMap © CARTO",
    swatch: "linear-gradient(135deg,#0f172a,#1e293b)",
  },
  satellite: {
    name: "Satellite",
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attribution: "Tiles © Esri",
    swatch: "linear-gradient(135deg,#1a3d2e,#3a6b4f)",
  },
  terrain: {
    name: "Terrain",
    url: "https://tile.opentopomap.org/{z}/{x}/{y}.png",
    attribution: "© OpenTopoMap (CC-BY-SA)",
    swatch: "linear-gradient(135deg,#d6c8a3,#8a9a5b)",
  },
  voyager: {
    name: "Voyager",
    url: "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
    attribution: "© OpenStreetMap © CARTO",
    swatch: "linear-gradient(135deg,#fef3c7,#fcd34d)",
  },
  watercolor: {
    name: "Watercolor",
    url: "https://tiles.stadiamaps.com/tiles/stamen_watercolor/{z}/{x}/{y}.jpg",
    attribution: "© Stadia Maps © Stamen © OSM",
    swatch: "linear-gradient(135deg,#fda4af,#a78bfa)",
  },
};

function FlyTo({ position }: { position: [number, number] | null }) {
  const map = useMap();
  useEffect(() => {
    if (position) map.flyTo(position, 15, { duration: 1.5 });
  }, [position, map]);
  return null;
}

function FlyToSearch({ target }: { target: { lat: number; lng: number; zoom?: number } | null }) {
  const map = useMap();
  useEffect(() => {
    if (target) map.flyTo([target.lat, target.lng], target.zoom ?? 16, { duration: 1.5 });
  }, [target, map]);
  return null;
}

export type SelectedTrain = {
  id: string;
  label: string;
  color: string;
  routeLong: string;
  routeDesc: string;
  destination: string;
  status: string;
  occupancy: number; // 0..8
  lastStop: string;
  platform: string;
  carriages: string;
  precededBy?: { runNumber: string; label: string; origin: string };
  continuesAs?: { runNumber: string; label: string; via: string; destination: string };
  alerts: string[];
  stops: {
    name: string;
    platform: string;
    runNumber: string;
    time: string;
    status: "departed" | "current" | "upcoming";
    occupancy: number;
    note?: "pick up only" | "drop off only";
    interchanges?: { label: string; color: string }[];
  }[];
};

const STATIONS_BY_LINE: Record<string, string[]> = {
  T1: ["Central", "Strathfield", "Epping", "Hornsby", "Berowra", "Richmond"],
  T2: ["Central", "Redfern", "Sydenham", "Wolli Creek", "Hurstville", "Leppington"],
  T3: ["City Circle", "Redfern", "Burwood", "Strathfield", "Lidcombe", "Regents Park", "Sefton", "Liverpool"],
  T4: ["Bondi Junction", "Town Hall", "Central", "Sydenham", "Hurstville", "Sutherland", "Cronulla"],
  T5: ["Leppington", "Glenfield", "Liverpool", "Cabramatta", "Merrylands", "Richmond"],
  T6: ["Lidcombe", "Berala", "Regents Park", "Sefton", "Chester Hill", "Leightonfield"],
  T7: ["Olympic Park", "Lidcombe", "Strathfield", "Central"],
  T8: ["Central", "Sydenham", "Wolli Creek", "Sydney Airport", "Revesby", "Macarthur"],
  T9: ["Hornsby", "Strathfield", "Burwood", "Redfern", "Central", "Gordon"],
  M1: ["Tallawong", "Rouse Hill", "Norwest", "Chatswood", "North Sydney", "Barangaroo", "Martin Place", "Sydenham"],
};

function pickRandom<T>(arr: T[]) {
  return arr[Math.floor(Math.random() * arr.length)];
}

const LINE_COLORS: Record<string, string> = {
  T1: "#F99D1C", T2: "#0098CD", T3: "#F37021", T4: "#005AA3", T5: "#C4258F",
  T6: "#7D3F1A", T7: "#6F818E", T8: "#00954C", T9: "#D11F2F", M1: "#168388",
};

function fmtTime(d: Date) {
  let h = d.getHours();
  const m = d.getMinutes();
  const ampm = h >= 12 ? "pm" : "am";
  h = h % 12 || 12;
  return `${h}:${m.toString().padStart(2, "0")} ${ampm}`;
}

function buildMockTrain(label: string, color: string, routeLong: string, routeDesc: string): SelectedTrain {
  const stations = STATIONS_BY_LINE[label] ?? ["Central", "Town Hall", "Wynyard"];
  const currentIdx = Math.max(0, Math.floor(Math.random() * Math.max(1, stations.length - 2)));
  const destination = stations[stations.length - 1];
  const baseRun = 2000000 + Math.floor(Math.random() * 99999);
  const start = new Date();
  start.setMinutes(start.getMinutes() + 2);
  const stops = stations.map((name, i) => {
    const t = new Date(start.getTime() + i * (2 + Math.floor(Math.random() * 3)) * 60_000);
    const status: "departed" | "current" | "upcoming" =
      i < currentIdx ? "departed" : i === currentIdx ? "current" : "upcoming";
    const interchanges: { label: string; color: string }[] = [];
    if (i === 0 || name === "Central" || name === "Strathfield") {
      // mock a couple of interchange dots
      const others = Object.keys(LINE_COLORS).filter((k) => k !== label);
      for (let j = 0; j < 1 + Math.floor(Math.random() * 2); j++) {
        const k = others[Math.floor(Math.random() * others.length)];
        interchanges.push({ label: k, color: LINE_COLORS[k] });
      }
    }
    return {
      name,
      platform: String(1 + Math.floor(Math.random() * 8)),
      runNumber: String(baseRun + i * 137),
      time: fmtTime(t),
      status,
      occupancy: 1 + Math.floor(Math.random() * 8),
      note:
        i === 0 ? ("pick up only" as const)
        : i === stations.length - 1 ? ("drop off only" as const)
        : undefined,
      interchanges,
    };
  });
  const lastStop = stops[currentIdx]?.name ?? stations[0];
  const statuses = ["On time", "1m early", "2m late", "On time", "On time"];
  // preceded by / continues as – pick another line
  const otherLines = Object.keys(LINE_COLORS).filter((k) => k !== label);
  const prec = pickRandom(otherLines);
  const cont = pickRandom(otherLines);
  return {
    id: `${label}-${Math.random().toString(36).slice(2, 7)}`,
    label,
    color,
    routeLong,
    routeDesc,
    destination,
    status: pickRandom(statuses),
    occupancy: 2 + Math.floor(Math.random() * 6),
    lastStop,
    platform: stops[currentIdx]?.platform ?? "1",
    carriages: pickRandom(["8 car Waratah Series 2 (A)", "8 car Waratah Series 2 (B)", "8 car Mariyung", "6 car Metro"]),
    precededBy: { runNumber: String(baseRun - 200), label: prec, origin: "Central" },
    continuesAs: { runNumber: String(baseRun + 600), label: cont, via: "Strathfield", destination: "Central" },
    alerts: [
      `Trains run between ${stations[0]} or ${stations[Math.min(2, stations.length - 1)]} and ${destination}`,
      "+3 more alerts this week",
    ],
    stops,
  };
}

function OccupancyBars({ value, max = 8 }: { value: number; max?: number }) {
  return (
    <div className="flex gap-0.5">
      {Array.from({ length: max }).map((_, i) => {
        const filled = i < value;
        const color =
          value <= 3 ? "bg-emerald-500" : value <= 5 ? "bg-amber-500" : "bg-orange-500";
        return (
          <div
            key={i}
            className={`h-4 w-3 rounded-sm text-center text-[9px] font-bold leading-4 text-white ${
              filled ? color : "bg-muted"
            }`}
          >
            {max - i}
          </div>
        );
      })}
    </div>
  );
}

function SimulatedTrains({
  data,
  onSelect,
}: {
  data: any | null;
  onSelect: (t: SelectedTrain) => void;
}) {
  const map = useMap();
  useEffect(() => {
    if (!data) return;
    const markers: L.Marker[] = [];
    const trains: Array<{
      marker: L.Marker;
      coords: [number, number][]; // [lat, lng]
      cum: number[]; // cumulative distance per vertex
      total: number;
      speed: number; // units per ms (deg)
      offset: number; // start offset distance
      startedAt: number;
      direction: 1 | -1;
    }> = [];

    const makeIcon = (label: string, color: string) =>
      L.divIcon({
        className: "",
        html: `<div class="train-dot train-dot-clickable" style="--c:${color}"><span>${label}</span></div>`,
        iconSize: [34, 22],
        iconAnchor: [17, 11],
      });

    (data.features || []).forEach((f: any) => {
      const p = f.properties || {};
      const label = String(p.route_short_name ?? "").toUpperCase();
      if (!label) return;
      const color = `#${p.route_color ?? "888888"}`;
      const geom = f.geometry;
      const lineStrings: [number, number][][] = [];
      if (geom?.type === "LineString") {
        lineStrings.push(geom.coordinates.map((c: number[]) => [c[1], c[0]]));
      } else if (geom?.type === "MultiLineString") {
        geom.coordinates.forEach((ls: number[][]) =>
          lineStrings.push(ls.map((c) => [c[1], c[0]]))
        );
      }
      // 1-2 trains per line segment, depending on length
      const routeLong = String(p.route_long_name ?? "");
      const routeDesc = String(p.route_desc ?? "");
      lineStrings.forEach((coords) => {
        if (coords.length < 2) return;
        const cum: number[] = [0];
        for (let i = 1; i < coords.length; i++) {
          const dx = coords[i][0] - coords[i - 1][0];
          const dy = coords[i][1] - coords[i - 1][1];
          cum.push(cum[i - 1] + Math.hypot(dx, dy));
        }
        const total = cum[cum.length - 1];
        if (total === 0) return;
        const count = total > 0.05 ? 2 : 1;
        for (let i = 0; i < count; i++) {
          const train = buildMockTrain(label, color, routeLong, routeDesc);
          const marker = L.marker(coords[0], {
            icon: makeIcon(label, color),
            interactive: true,
            keyboard: false,
            riseOnHover: true,
            bubblingMouseEvents: false,
          });
          marker.bindTooltip(
            `<div style="font:600 11px system-ui;color:#fff;background:${color};padding:4px 8px;border-radius:6px">${label} → ${train.destination}<br/><span style="font-weight:400;opacity:0.9">${train.status} • ${train.lastStop}</span></div>`,
            { direction: "top", offset: [0, -8], opacity: 1, className: "train-tooltip" }
          );
          markers.push(marker);
          marker.addTo(map);
          // Attach DOM-level click directly to the marker icon — fast-moving
          // leaflet markers can drop the synthetic "click" event, so we listen
          // on the actual element.
          const select = () => {
            console.log("[train] select", train.label, train.id);
            onSelect(train);
          };
          marker.on("click", (e: any) => {
            L.DomEvent.stopPropagation(e);
            select();
          });
          const el = marker.getElement();
          if (el) {
            L.DomEvent.disableClickPropagation(el);
            el.addEventListener("click", (ev) => { ev.stopPropagation(); select(); });
            el.addEventListener("mouseenter", () => {
              (marker as any)._paused = true;
            });
            el.addEventListener("mouseleave", () => {
              (marker as any)._paused = false;
              const tr = trains.find((t) => t.marker === marker) as any;
              if (tr) tr.startedAt = performance.now() - (tr._lastElapsed ?? 0);
            });
          }
          trains.push({
            marker,
            coords,
            cum,
            total,
            // much slower — ~deg/ms; tuned for a calm, "live" feel
            speed: 0.0000035 + Math.random() * 0.0000015,
            offset: (total / count) * i + Math.random() * (total / count),
            startedAt: performance.now(),
            direction: 1,
          });
        }
      });
    });

    let raf = 0;
    const tick = (now: number) => {
      trains.forEach((t) => {
        if ((t.marker as any)._paused) {
          (t as any)._lastElapsed = now - t.startedAt;
          return;
        }
        const elapsed = now - t.startedAt;
        // continuous loop — train runs end-to-end, then teleports back to start
        const d = (t.offset + elapsed * t.speed) % t.total;
        // find segment via cum
        let idx = 1;
        while (idx < t.cum.length && t.cum[idx] < d) idx++;
        const a = t.coords[idx - 1];
        const b = t.coords[Math.min(idx, t.coords.length - 1)];
        const segLen = (t.cum[idx] ?? t.total) - t.cum[idx - 1];
        const tt = segLen > 0 ? (d - t.cum[idx - 1]) / segLen : 0;
        const lat = a[0] + (b[0] - a[0]) * tt;
        const lng = a[1] + (b[1] - a[1]) * tt;
        t.marker.setLatLng([lat, lng]);
      });
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(raf);
      markers.forEach((m) => m.remove());
    };
  }, [data, map]);
  return null;
}

type SearchResult = {
  place_id: number;
  display_name: string;
  lat: string;
  lon: string;
  type?: string;
};

const liveIcon = L.divIcon({
  className: "",
  html: `<div class="live-pulse"></div>`,
  iconSize: [18, 18],
  iconAnchor: [9, 9],
});

export default function LiveMap() {
  const [theme, setTheme] = useState<ThemeKey>("voyager");
  const [position, setPosition] = useState<[number, number] | null>(null);
  const [accuracy, setAccuracy] = useState<number | null>(null);
  const [tracking, setTracking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const watchId = useRef<number | null>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchTarget, setSearchTarget] = useState<{ lat: number; lng: number; zoom?: number } | null>(null);
  const [selectedMarker, setSelectedMarker] = useState<{ lat: number; lng: number; label: string } | null>(null);
  const [trainsData, setTrainsData] = useState<any | null>(null);
  const ALLOWED_LINES = useMemo(
    () => new Set(["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "M1"]),
    []
  );
  const [showTrains, setShowTrains] = useState(true);
  const [selectedTrain, setSelectedTrain] = useState<SelectedTrain | null>(null);

  useEffect(() => {
    fetch("/data/sydneytrains.geojson")
      .then((r) => r.json())
      .then((data) => {
        const filtered = {
          ...data,
          features: (data.features || []).filter((f: any) =>
            ALLOWED_LINES.has(String(f?.properties?.route_short_name ?? "").toUpperCase())
          ),
        };
        setTrainsData(filtered);
      })
      .catch(() => {});
  }, [ALLOWED_LINES]);

  const runSearch = async (q: string) => {
    if (!q.trim()) return;
    setSearching(true);
    try {
      // Sydney viewbox: left,top,right,bottom
      const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
        q
      )}&limit=8&viewbox=150.5,-33.4,151.5,-34.2&bounded=1`;
      const res = await fetch(url, { headers: { Accept: "application/json" } });
      const data: SearchResult[] = await res.json();
      setResults(data);
      if (data.length > 0) {
        const first = data[0];
        const lat = parseFloat(first.lat);
        const lng = parseFloat(first.lon);
        setSearchTarget({ lat, lng, zoom: 16 });
        setSelectedMarker({ lat, lng, label: first.display_name });
      }
    } catch (e) {
      setError("Search failed");
    } finally {
      setSearching(false);
    }
  };

  const pickResult = (r: SearchResult) => {
    const lat = parseFloat(r.lat);
    const lng = parseFloat(r.lon);
    setSearchTarget({ lat, lng, zoom: 17 });
    setSelectedMarker({ lat, lng, label: r.display_name });
    setResults([]);
  };

  const startTracking = () => {
    if (!("geolocation" in navigator)) {
      setError("Geolocation not supported");
      return;
    }
    setError(null);
    setTracking(true);
    watchId.current = navigator.geolocation.watchPosition(
      (pos) => {
        setPosition([pos.coords.latitude, pos.coords.longitude]);
        setAccuracy(pos.coords.accuracy);
      },
      (err) => {
        setError(err.message);
        setTracking(false);
      },
      { enableHighAccuracy: true, maximumAge: 1000 }
    );
  };

  const stopTracking = () => {
    if (watchId.current !== null) navigator.geolocation.clearWatch(watchId.current);
    watchId.current = null;
    setTracking(false);
  };

  useEffect(() => () => { if (watchId.current !== null) navigator.geolocation.clearWatch(watchId.current); }, []);

  const themeData = THEMES[theme];
  const center = useMemo<[number, number]>(() => position ?? [-33.8688, 151.2093], [position]);

  return (
    <div className="relative h-screen w-full">
      <MapContainer
        center={center}
        zoom={13}
        scrollWheelZoom
        className="h-full w-full"
        zoomControl={false}
      >
        <TileLayer key={theme} url={themeData.url} attribution={themeData.attribution} />
        {showTrains && trainsData && (
          <GeoJSON
            key={`trains-${theme}`}
            data={trainsData}
            style={(f: any) => ({
              color: `#${f?.properties?.route_color ?? "888888"}`,
              weight: 3.5,
              opacity: 0.9,
            })}
            onEachFeature={(feature, layer: any) => {
              const p = feature.properties || {};
              layer.bindPopup(
                `<div style="font-size:12px"><strong>${p.route_short_name ?? ""} — ${p.route_desc ?? ""}</strong><br/>${p.route_long_name ?? ""}</div>`
              );
              const baseColor = `#${p.route_color ?? "888888"}`;
              layer.on({
                click: (e: any) => {
                  if (typeof layer.bringToFront === "function") layer.bringToFront();
                  if (typeof layer.setStyle === "function") {
                    layer.setStyle({ weight: 7, opacity: 1, color: baseColor });
                  }
                  e.originalEvent?.stopPropagation?.();
                },
                popupclose: () => {
                  if (typeof layer.setStyle === "function") {
                    layer.setStyle({ weight: 3.5, opacity: 0.9, color: baseColor });
                  }
                },
                mouseover: () => {
                  if (typeof layer.bringToFront === "function") layer.bringToFront();
                },
              });
            }}
          />
        )}
        {showTrains && trainsData && (
          <SimulatedTrains data={trainsData} onSelect={setSelectedTrain} />
        )}
        {position && (
          <Marker position={position} icon={liveIcon}>
            <Popup>
              <div className="text-sm">
                <div className="font-semibold">You are here</div>
                <div>Lat: {position[0].toFixed(5)}</div>
                <div>Lng: {position[1].toFixed(5)}</div>
                {accuracy && <div>±{Math.round(accuracy)}m</div>}
              </div>
            </Popup>
          </Marker>
        )}
        {selectedMarker && (
          <Marker position={[selectedMarker.lat, selectedMarker.lng]}>
            <Popup>
              <div className="text-sm max-w-[220px]">{selectedMarker.label}</div>
            </Popup>
          </Marker>
        )}
        <FlyTo position={position} />
        <FlyToSearch target={searchTarget} />
      </MapContainer>

      {/* Header */}
      <div className="pointer-events-none absolute inset-x-0 top-0 z-[1000] flex items-start justify-between p-4">
        <Card className="pointer-events-auto flex items-center gap-2 px-3 py-2 backdrop-blur-md bg-background/80">
          <MapIcon className="h-5 w-5 text-primary" />
          <div>
            <div className="text-sm font-semibold leading-none">Live Map</div>
            <div className="text-xs text-muted-foreground">Interactive navigation</div>
          </div>
        </Card>

        <Card className="pointer-events-auto flex items-center gap-2 px-3 py-2 backdrop-blur-md bg-background/80">
          {tracking ? (
            <Badge className="gap-1.5">
              <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
              Live
            </Badge>
          ) : (
            <Badge variant="secondary">Idle</Badge>
          )}
        </Card>
      </div>

      {/* Theme selector */}
      <Card className="pointer-events-auto absolute left-4 top-20 z-[1000] w-56 p-3 backdrop-blur-md bg-background/80">
        <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Map Theme
        </div>
        <div className="grid grid-cols-3 gap-2">
          {(Object.keys(THEMES) as ThemeKey[]).map((k) => (
            <button
              key={k}
              onClick={() => setTheme(k)}
              className={`group flex flex-col items-center gap-1 rounded-md p-1.5 transition-all hover:bg-accent ${
                theme === k ? "ring-2 ring-primary" : ""
              }`}
            >
              <div
                className="h-10 w-full rounded-md border"
                style={{ background: THEMES[k].swatch }}
              />
              <span className="text-[10px] font-medium">{THEMES[k].name}</span>
            </button>
          ))}
        </div>
      </Card>

      {/* Search bar */}
      <div className="pointer-events-auto absolute left-1/2 top-4 z-[1000] w-[min(420px,calc(100%-2rem))] -translate-x-1/2">
        <Card className="backdrop-blur-md bg-background/80 p-2">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              runSearch(query);
            }}
            className="flex items-center gap-2"
          >
            <Search className="ml-1 h-4 w-4 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search places in Sydney…"
              className="border-0 shadow-none focus-visible:ring-0 px-1"
            />
            {query && (
              <button
                type="button"
                onClick={() => { setQuery(""); setResults([]); }}
                className="text-muted-foreground hover:text-foreground"
                aria-label="Clear"
              >
                <X className="h-4 w-4" />
              </button>
            )}
            <Button type="submit" size="sm" disabled={searching}>
              {searching ? <Loader2 className="h-4 w-4 animate-spin" /> : "Go"}
            </Button>
          </form>
          {results.length > 0 && (
            <ul className="mt-2 max-h-64 overflow-auto rounded-md border bg-popover">
              {results.map((r) => (
                <li key={r.place_id}>
                  <button
                    onClick={() => pickResult(r)}
                    className="w-full px-3 py-2 text-left text-sm hover:bg-accent"
                  >
                    {r.display_name}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      {/* Controls */}
      <div className="absolute bottom-6 right-4 z-[1000] flex flex-col gap-2">
        <Button
          size="lg"
          variant={showTrains ? "secondary" : "outline"}
          onClick={() => setShowTrains((s) => !s)}
          className="shadow-lg"
        >
          <TrainFront className="mr-2 h-4 w-4" />
          {showTrains ? "Hide Train Lines" : "Show Train Lines"}
        </Button>
        <Button
          size="lg"
          onClick={tracking ? stopTracking : startTracking}
          className="shadow-lg"
          variant={tracking ? "destructive" : "default"}
        >
          {tracking ? <Navigation className="mr-2 h-4 w-4" /> : <Locate className="mr-2 h-4 w-4" />}
          {tracking ? "Stop Tracking" : "Start Live Location"}
        </Button>
        {error && (
          <Card className="bg-destructive/10 border-destructive/30 px-3 py-2 text-xs text-destructive">
            {error}
          </Card>
        )}
      </div>

      {/* Train details side panel */}
      {selectedTrain && (
        <div className="fixed inset-y-0 right-0 z-[1100] flex w-[420px] max-w-[92vw] flex-col overflow-y-auto border-l bg-white shadow-2xl animate-in slide-in-from-right">
          <button
            onClick={() => setSelectedTrain(null)}
            className="absolute right-3 top-3 z-10 rounded-md bg-white/90 p-1 text-gray-600 shadow hover:text-gray-900"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
              {/* Alerts banner */}
              <div className="flex items-start gap-2 border-b bg-white px-4 py-3 text-[13px]">
                <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-rose-600 text-[11px] font-bold text-white">!</div>
                <div className="min-w-0 flex-1">
                  <div className="truncate font-medium text-gray-800">🚆 {selectedTrain.alerts[0]}</div>
                  <div className="text-xs text-gray-500">{selectedTrain.alerts[1]}</div>
                </div>
                <span className="text-gray-400">›</span>
              </div>

              {/* Preceded-by header */}
              {selectedTrain.precededBy && (
                <div className="flex items-center justify-between border-b bg-gray-50 px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-gray-500">
                  <span>‹</span>
                  <span>
                    Preceded by: {selectedTrain.precededBy.runNumber}{" "}
                    <span
                      className="ml-1 inline-block rounded-sm px-1.5 py-0.5 text-[11px] font-bold text-white"
                      style={{ background: LINE_COLORS[selectedTrain.precededBy.label] ?? "#666" }}
                    >
                      {selectedTrain.precededBy.label}
                    </span>{" "}
                    {selectedTrain.precededBy.origin}
                  </span>
                </div>
              )}

              {/* Stops list with vertical timeline */}
              <div className="relative bg-white">
                {/* vertical line */}
                <div
                  className="absolute bottom-4 left-[14px] top-2 w-[3px]"
                  style={{ background: selectedTrain.color }}
                />
                <ul>
                  {selectedTrain.stops.map((s, i) => {
                    const isCurrent = s.status === "current";
                    const isPast = s.status === "departed";
                    return (
                      <li
                        key={i}
                        className="relative flex items-start gap-3 border-b border-gray-100 px-4 py-2.5"
                      >
                        {/* dot */}
                        <div className="relative z-10 mt-1.5 flex w-[10px] justify-center">
                          {isCurrent ? (
                            <div className="flex h-5 w-5 -translate-x-[5px] items-center justify-center rounded-full bg-white shadow ring-2" style={{ boxShadow: `0 0 0 2px ${selectedTrain.color}` }}>
                              <span className="text-[10px]">📡</span>
                            </div>
                          ) : (
                            <div
                              className="h-2.5 w-2.5 rounded-full ring-2 ring-white"
                              style={{ background: isPast ? selectedTrain.color : "#fff", border: `2px solid ${selectedTrain.color}` }}
                            />
                          )}
                        </div>

                        {/* station info */}
                        <div className="min-w-0 flex-1">
                          <div className="text-[10px] font-semibold uppercase tracking-wider text-gray-500">
                            {s.name}
                          </div>
                          <div className="flex items-center gap-1.5">
                            <span className="truncate text-[15px] font-bold text-gray-900">
                              {s.name}
                            </span>
                            {s.interchanges?.map((ic, k) => (
                              <span
                                key={k}
                                className="inline-flex h-4 w-4 items-center justify-center rounded-full text-[9px] font-bold text-white"
                                style={{ background: ic.color }}
                              >
                                {ic.label[0]}
                              </span>
                            ))}
                          </div>
                          <div className="text-[12px] text-gray-600">Platform {s.platform}</div>
                        </div>

                        {/* run number + occupancy + arrival */}
                        <div className="flex flex-col items-end gap-1">
                          <div className="flex items-center gap-1.5">
                            <span className="text-[10px] text-gray-400">{s.runNumber}</span>
                            {s.note && (
                              <span className="rounded-sm bg-gray-800 px-1.5 py-0.5 text-[10px] font-medium text-white">
                                {s.note}
                              </span>
                            )}
                          </div>
                          <OccupancyBars value={s.occupancy} />
                          <div className="text-right">
                            <div className="text-[10px] font-semibold uppercase tracking-wider text-gray-500">
                              {i === 0 ? "Departs" : "Arrives"}
                            </div>
                            <div className="text-[13px] font-bold text-gray-900">{s.time}</div>
                            <div className="text-[11px] text-emerald-600">on time</div>
                          </div>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </div>

              {/* Continues-as footer */}
              {selectedTrain.continuesAs && (
                <div className="flex items-center justify-between border-t bg-gray-50 px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-gray-500">
                  <span>
                    Continues as: {selectedTrain.continuesAs.runNumber}{" "}
                    <span
                      className="ml-1 inline-block rounded-sm px-1.5 py-0.5 text-[11px] font-bold text-white"
                      style={{ background: LINE_COLORS[selectedTrain.continuesAs.label] ?? "#666" }}
                    >
                      {selectedTrain.continuesAs.label}
                    </span>{" "}
                    {selectedTrain.continuesAs.destination}{" "}
                    <span className="font-normal normal-case text-gray-500">
                      via {selectedTrain.continuesAs.via}
                    </span>
                  </span>
                  <span>›</span>
                </div>
              )}

              <div className="px-4 py-3 text-[11px] text-gray-500">
                {selectedTrain.carriages} • Status: {selectedTrain.status}
              </div>
        </div>
      )}
    </div>
  );
}