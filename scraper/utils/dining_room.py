from __future__ import annotations

import re
import unicodedata

ITEM_TYPE_ORDER = {
    "Konsol": 1,
    "Sabit Masa": 2,
    "Acilir Masa": 3,
    "Sandalye": 4,
    "Bench / Puf": 5,
    "Vitrin": 6,
    "Yemek Odasi": 7,
}

GENERIC_TEAM_TOKENS = {
    "yemek",
    "odasi",
    "odası",
    "takimi",
    "takımı",
    "masa",
    "masasi",
    "masası",
    "acilir",
    "açılır",
    "sabit",
    "mini",
    "konsol",
    "sandalye",
    "bench",
    "bank",
    "puf",
    "vitrin",
    "sehpa",
    "ayna",
    "şifonyer",
    "sifonyer",
    "yuvarlak",
    "fitilli",
    "kadife",
    "dokulu",
    "alternatif",
    "mutfak",
    "genc",
    "genç",
    "aynasi",
    "aynası",
    "li",
}

SECONDARY_COMPONENT_TOKENS = {
    "ayakucu",
    "acilir",
    "açılır",
    "sabit",
    "konsol",
    "sifonyer",
    "şifonyer",
    "yuvarlak",
    "mini",
    "mermer",
    "melanj",
    "orme",
    "örme",
    "sonil",
    "fitilli",
    "dokuma",
    "desenli",
    "desen",
    "alternatif",
    "mutfak",
    "genc",
    "genç",
    "aynasi",
    "aynası",
}

CHARACTER_MAP = str.maketrans(
    {
        "ı": "i",
        "İ": "i",
        "ş": "s",
        "Ş": "s",
        "ğ": "g",
        "Ğ": "g",
        "ç": "c",
        "Ç": "c",
        "ö": "o",
        "Ö": "o",
        "ü": "u",
        "Ü": "u",
    }
)


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = normalized.translate(CHARACTER_MAP)
    return normalized.casefold()


def clean_product_name(product_name: str | None) -> str:
    if not product_name:
        return ""
    cleaned_lines: list[str] = []
    for raw_line in str(product_name).splitlines():
        line = " ".join(raw_line.split()).strip()
        if not line:
            continue
        normalized_line = normalize_text(line)
        if "sepette" in normalized_line or "alisveriste" in normalized_line or "indirim" in normalized_line:
            continue
        if " tl" in normalized_line and any(char.isdigit() for char in normalized_line):
            continue
        if re.fullmatch(r"[\d.,]+\s*tl?", normalized_line):
            continue
        cleaned_lines.append(line)
    if not cleaned_lines:
        return " ".join(str(product_name).split())
    return " ".join(cleaned_lines)


def infer_item_type(product_name: str | None) -> str:
    name = normalize_text(clean_product_name(product_name))
    if "yemek odasi takimi" in name or "yemek odasi" in name and "takim" in name:
        return "Yemek Odasi"
    if "konsol" in name:
        return "Konsol"
    if "vitrin" in name:
        return "Vitrin"
    if "sandalye" in name:
        return "Sandalye"
    if "bench" in name or "bank" in name or "puf" in name:
        return "Bench / Puf"
    if "masa" in name and "sabit" in name:
        return "Sabit Masa"
    if "masa" in name and ("acilir" in name or "extensible" in name):
        return "Acilir Masa"
    if "masa" in name:
        return "Acilir Masa"
    return "Diger"


def infer_team_size_variant(product_name: str | None) -> str | None:
    if not product_name:
        return None
    match = re.search(r"tak[ıi]m\s*\((\d+)\)\s*(min|max)", normalize_text(clean_product_name(product_name)))
    if not match:
        return None
    team_no, variant = match.groups()
    return f"Takim ({team_no}) {variant.upper()}"


def is_team_row(product_name: str | None, item_type: str | None = None) -> bool:
    if item_type == "Yemek Odasi":
        return True
    name = normalize_text(clean_product_name(product_name))
    return "yemek odasi takimi" in name or "yemek odasi" in name and "takim" in name


def derive_team_name(product_name: str | None) -> str:
    if not product_name:
        return "Bilinmiyor"

    cleaned = re.sub(r"[()\\-_/]", " ", clean_product_name(product_name))
    tokens = [token for token in cleaned.split() if token]
    filtered = [
        token
        for token in tokens
        if normalize_text(token) not in GENERIC_TEAM_TOKENS and not any(char.isdigit() for char in token)
    ]
    if len(filtered) >= 2 and normalize_text(filtered[1]) in SECONDARY_COMPONENT_TOKENS:
        base_tokens = filtered[:1]
    else:
        base_tokens = filtered[:2] or tokens[:2]
    return " ".join(base_tokens).strip() or product_name


def build_match_key(product_name: str | None, item_type: str | None, team_name: str | None = None) -> str:
    normalized_team = normalize_text(team_name) or normalize_text(derive_team_name(product_name))
    normalized_type = normalize_text(item_type) or infer_item_type(product_name)
    return f"{normalized_team}|{normalized_type}"


def classify_product(product_name: str | None) -> dict[str, str | bool | None | int]:
    item_type = infer_item_type(product_name)
    team_name = derive_team_name(product_name)
    team_row = is_team_row(product_name, item_type)
    team_size_variant = infer_team_size_variant(product_name)
    return {
        "team_name": team_name,
        "item_type": item_type,
        "is_team_row": team_row,
        "team_size_variant": team_size_variant,
        "display_order": ITEM_TYPE_ORDER.get(item_type, 999),
        "match_group": build_match_key(product_name, item_type, team_name),
    }
