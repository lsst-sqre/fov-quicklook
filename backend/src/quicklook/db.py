import contextlib

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from quicklook.config import config


# def disable_sa_warnings():
#     import warnings

#     from sqlalchemy.exc import SAWarning

#     warnings.filterwarnings(
#         'ignore',
#         message="Implicitly combining column .*? with column .*? under attribute",
#         category=SAWarning,
#     )


engine = create_engine(config.db_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextlib.contextmanager
def db_context():
    for db in get_db():
        yield db
