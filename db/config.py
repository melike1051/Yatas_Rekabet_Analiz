from functools import lru_cache
from os import getenv

from dotenv import load_dotenv


load_dotenv()


@lru_cache(maxsize=1)
def get_database_url() -> str:
    return (
        f"postgresql+psycopg2://{getenv('POSTGRES_USER', 'competitor_user')}:"
        f"{getenv('POSTGRES_PASSWORD', 'competitor_pass')}@"
        f"{getenv('POSTGRES_HOST', 'localhost')}:"
        f"{getenv('POSTGRES_PORT', '5432')}/"
        f"{getenv('POSTGRES_DB', 'competitor_analysis')}"
    )
