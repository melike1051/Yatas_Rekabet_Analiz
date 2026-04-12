from scraper.brands.brand_configs import BRAND_CONFIGS
from scraper.brands.furniture_scraper import FurnitureBrandScraper


class IstikbalScraper(FurnitureBrandScraper):
    def __init__(self):
        super().__init__(competitor_name="istikbal", config=BRAND_CONFIGS["istikbal"])
