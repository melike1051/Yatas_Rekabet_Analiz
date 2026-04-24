from scraper.schemas import ScrapedProduct


def test_scraped_product_supports_image_url() -> None:
    product = ScrapedProduct(
        competitor_name="bellona",
        competitor_sku="sku-1",
        product_name="Mona Konsol",
        category_name="Konsol",
        product_url="https://example.com/mona-konsol",
        image_url="https://cdn.example.com/mona-konsol.jpg",
    )

    assert product.image_url == "https://cdn.example.com/mona-konsol.jpg"
