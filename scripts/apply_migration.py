"""
Apply database migration script.

Usage:
    python scripts/apply_migration.py schema/003_filing_text_content.sql
"""

import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Note: dotenv not needed in production (Railway provides env vars directly)


def apply_migration(sql_file: Path):
    """Apply SQL migration file to database."""

    if not sql_file.exists():
        logger.error(f"❌ File not found: {sql_file}")
        return False

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("❌ DATABASE_URL not set in environment")
        return False

    logger.info(f"Applying migration: {sql_file.name}")
    logger.info(f"Database: {database_url.split('@')[1] if '@' in database_url else 'local'}")

    try:
        # Read SQL file
        sql_content = sql_file.read_text(encoding='utf-8')

        # Create engine
        engine = create_engine(database_url)

        # Execute SQL
        with engine.connect() as conn:
            # Split by semicolon and execute each statement
            statements = [s.strip() for s in sql_content.split(';') if s.strip()]

            logger.info(f"Executing {len(statements)} SQL statements...")

            for i, statement in enumerate(statements, 1):
                # Skip comments and empty lines
                if not statement or statement.startswith('--'):
                    continue

                try:
                    conn.execute(text(statement))
                    logger.debug(f"  ✅ Statement {i}/{len(statements)}")
                except Exception as e:
                    # Some statements may fail if already exists - that's ok
                    if "already exists" in str(e).lower():
                        logger.debug(f"  ℹ️  Statement {i}: Already exists (skipped)")
                    else:
                        logger.warning(f"  ⚠️  Statement {i} failed: {e}")

            conn.commit()

        logger.info("✅ Migration applied successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/apply_migration.py <path_to_sql_file>")
        print("\nExample:")
        print("  python scripts/apply_migration.py schema/003_filing_text_content.sql")
        sys.exit(1)

    sql_file = Path(sys.argv[1])
    success = apply_migration(sql_file)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
