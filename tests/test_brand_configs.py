from scraper.brands.brand_configs import BRAND_CONFIGS


def test_brand_configs_define_category_sources() -> None:
    for config in BRAND_CONFIGS.values():
        assert config["category_sources"]
        assert config["category_sources"][0]["category_name"] == "Yemek Odasi"
        assert config["category_sources"][0]["url"].startswith("https://")
