import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Alert, api, Household, Location, Phase, PlanResponse,
  ChecklistItem, TravelAdvisory, ChatResponse,
} from "./api";
import {
  AlertsPanel, Card, ChecklistView, LocationSearch, PlanView, Spinner, TravelResult, WeatherCard,
} from "./components";

const LANGS = [
  ["en", "English"], ["hi", "हिन्दी"], ["bn", "বাংলা"], ["ta", "தமிழ்"], ["te", "తెలుగు"],
  ["mr", "मराठी"], ["gu", "ગુજરાતી"], ["kn", "ಕನ್ನಡ"], ["ml", "മലയാളം"], ["pa", "ਪੰਜਾਬੀ"],
  ["or", "ଓଡ଼ିଆ"], ["as", "অসমীয়া"],
];

const DEFAULT_HOUSEHOLD: Household = {
  adults: 2, children: 0, seniors: 0, dwelling: "apartment",
  floor: 1, medical_needs: [], has_vehicle: false, pets: 0,
};

type Tab = "plan" | "checklist" | "travel" | "assistant";

export default function App() {
  const { t, i18n } = useTranslation();
  const [language, setLanguage] = useState("en");
  const [location, setLocation] = useState<Location | null>(null);
  const [household, setHousehold] = useState<Household>(DEFAULT_HOUSEHOLD);
  const [tab, setTab] = useState<Tab>("plan");

  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [plan, setPlan] = useState<PlanResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [banner, setBanner] = useState<string | null>(null);

  useEffect(() => { i18n.changeLanguage(language === "hi" ? "hi" : "en"); }, [language, i18n]);

  // Try to detect the user's location once on first load (non-blocking),
  // then resolve the coordinates to a readable place name.
  useEffect(() => {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = +pos.coords.latitude.toFixed(4);
        const lon = +pos.coords.longitude.toFixed(4);
        let name = "My location";
        try {
          const place = await api.reverseGeocode(lat, lon);
          if (place?.name) name = place.label || place.name;
        } catch { /* keep fallback */ }
        setLocation({ lat, lon, name });
      },
      () => {/* user declined; they can search manually */},
      { enableHighAccuracy: false, timeout: 8000 },
    );
  }, []);

  // Real-time alerts via SSE; re-subscribes whenever the chosen location changes.
  useEffect(() => {
    if (!location) return;
    api.alerts(location).then(setAlerts).catch(() => {});
    const es = new EventSource(api.alertStreamUrl(location));
    es.addEventListener("alerts", (e) => {
      try {
        const data = JSON.parse((e as MessageEvent).data);
        const list: Alert[] = Array.isArray(data?.alerts) ? data.alerts : [];
        setAlerts(list);
        const severe = list.find((a) => a.severity === "severe" || a.severity === "high");
        if (severe) setBanner(`⚠ ${severe.title}`);
      } catch { /* ignore malformed frame */ }
    });
    es.onerror = () => es.close();
    return () => es.close();
  }, [location]);

  async function generatePlan() {
    if (!location) { setError("Please choose a location first."); return; }
    setLoading(true); setError(null);
    try {
      const res = await api.plan(location, household, language);
      setPlan(res); setAlerts(Array.isArray(res.alerts) ? res.alerts : []);
    } catch (e) { setError((e as Error).message); }
    finally { setLoading(false); }
  }

  return (
    <div className="min-h-screen">
      <header className="bg-gradient-to-r from-monsoon-700 to-monsoon-500 text-white">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-4 py-4">
          <div>
            <h1 className="text-2xl font-bold">🌧️ MonsoonMitra</h1>
            <p className="text-sm text-monsoon-50">{t("tagline")}</p>
          </div>
          <select value={language} onChange={(e) => setLanguage(e.target.value)}
                  className="rounded-lg bg-white/15 px-3 py-1.5 text-sm text-white backdrop-blur">
            {LANGS.map(([code, label]) => (
              <option key={code} value={code} className="text-slate-800">{label}</option>
            ))}
          </select>
        </div>
      </header>

      {banner && (
        <div className="bg-red-600 px-4 py-2 text-center text-sm font-medium text-white">
          {banner} · {t("emergency")}
          <button className="ml-3 underline" onClick={() => setBanner(null)}>✕</button>
        </div>
      )}

      {location && (
        <div className="border-b border-slate-200 bg-white">
          <div className="mx-auto flex max-w-5xl items-center gap-2 px-4 py-2 text-sm">
            <span className="text-monsoon-600">📍</span>
            <span className="font-medium text-slate-800">{location.name || "Selected location"}</span>
            <span className="text-slate-400">({location.lat.toFixed(3)}, {location.lon.toFixed(3)})</span>
          </div>
        </div>
      )}

      <main className="mx-auto max-w-5xl space-y-5 px-4 py-6">
        <ProfileBar location={location} setLocation={setLocation} language={language}
                    household={household} setHousehold={setHousehold} />

        {plan && <WeatherCard w={plan.weather} />}
        {location && <AlertsPanel alerts={alerts} />}

        <nav className="flex gap-2 overflow-x-auto">
          {(["plan", "checklist", "travel", "assistant"] as Tab[]).map((tb) => (
            <button key={tb} onClick={() => setTab(tb)}
              className={`whitespace-nowrap rounded-full px-4 py-1.5 text-sm font-medium ${
                tab === tb ? "bg-monsoon-600 text-white" : "bg-white text-slate-600 border border-slate-200"}`}>
              {t(tb === "plan" ? "generatePlan" : tb)}
            </button>
          ))}
        </nav>

        {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>}
        {!location && <div className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
          Search for your city or tap 📍 above to begin.
        </div>}

        {tab === "plan" && (
          <div className="space-y-4">
            <button onClick={generatePlan} disabled={loading || !location}
              className="rounded-xl bg-monsoon-600 px-5 py-2.5 font-medium text-white hover:bg-monsoon-700 disabled:opacity-60">
              {loading ? t("loading") : t("generatePlan")}
            </button>
            {loading && <Spinner label={t("loading")} />}
            {plan && <PlanView plan={plan.plan} />}
          </div>
        )}
        {tab === "checklist" && <ChecklistTab location={location} household={household} language={language} />}
        {tab === "travel" && <TravelTab origin={location} language={language} />}
        {tab === "assistant" && <AssistantTab location={location} language={language} />}
      </main>

      <footer className="mx-auto max-w-5xl px-4 py-6 text-center text-xs text-slate-400">
        Reference implementation · Not a substitute for official IMD/NDMA warnings · {t("emergency")}
      </footer>
    </div>
  );
}

