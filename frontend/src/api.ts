// Typed API client for the MonsoonMitra backend.

/** Normalize the configured base URL so a malformed env var can't break requests.
 *  Handles the common host-dashboard copy-paste mistakes:
 *   - stray whitespace / newlines            → trimmed
 *   - trailing slashes                       → removed
 *   - missing scheme ("host.app")            → https:// prepended
 *   - doubled scheme ("https://https://…")   → collapsed
 *   - embedded credentials ("user:pass@…")   → stripped (fetch rejects these with
 *     "URL is not valid or contains user credentials")
 *   - otherwise-invalid value                → same-origin fallback ("") so the app
 *     can still work behind a proxy/rewrite instead of throwing.
 */
function resolveBase(): string {
  // Strip ALL whitespace (not just the ends): pasted values sometimes wrap
  // across lines in host dashboards. A valid URL never contains raw whitespace.
  let raw = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\s+/g, "") || "";
  if (!raw) return "http://localhost:8000"; // dev default
  raw = raw.replace(/^(?:https?:\/\/)+/i, (m) => m.match(/https?:\/\//i)![0]);
  raw = raw.replace(/\/+$/, "");
  if (!/^https?:\/\//i.test(raw)) raw = `https://${raw}`;
  try {
    const u = new URL(raw);
    u.username = "";
    u.password = "";
    return u.origin + (u.pathname === "/" ? "" : u.pathname);
  } catch {
    console.error("Invalid VITE_API_BASE_URL; falling back to same-origin:", raw);
    return "";
  }
}

const BASE = resolveBase();
const API = `${BASE}/api/v1`;

/** The API origin actually in use (shown in the UI when the backend is unreachable). */
export const API_BASE = BASE || `${typeof location !== "undefined" ? location.origin : ""} (same origin)`;

export type RiskLevel = "low" | "moderate" | "high" | "severe";
export type Phase = "before" | "during" | "after";

export interface Location { lat: number; lon: number; name?: string }

export interface GeoResult {
  name: string; lat: number; lon: number;
  admin1?: string | null; country?: string | null; country_code?: string | null; label: string;
}

export interface Household {
  adults: number; children: number; seniors: number;
  dwelling: "apartment" | "independent_house" | "slum_kutcha" | "coastal" | "hillside";
  floor: number; medical_needs: string[]; has_vehicle: boolean; pets: number;
}

export interface DailyForecast {
  date: string; precip_mm: number; precip_prob: number;
  temp_max: number; temp_min: number; wind_max_kmh: number;
}

export interface WeatherSnapshot {
  location: Location; observed_at: string; temp_c: number; feels_like_c: number;
  precip_mm: number; humidity: number; wind_kmh: number;
  monsoon_hazard_score: number; daily: DailyForecast[];
}

export interface Alert {
  id: string; severity: RiskLevel; title: string; message: string;
  hazard: string; issued_at: string; valid_until: string;
}

export interface PreparednessPlan {
  risk_level: RiskLevel; summary: string;
  before: string[]; during: string[]; after: string[]; go_bag: string[];
  language: string; generated_by: string;
}

export interface PlanResponse { plan: PreparednessPlan; weather: WeatherSnapshot; alerts: Alert[] }
export interface ChecklistItem { task: string; priority: RiskLevel; done: boolean }
export interface ChecklistResponse { phase: Phase; items: ChecklistItem[]; language: string; generated_by: string }
export interface TravelAdvisory {
  recommendation: "go" | "caution" | "postpone"; risk_level: RiskLevel;
  summary: string; tips: string[]; language: string; generated_by: string;
}
export interface ChatResponse { reply: string; language: string; grounded_on: string[]; generated_by: string }

/** Build a request URL safely so a bad path/base can never throw a raw URL error. */
function makeUrl(path: string): string {
  return API ? `${API}${path}` : `/api/v1${path.replace(/^\/api\/v1/, "")}`;
}

function friendlyNetworkError(err: unknown): Error {
  const msg = err instanceof Error ? err.message : String(err);
  return new Error(
    `Could not reach the API${BASE ? ` at ${BASE}` : ""}. ` +
      `Check the backend is running and VITE_API_BASE_URL is a valid https URL. (${msg})`,
  );
}

async function post<T>(path: string, body: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(makeUrl(path), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (err) {
    throw friendlyNetworkError(err);
  }
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `Request failed (${res.status})`);
  return res.json();
}

async function get<T>(path: string): Promise<T> {
  let res: Response;
  try {
    res = await fetch(makeUrl(path));
  } catch (err) {
    throw friendlyNetworkError(err);
  }
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return res.json();
}

export const api = {
  health: () => get<{ status: string; llm_enabled: boolean; provider: string }>("/health"),
  languages: () => get<{ languages: Record<string, string> }>("/languages"),
  geocode: (q: string, language = "en") =>
    get<GeoResult[]>(`/geocode?q=${encodeURIComponent(q)}&language=${language}`),
  reverseGeocode: (lat: number, lon: number, language = "en") =>
    get<GeoResult | null>(`/reverse-geocode?lat=${lat}&lon=${lon}&language=${language}`),
  weather: (l: Location) => get<WeatherSnapshot>(`/weather?lat=${l.lat}&lon=${l.lon}&name=${encodeURIComponent(l.name || "")}`),
  alerts: (l: Location) => get<Alert[]>(`/alerts?lat=${l.lat}&lon=${l.lon}`),
  plan: (location: Location, household: Household, language: string) =>
    post<PlanResponse>("/plan", { location, household, language }),
  checklist: (location: Location, household: Household, phase: Phase, language: string) =>
    post<ChecklistResponse>("/checklist", { location, household, phase, language }),
  travel: (origin: Location, destination: Location, depart_in_hours: number, mode: string, language: string) =>
    post<TravelAdvisory>("/plan/travel", { origin, destination, depart_in_hours, mode, language }),
  chat: (message: string, location: Location | null, language: string) =>
    post<ChatResponse>("/chat", { message, location, language }),
};

/** Resolve coordinates to a display name.
 *  Tries our backend first; if that is unreachable, falls back to the same
 *  free/keyless (CORS-enabled) provider directly from the browser, so the
 *  user still sees where they are even when the API is misconfigured. */
export async function resolvePlaceName(
  lat: number, lon: number, language = "en",
): Promise<string | null> {
  try {
    const p = await api.reverseGeocode(lat, lon, language);
    if (p?.name) return p.label || p.name;
  } catch { /* backend unreachable — try direct */ }

  try {
    const r = await fetch(
      "https://api.bigdatacloud.net/data/reverse-geocode-client" +
        `?latitude=${lat}&longitude=${lon}&localityLanguage=${encodeURIComponent(language)}`,
    );
    if (!r.ok) return null;
    const d = await r.json();
    const primary = d.city || d.locality || d.principalSubdivision;
    if (!primary) return null;
    const parts = [d.locality || primary, d.principalSubdivision, d.countryName].filter(Boolean);
    return Array.from(new Set(parts)).join(", ");
  } catch {
    return null;
  }
}
