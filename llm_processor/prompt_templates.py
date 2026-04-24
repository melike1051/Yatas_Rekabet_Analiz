from __future__ import annotations

import json

from scraper.utils.normalizers import make_json_safe


def build_product_spec_prompt(source_text: str) -> str:
    return f"""
Urun metninden teknik ozellikleri JSON olarak cikar.

Beklenen alanlar:
- material_type
- tabletop_thickness_mm
- width_cm
- depth_cm
- height_cm
- skeleton_type
- color
- confidence_score

Kurallar:
- Sadece metinde gecen bilgileri kullan.
- Emin degilsen null don.
- Birim donusumlerinde santimetre ve milimetre kullan.
- Cevabi yalnizca JSON nesnesi olarak don.
- Ek aciklama, markdown veya kod blogu ekleme.

Urun metni:
{source_text}
""".strip()


def build_competitive_insight_prompt(context: dict) -> str:
    compact_context = json.dumps(make_json_safe(context), ensure_ascii=False, indent=2)
    return f"""
Mobilya rekabet takibi verisini yorumlayip yonetici seviyesinde icgoruler uret.

Asagidaki JSON formatinda cevap ver:
{{
  "campaign_insight": "string",
  "launch_delist_insight": "string",
  "pricing_insight": "string",
  "strategic_summary": "string",
  "recommended_actions": ["string", "string", "string"]
}}

Kurallar:
- Sadece verilen veriden cikarsama yap.
- Sayisal ifadelerde veride yer alan sayilari kullan.
- Kisa, yonetici odakli ve aksiyona donuk yaz.
- Kampanya, fiyat ve katalog hareketlerini birlikte degerlendir.
- Cevabi yalnizca JSON nesnesi olarak don.

Veri:
{compact_context}
""".strip()
