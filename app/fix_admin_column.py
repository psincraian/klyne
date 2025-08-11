#!/usr/bin/env python3
"""
Script to fix is_admin column issues in production database.
Run this if you encounter is_admin NOT NULL constraint errors.
"""
import asyncio
import logging
from sqlalchemy import text
from src.core.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_admin_column():
    """Fix is_admin column default value and constraints."""
    async with engine.begin() as conn:
        try:
            # Check if column exists and has issues
            result = await conn.execute(text("""
                SELECT column_name, is_nullable, column_default 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'is_admin'
            """))
            row = result.fetchone()
            
            if row:
                logger.info(f"Current is_admin column: nullable={row.is_nullable}, default={row.column_default}")
                
                # Update any NULL values to false
                result = await conn.execute(text("""
                    UPDATE users SET is_admin = false WHERE is_admin IS NULL
                """))
                logger.info(f"Updated {result.rowcount} rows with NULL is_admin values")
                
                # Ensure column has proper default
                await conn.execute(text("""
                    ALTER TABLE users ALTER COLUMN is_admin SET DEFAULT false
                """))
                logger.info("Set default value for is_admin column")
                
                # Ensure column is NOT NULL
                await conn.execute(text("""
                    ALTER TABLE users ALTER COLUMN is_admin SET NOT NULL
                """))
                logger.info("Set is_admin column to NOT NULL")
                
            else:
                logger.info("is_admin column does not exist - it will be created by Alembic")
            
        except Exception as e:
            logger.error(f"Error fixing is_admin column: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(fix_admin_column())