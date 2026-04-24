from scraper.brands.brand_configs import BRAND_CONFIGS
from scraper.brands.furniture_scraper import FurnitureBrandScraper


def test_normalize_image_candidate_rejects_icon_assets() -> None:
    scraper = FurnitureBrandScraper("dogtas", BRAND_CONFIGS["dogtas"])
    assert scraper._normalize_image_candidate("https://www.dogtas.com/theme/agexdogtas/assets/icons/cart-heart.svg") is None


def test_normalize_image_candidate_accepts_product_images() -> None:
    scraper = FurnitureBrandScraper("bellona", BRAND_CONFIGS["bellona"])
    candidate = scraper._normalize_image_candidate("https://www.bellona.com.tr/idea/kc/78/myassets/products/998/product.jpg")
    assert candidate == "https://www.bellona.com.tr/idea/kc/78/myassets/products/998/product.jpg"
