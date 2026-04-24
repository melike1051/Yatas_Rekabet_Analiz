from llm_processor.insights import generate_competitive_insights


def test_generate_competitive_insights_returns_heuristic_fallback() -> None:
    result = generate_competitive_insights(
        {
            "llm_provider": "heuristic",
            "overview": {"competitor_count": 3, "product_count": 100},
            "price_summary": {"top_discount_brand": "bellona", "price_decreased_count": 7},
            "promotion_summary": {
                "top_campaign_type": "basket_discount",
                "brands": [
                    {
                        "competitor_name": "dogtas",
                        "promotion_count": 5,
                        "basket_discount_count": 3,
                    }
                ],
            },
            "catalog_diff_summary": {
                "brands": {
                    "bellona": {"summary": {"new_count": 2, "removed_count": 1}},
                    "dogtas": {"summary": {"new_count": 0, "removed_count": 2}},
                }
            },
        }
    )

    assert result["generated_by"] == "heuristic"
    assert "dogtas" in result["campaign_insight"].lower()
    assert "bellona" in result["launch_delist_insight"].lower()
    assert "bellona" in result["pricing_insight"].lower()
    assert len(result["recommended_actions"]) == 3
