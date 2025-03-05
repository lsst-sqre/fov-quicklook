import contextlib

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quicklook.config import config

# from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


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


if __name__ == '__main__':  # pragma: no cover

    def cli():
        import argparse

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest='command')
        subparsers.required = True

        drop = subparsers.add_parser('reset')
        drop.set_defaults(func=reset_db)

        drop_db_parser = subparsers.add_parser('drop')
        drop_db_parser.set_defaults(func=drop_db)

        args = parser.parse_args()

        args.func()

    def reset_db():
        from .models import Base

        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)

    def drop_db():
        from sqlalchemy import text

        from .models import Base

        Base.metadata.drop_all(engine)
        with engine.connect() as conn:

            conn.execute(text('DROP TABLE IF EXISTS alembic_version'))
            conn.commit()

    cli()
