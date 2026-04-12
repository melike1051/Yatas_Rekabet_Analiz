from db.repository import session_scope
from db.session import Base, engine


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    with session_scope():
        pass
