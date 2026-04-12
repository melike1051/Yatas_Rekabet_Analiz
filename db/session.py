from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from db.config import get_database_url


Base = declarative_base()


engine = create_engine(get_database_url(), future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
