import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "./api";
import type {
  Alert, ChecklistItem, GeoResult, Location, PreparednessPlan, RiskLevel,
  TravelAdvisory, WeatherSnapshot,
} from "./api";

const RISK_STYLES: Record<RiskLevel, string> = {
  low: "bg-emerald-100 text-emerald-800 border-emerald-200",
  moderate: "bg-amber-100 text-amber-800 border-amber-200",
  high: "bg-orange-100 text-orange-800 border-orange-200",
  severe: "bg-red-100 text-red-800 border-red-200",
};

export function RiskBadge({ level }: { level: RiskLevel }) {
  return (
    <span className={`inline-block rounded-full border px-3 py-0.5 text-xs font-semibold uppercase tracking-wide ${RISK_STYLES[level]}`}>
      {level}
    </span>
  );
}

export function Card({ title, children, className = "" }: { title?: string; children: React.ReactNode; className?: string }) {
  return (
    <section className={`rounded-2xl border border-slate-200 bg-white p-5 shadow-sm ${className}`}>
      {title && <h2 className="mb-3 text-lg font-semibold text-slate-900">{title}</h2>}
      {children}
    </section>
  );
}

/** Debounced place search backed by the /geocode endpoint. Any place worldwide. */
export function LocationSearch({
  value, onSelect, placeholder, language = "en", allowGeolocate = false,
}: {
  value: Location | null;
  onSelect: (l: Location) => void;
  placeholder?: string;
  language?: string;
  allowGeolocate?: boolean;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<GeoResult[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [locating, setLocating] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  // Debounced geocode lookup.
  useEffect(() => {
    if (query.trim().length < 2) { setResults([]); return; }
    const id = setTimeout(async () => {
      setLoading(true);
      try { setResults(await api.geocode(query.trim(), language)); setOpen(true); }
      catch { setResults([]); }
      finally { setLoading(false); }
    }, 300);
    return () => clearTimeout(id);
  }, [query, language]);

  // Close on outside click.
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  function pick(r: GeoResult) {
    onSelect({ lat: r.lat, lon: r.lon, name: r.name });
    setQuery(""); setResults([]); setOpen(false);
  }

  function useMyLocation() {
    if (!navigator.geolocation) return;
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = +pos.coords.latitude.toFixed(4);
        const lon = +pos.coords.longitude.toFixed(4);
        // Resolve coordinates to a readable place name.
        let name = "My location";
        try {
          const place = await api.reverseGeocode(lat, lon, language);
          if (place?.name) name = place.label || place.name;
        } catch { /* keep fallback name */ }
        onSelect({ lat, lon, name });
        setLocating(false);
      },
      () => setLocating(false),
      { enableHighAccuracy: false, timeout: 8000 },
    );
  }

  return (
    <div className="relative" ref={boxRef}>
      <div className="flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => results.length && setOpen(true)}
          placeholder={placeholder || (value?.name ? value.name : "Search any city or place…")}
          className="w-full rounded-lg border border-slate-300 p-2 text-sm"
        />
        {allowGeolocate && (
          <button type="button" onClick={useMyLocation} title="Use my location"
            className="shrink-0 rounded-lg border border-slate-300 px-2 text-sm hover:bg-slate-50">
            {locating ? "…" : "📍"}
          </button>
        )}
      </div>
      {value?.name && !query && (
        <p className="mt-1 text-xs text-slate-500">Selected: <span className="font-medium text-slate-700">{value.name}</span></p>
      )}
      {open && (results.length > 0 || loading) && (
        <ul className="absolute z-20 mt-1 w-full overflow-hidden rounded-lg border border-slate-200 bg-white shadow-lg">
          {loading && <li className="px-3 py-2 text-sm text-slate-400">Searching…</li>}
          {results.map((r, i) => (
            <li key={`${r.lat},${r.lon},${i}`}>
              <button type="button" onClick={() => pick(r)}
                className="block w-full px-3 py-2 text-left text-sm hover:bg-monsoon-50">
                <span className="font-medium text-slate-800">{r.name}</span>
                <span className="text-slate-500"> — {r.label}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function Spinner({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-slate-500">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-monsoon-600" />
      {label}
    </div>
  );
}

export function WeatherCard({ w }: { w: WeatherSnapshot }) {
  const { t } = useTranslation();
  const hazardColor = w.monsoon_hazard_score >= 75 ? "text-red-600"
    : w.monsoon_hazard_score >= 50 ? "text-orange-600"
    : w.monsoon_hazard_score >= 25 ? "text-amber-600" : "text-emerald-600";
  return (
    <Card title={`${t("weather")} · ${w.location.name || ""}`}>
      <div className="flex flex-wrap items-end gap-x-8 gap-y-3">
        <div>
          <div className="text-4xl font-bold text-slate-900">{Math.round(w.temp_c)}°C</div>
          <div className="text-sm text-slate-500">feels {Math.round(w.feels_like_c)}°C · {w.humidity}% humidity</div>
        </div>
        <div className="text-sm text-slate-600">
          <div>Rain now: {w.precip_mm} mm</div>
          <div>Wind: {Math.round(w.wind_kmh)} km/h</div>
        </div>
        <div className="ml-auto text-right">
          <div className="text-xs uppercase tracking-wide text-slate-400">{t("hazard")}</div>
          <div className={`text-3xl font-bold ${hazardColor}`}>{w.monsoon_hazard_score}<span className="text-base text-slate-400">/100</span></div>
        </div>
      </div>
      {w.daily.length > 0 && (
        <div className="mt-4 grid grid-cols-3 gap-2 sm:grid-cols-5">
          {w.daily.slice(0, 5).map((d) => (
            <div key={d.date} className="rounded-lg bg-slate-50 p-2 text-center text-xs">
              <div className="font-medium text-slate-700">{new Date(d.date).toLocaleDateString(undefined, { weekday: "short" })}</div>
              <div className="text-monsoon-600">{Math.round(d.precip_mm)}mm</div>
              <div className="text-slate-400">{d.precip_prob}%</div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

export function AlertsPanel({ alerts }: { alerts: Alert[] }) {
  const { t } = useTranslation();
  if (alerts.length === 0)
    return <Card title={t("alerts")}><p className="text-sm text-slate-500">{t("noAlerts")}</p></Card>;
  return (
    <Card title={`${t("alerts")} (${alerts.length})`}>
      <ul className="space-y-3">
        {alerts.map((a) => (
          <li key={a.id} className={`rounded-xl border p-3 ${RISK_STYLES[a.severity]}`}>
            <div className="flex items-center justify-between">
              <span className="font-semibold">{a.title}</span>
              <RiskBadge level={a.severity} />
            </div>
            <p className="mt-1 text-sm opacity-90">{a.message}</p>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function StepList({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <h3 className="mb-2 font-semibold text-slate-800">{title}</h3>
      <ul className="space-y-1.5">
        {items.map((s, i) => (
          <li key={i} className="flex gap-2 text-sm text-slate-700">
            <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-monsoon-500" />{s}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function PlanView({ plan }: { plan: PreparednessPlan }) {
  const { t } = useTranslation();
  return (
    <Card>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">{t("generatePlan")}</h2>
        <RiskBadge level={plan.risk_level} />
      </div>
      <p className="mb-5 rounded-lg bg-monsoon-50 p-3 text-sm text-slate-700">{plan.summary}</p>
      <div className="grid gap-6 md:grid-cols-3">
        <StepList title={t("before")} items={plan.before} />
        <StepList title={t("during")} items={plan.during} />
        <StepList title={t("after")} items={plan.after} />
      </div>
      <div className="mt-6 border-t border-slate-100 pt-4">
        <StepList title={t("goBag")} items={plan.go_bag} />
      </div>
      <p className="mt-4 text-right text-xs text-slate-400">
        {plan.generated_by === "template" ? t("poweredTemplate") : plan.generated_by}
      </p>
    </Card>
  );
}

export function TravelResult({ adv }: { adv: TravelAdvisory }) {
  const color = adv.recommendation === "postpone" ? "text-red-600"
    : adv.recommendation === "caution" ? "text-amber-600" : "text-emerald-600";
  return (
    <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex items-center justify-between">
        <span className={`text-lg font-bold uppercase ${color}`}>{adv.recommendation}</span>
        <RiskBadge level={adv.risk_level} />
      </div>
      <p className="mt-1 text-sm text-slate-700">{adv.summary}</p>
      <ul className="mt-2 space-y-1">
        {adv.tips.map((tip, i) => <li key={i} className="text-sm text-slate-600">• {tip}</li>)}
      </ul>
    </div>
  );
}

export function ChecklistView({ items, onToggle }: { items: ChecklistItem[]; onToggle: (i: number) => void }) {
  return (
    <ul className="mt-4 space-y-2">
      {items.map((it, i) => (
        <li key={i} className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white p-3">
          <input type="checkbox" checked={it.done} onChange={() => onToggle(i)}
                 className="h-5 w-5 rounded border-slate-300 text-monsoon-600" />
          <span className={`flex-1 text-sm ${it.done ? "text-slate-400 line-through" : "text-slate-700"}`}>{it.task}</span>
          <RiskBadge level={it.priority} />
        </li>
      ))}
    </ul>
  );
}