function ProfileBar({ location, setLocation, household, setHousehold, language }: {
  location: Location | null; setLocation: (l: Location) => void;
  household: Household; setHousehold: (h: Household) => void; language: string;
}) {
  const { t } = useTranslation();
  const num = (v: string) => Math.max(0, parseInt(v || "0", 10));
  return (
    <Card title={`${t("location")} · ${t("household")}`}>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="text-sm sm:col-span-2 lg:col-span-2">{t("location")}
          <div className="mt-1"><LocationSearch value={location} onSelect={setLocation} language={language} allowGeolocate /></div>
        </div>
        <label className="text-sm">{t("dwelling")}
          <select value={household.dwelling} onChange={(e) => setHousehold({ ...household, dwelling: e.target.value as Household["dwelling"] })}
            className="mt-1 w-full rounded-lg border border-slate-300 p-2">
            {["apartment", "independent_house", "slum_kutcha", "coastal", "hillside"].map((d) =>
              <option key={d} value={d}>{d.replace("_", " ")}</option>)}
          </select>
        </label>
        <label className="text-sm">{t("floor")}
          <input type="number" value={household.floor} onChange={(e) => setHousehold({ ...household, floor: parseInt(e.target.value || "0", 10) })}
            className="mt-1 w-full rounded-lg border border-slate-300 p-2" />
        </label>
        <label className="text-sm">{t("adults")}
          <input type="number" value={household.adults} onChange={(e) => setHousehold({ ...household, adults: num(e.target.value) })}
            className="mt-1 w-full rounded-lg border border-slate-300 p-2" />
        </label>
        <label className="text-sm">{t("children")}
          <input type="number" value={household.children} onChange={(e) => setHousehold({ ...household, children: num(e.target.value) })}
            className="mt-1 w-full rounded-lg border border-slate-300 p-2" />
        </label>
        <label className="text-sm">{t("seniors")}
          <input type="number" value={household.seniors} onChange={(e) => setHousehold({ ...household, seniors: num(e.target.value) })}
            className="mt-1 w-full rounded-lg border border-slate-300 p-2" />
        </label>
        <label className="text-sm sm:col-span-2">{t("medical")}
          <input type="text" onChange={(e) => setHousehold({ ...household, medical_needs: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })}
            className="mt-1 w-full rounded-lg border border-slate-300 p-2" placeholder="diabetes, asthma" />
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={household.has_vehicle} onChange={(e) => setHousehold({ ...household, has_vehicle: e.target.checked })}
            className="h-4 w-4" /> {t("vehicle")}
        </label>
      </div>
    </Card>
  );
}

