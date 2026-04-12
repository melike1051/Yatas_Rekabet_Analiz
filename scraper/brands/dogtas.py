from scraper.brands.brand_configs import BRAND_CONFIGS
from scraper.brands.furniture_scraper import FurnitureBrandScraper


class DogtasScraper(FurnitureBrandScraper):
    def __init__(self):
        super().__init__(competitor_name="dogtas", config=BRAND_CONFIGS["dogtas"])
