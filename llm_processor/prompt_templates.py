from __future__ import annotations


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
