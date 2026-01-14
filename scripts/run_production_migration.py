"""
Run database migration in production via API database connection.

This script connects directly to the production database and runs the migration.
Usage:
    # Get DATABASE_URL from Railway
    railway variables --service form13f-aiagent | grep DATABASE_URL

    # Set it locally and run
    set DATABASE_URL=postgresql://...
    python scripts/run_production_migration.py
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Run the filing_text_content migration."""

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("❌ DATABASE_URL environment variable not set")
        logger.info("Get it from Railway with: railway variables --service form13f-aiagent")
        return False

    # Read SQL file
    sql_file = Path(__file__).parent.parent / "schema" / "003_filing_text_content.sql"
    if not sql_file.exists():
        logger.error(f"❌ SQL file not found: {sql_file}")
        return False

    logger.info("Reading migration SQL...")
    sql_content = sql_file.read_text(encoding='utf-8')

    # Connect to database
    logger.info("Connecting to production database...")
    engine = create_engine(database_url)

    try:
        with engine.connect() as conn:
            logger.info("✅ Connected to database")

            # Execute SQL
            logger.info("Running migration...")
            conn.execute(text(sql_content))
            conn.commit()

            logger.info("✅ Migration completed successfully")

            # Verify table was created
            result = conn.execute(text("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_name = 'filing_text_content'
            """))
            table_exists = result.scalar() > 0

            if table_exists:
                logger.info("✅ filing_text_content table verified")
            else:
                logger.warning("⚠️  Table not found after migration")
                return False

            return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
