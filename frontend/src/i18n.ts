// UI-chrome translations. AI-generated content (plans, chat) is translated
// server-side by the LLM into any of the 12 supported languages.
import i18n from "i18next";
import { initReactI18next } from "react-i18next";

const resources = {
  en: {
    translation: {
      tagline: "Your monsoon preparedness companion",
      location: "Location", household: "Household", language: "Language",
      adults: "Adults", children: "Children", seniors: "Seniors",
      dwelling: "Dwelling", floor: "Floor", vehicle: "Has vehicle", pets: "Pets",
      medical: "Medical needs (comma separated)",
      generatePlan: "Generate my plan", weather: "Weather", hazard: "Monsoon hazard",
      alerts: "Alerts", noAlerts: "No active alerts for this area.",
      before: "Before", during: "During", after: "After", goBag: "Emergency go-bag",
      checklist: "Checklist", travel: "Travel advisory", assistant: "Ask MonsoonMitra",
      from: "From", to: "To", departIn: "Depart in (hours)", mode: "Mode",
      checkTravel: "Check this trip", ask: "Ask", askPlaceholder: "e.g. Is it safe to travel by train today?",
      loading: "Working…", poweredTemplate: "offline template", emergency: "In an emergency call 112",
    },
  },
  hi: {
    translation: {
      tagline: "आपका मानसून तैयारी साथी",
      location: "स्थान", household: "परिवार", language: "भाषा",
      adults: "वयस्क", children: "बच्चे", seniors: "बुज़ुर्ग",
      dwelling: "निवास", floor: "मंज़िल", vehicle: "वाहन है", pets: "पालतू",
      medical: "चिकित्सा ज़रूरतें (कॉमा से अलग)",
      generatePlan: "मेरी योजना बनाएँ", weather: "मौसम", hazard: "मानसून जोखिम",
      alerts: "चेतावनियाँ", noAlerts: "इस क्षेत्र के लिए कोई सक्रिय चेतावनी नहीं।",
      before: "पहले", during: "दौरान", after: "बाद में", goBag: "आपातकालीन बैग",
      checklist: "चेकलिस्ट", travel: "यात्रा सलाह", assistant: "मानसूनमित्र से पूछें",
      from: "से", to: "तक", departIn: "प्रस्थान (घंटे में)", mode: "साधन",
      checkTravel: "यात्रा जाँचें", ask: "पूछें", askPlaceholder: "जैसे: क्या आज ट्रेन से यात्रा सुरक्षित है?",
      loading: "काम हो रहा है…", poweredTemplate: "ऑफ़लाइन टेम्पलेट", emergency: "आपातकाल में 112 पर कॉल करें",
    },
  },
};

i18n.use(initReactI18next).init({
  resources,
  lng: "en",
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

export default i18n;
