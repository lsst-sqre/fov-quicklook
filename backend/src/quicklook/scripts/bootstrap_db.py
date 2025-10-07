#!/usr/bin/env python
"""
Database bootstrap script.

Runs alembic migrations. If migration fails, drops all tables,
deletes all objects from object storage with the configured prefix,
and retries the migration.
"""

import asyncio
import logging
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig

from quicklook.config import config
from quicklook.db import Base, get_engine
from quicklook.object_storage import delete_objects_by_prefix

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def drop_all_tables():
    """Drop all tables from the database."""
    logger.info("Dropping all tables...")
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    logger.info("All tables dropped")


def delete_all_object_storage():
    """Delete all objects from object storage with the configured prefix."""
    logger.info(f"Deleting all objects with prefix: {config.s3_tile_key_prefix}quicklooks/")
    delete_objects_by_prefix("quicklooks/")
    logger.info("All objects deleted from object storage")


def run_migrations():
    """Run alembic migrations."""
    logger.info("Running alembic migrations...")
    
    # Get the alembic.ini path
    alembic_ini = Path(__file__).parent.parent.parent / "alembic.ini"
    if not alembic_ini.exists():
        raise FileNotFoundError(f"alembic.ini not found at {alembic_ini}")
    
    alembic_cfg = AlembicConfig(str(alembic_ini))
    command.upgrade(alembic_cfg, "head")
    logger.info("Migrations completed successfully")


async def bootstrap():
    """Bootstrap the database."""
    try:
        # Try to run migrations
        run_migrations()
        logger.info("Database bootstrap completed successfully")
        return True
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        logger.info("Attempting to reset database and retry...")
        
        try:
            # Drop all tables
            await drop_all_tables()
            
            # Delete all object storage data
            delete_all_object_storage()
            
            # Retry migrations
            run_migrations()
            logger.info("Database bootstrap completed successfully after reset")
            return True
        except Exception as e:
            logger.error(f"Failed to bootstrap database after reset: {e}")
            return False


def main():
    """Main entry point."""
    success = asyncio.run(bootstrap())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
