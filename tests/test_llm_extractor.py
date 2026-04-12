from decimal import Decimal

from llm_processor.extractor import build_spec_from_llm_payload, extract_specs_heuristic, merge_specs, parse_llm_json_response
from llm_processor.schemas import ProductSpecCandidate


def test_extract_specs_heuristic_material_and_dimensions() -> None:
    candidate = ProductSpecCandidate(
        product_id=1,
        competitor_name="test",
        competitor_sku="sku-1",
        product_name="MDF Masa",
        category_name="Acilir Masa",
        product_url="https://example.com/urun",
        source_text=(
            "MDF govde. Metal ayak. Genişlik 160 cm. Derinlik 90 cm. "
            "Yükseklik 76 cm. Tabla kalınlığı 18 mm. Renk beyaz."
        ),
    )

    result = extract_specs_heuristic(candidate)

    assert result.material_type == "MDF"
    assert result.skeleton_type == "Metal Ayak"
    assert result.width_cm == Decimal("160")
    assert result.depth_cm == Decimal("90")
    assert result.height_cm == Decimal("76")
    assert result.tabletop_thickness_mm == Decimal("18")
    assert result.color == "beyaz"


def test_parse_llm_json_response_with_code_fence() -> None:
    payload = parse_llm_json_response(
        """```json
        {"material_type":"MDF","width_cm":160}
        ```"""
    )
    assert payload["material_type"] == "MDF"
    assert payload["width_cm"] == 160


def test_merge_specs_prefers_primary_and_falls_back() -> None:
    primary = build_spec_from_llm_payload(
        {
            "material_type": "MDF",
            "width_cm": 160,
            "confidence_score": 0.8,
        }
    )
    fallback = extract_specs_heuristic(
        ProductSpecCandidate(
            product_id=2,
            competitor_name="test",
            competitor_sku="sku-2",
            product_name="Deneme",
            category_name="Acilir Masa",
            product_url="https://example.com/urun-2",
            source_text="Metal ayak. Derinlik 90 cm. Renk siyah.",
        )
    )

    merged = merge_specs(primary, fallback)

    assert merged.material_type == "MDF"
    assert merged.width_cm == Decimal("160")
    assert merged.depth_cm == Decimal("90")
    assert merged.skeleton_type == "Metal Ayak"
    assert merged.color == "siyah"