function ChecklistTab({ location, household, language }: { location: Location | null; household: Household; language: string }) {
  const { t } = useTranslation();
  const [phase, setPhase] = useState<Phase>("before");
  const [items, setItems] = useState<ChecklistItem[]>([]);
  const [loading, setLoading] = useState(false);

  async function load(p: Phase) {
    if (!location) return;
    setPhase(p); setLoading(true);
    try { setItems((await api.checklist(location, household, p, language)).items); }
    finally { setLoading(false); }
  }
  const toggle = (i: number) => setItems(items.map((it, idx) => idx === i ? { ...it, done: !it.done } : it));

  return (
    <Card title={t("checklist")}>
      {!location ? <p className="text-sm text-slate-500">Choose a location first.</p> : (
        <>
          <div className="flex gap-2">
            {(["before", "during", "after"] as Phase[]).map((p) => (
              <button key={p} onClick={() => load(p)}
                className={`rounded-full px-4 py-1 text-sm ${phase === p && items.length ? "bg-monsoon-600 text-white" : "border border-slate-200 bg-white"}`}>
                {t(p)}
              </button>
            ))}
          </div>
          {loading ? <div className="mt-4"><Spinner label={t("loading")} /></div>
            : <ChecklistView items={items} onToggle={toggle} />}
        </>
      )}
    </Card>
  );
}

function TravelTab({ origin, language }: { origin: Location | null; language: string }) {
  const { t } = useTranslation();
  const [dest, setDest] = useState<Location | null>(null);
  const [hours, setHours] = useState(2);
  const [adv, setAdv] = useState<TravelAdvisory | null>(null);
  const [loading, setLoading] = useState(false);

  async function check() {
    if (!origin || !dest) return;
    setLoading(true);
    try { setAdv(await api.travel(origin, dest, hours, "car", language)); }
    finally { setLoading(false); }
  }
  return (
    <Card title={t("travel")}>
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="text-sm">{t("from")}
          <div className="mt-1 rounded-lg border border-slate-200 bg-slate-50 p-2">{origin?.name || "—"}</div>
        </div>
        <div className="text-sm">{t("to")}
          <div className="mt-1"><LocationSearch value={dest} onSelect={setDest} language={language} /></div>
        </div>
        <label className="text-sm">{t("departIn")}
          <input type="number" value={hours} onChange={(e) => setHours(parseInt(e.target.value || "0", 10))}
            className="mt-1 w-full rounded-lg border border-slate-300 p-2" />
        </label>
      </div>
      <button onClick={check} disabled={loading || !origin || !dest}
        className="mt-4 rounded-xl bg-monsoon-600 px-5 py-2 font-medium text-white hover:bg-monsoon-700 disabled:opacity-60">
        {loading ? t("loading") : t("checkTravel")}
      </button>
      {adv && <TravelResult adv={adv} />}
    </Card>
  );
}

function AssistantTab({ location, language }: { location: Location | null; language: string }) {
  const { t } = useTranslation();
  const [msg, setMsg] = useState("");
  const [log, setLog] = useState<{ role: "user" | "assistant"; text: string }[]>([]);
  const [loading, setLoading] = useState(false);

  async function send() {
    if (!msg.trim()) return;
    const question = msg.trim();
    setLog((l) => [...l, { role: "user", text: question }]); setMsg(""); setLoading(true);
    try {
      const res: ChatResponse = await api.chat(question, location, language);
      setLog((l) => [...l, { role: "assistant", text: res.reply }]);
    } catch (e) {
      setLog((l) => [...l, { role: "assistant", text: (e as Error).message }]);
    } finally { setLoading(false); }
  }

  return (
    <Card title={t("assistant")}>
      <div className="mb-3 max-h-80 space-y-2 overflow-y-auto">
        {log.map((m, i) => (
          <div key={i} className={`rounded-xl p-3 text-sm ${m.role === "user" ? "ml-auto max-w-[80%] bg-monsoon-600 text-white" : "mr-auto max-w-[85%] bg-slate-100 text-slate-800"}`}>
            {m.text}
          </div>
        ))}
        {loading && <Spinner label={t("loading")} />}
      </div>
      <div className="flex gap-2">
        <input value={msg} onChange={(e) => setMsg(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder={t("askPlaceholder")} className="flex-1 rounded-xl border border-slate-300 p-2.5 text-sm" />
        <button onClick={send} disabled={loading}
          className="rounded-xl bg-monsoon-600 px-5 font-medium text-white hover:bg-monsoon-700 disabled:opacity-60">{t("ask")}</button>
      </div>
    </Card>
  );
}
