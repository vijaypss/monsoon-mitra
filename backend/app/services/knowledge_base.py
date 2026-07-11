"""Curated monsoon-safety knowledge base + lightweight keyword retrieval.

This is the grounding source. In production this becomes a vector store
(district disaster-management plans, IMD/NDMA guidance). Here it's a compact,
auditable set of facts so every AI answer can cite real guidance rather than
hallucinate. Sources: NDMA/IMD public safety guidance (paraphrased).
"""
from __future__ import annotations

import re

KB: list[dict] = [
    {
        "id": "flood-electricity",
        "tags": ["flood", "flooding", "electricity", "power", "shock"],
        "text": "During flooding, switch off the mains electricity if water is entering the "
        "home. Never touch electrical switches or appliances with wet hands or while "
        "standing in water.",
    },
    {
        "id": "flood-drinking-water",
        "tags": ["flood", "water", "drinking", "disease", "cholera", "diarrhoea"],
        "text": "Floodwater contaminates drinking supplies. Store safe drinking water in "
        "advance (3 litres per person per day for 3 days). Boil or chlorine-treat water; "
        "waterborne diseases like cholera and leptospirosis spike after floods.",
    },
    {
        "id": "flood-evacuate",
        "tags": ["flood", "evacuate", "low-lying", "ground floor", "basement"],
        "text": "If you live on a low floor, basement, or low-lying/coastal area, identify the "
        "nearest higher ground or relief shelter beforehand. Do not walk or drive through "
        "moving floodwater; 15 cm of moving water can knock an adult down, 30 cm can float a car.",
    },
    {
        "id": "lightning-safety",
        "tags": ["lightning", "thunderstorm", "outdoor", "field"],
        "text": "When thunder roars, go indoors. Avoid open fields, isolated trees, water bodies "
        "and metal objects. India records the highest lightning deaths in the world during "
        "monsoon; 30 minutes should pass after the last thunder before going out.",
    },
    {
        "id": "go-bag",
        "tags": ["kit", "go-bag", "emergency", "supplies", "documents"],
        "text": "Keep a ready go-bag: drinking water, dry non-perishable food, torch with spare "
        "batteries, power bank, first-aid kit, essential medicines (7-day supply), copies of "
        "ID/insurance in a waterproof pouch, cash, whistle, and a phone charger.",
    },
    {
        "id": "medical-vulnerable",
        "tags": ["medical", "diabetes", "elderly", "senior", "infant", "children", "asthma"],
        "text": "For members with chronic conditions (diabetes, heart, asthma) keep extra "
        "medication and a note of dosages. Infants and elderly are most vulnerable to cold, "
        "damp and infection — keep them warm, dry and hydrated.",
    },
    {
        "id": "landslide-hillside",
        "tags": ["landslide", "hillside", "hill", "slope", "cracks"],
        "text": "In hilly areas watch for landslide signs: new cracks, tilting trees/poles, "
        "sudden muddy water in streams. Move away from steep slopes during prolonged heavy "
        "rain and know your evacuation route.",
    },
    {
        "id": "vehicle-travel",
        "tags": ["travel", "car", "vehicle", "road", "waterlogging", "drive"],
        "text": "Avoid non-essential travel during red/orange rainfall warnings. Do not enter "
        "waterlogged underpasses or flooded roads. Keep the fuel tank full, share your route, "
        "and check IMD/local traffic advisories before leaving.",
    },
    {
        "id": "after-cleanup",
        "tags": ["after", "recovery", "cleanup", "mould", "snake"],
        "text": "After a flood, wear gloves and boots during cleanup, disinfect surfaces, discard "
        "food touched by floodwater, watch for snakes/pests displaced by water, and dry the "
        "home to prevent mould. Report damaged power lines to authorities.",
    },
    {
        "id": "communication",
        "tags": ["alert", "phone", "communication", "emergency", "number"],
        "text": "Charge phones and power banks before a storm. Save emergency numbers: national "
        "emergency 112, disaster helpline 108, and note your local ward/municipal control room. "
        "Agree a family meeting point in case you get separated.",
    },
]


def retrieve(query: str, k: int = 4) -> list[dict]:
    """Simple keyword overlap scorer. Deterministic and dependency-free;
    swap for embeddings + a vector DB in production."""
    tokens = set(re.findall(r"[a-z]+", query.lower()))
    scored: list[tuple[int, dict]] = []
    for entry in KB:
        score = sum(1 for tag in entry["tags"] if tag in tokens or tag in query.lower())
        # also reward token overlap with the fact text
        score += len(tokens & set(re.findall(r"[a-z]+", entry["text"].lower()))) // 6
        if score > 0:
            scored.append((score, entry))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = [e for _, e in scored[:k]]
    return top or KB[:k]


def as_context(entries: list[dict]) -> str:
    return "\n".join(f"- [{e['id']}] {e['text']}" for e in entries)
