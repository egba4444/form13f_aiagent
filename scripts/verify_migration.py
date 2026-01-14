"""Verify the filing_text_content table exists in production."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def verify_table():
    """Check if filing_text_content table exists."""

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("❌ DATABASE_URL not set")
        return False

    engine = create_engine(database_url)

    try:
        with engine.connect() as conn:
            # Check if table exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'filing_text_content'
                )
            """))
            table_exists = result.scalar()

            if table_exists:
                logger.info("✅ filing_text_content table EXISTS")

                # Get row count
                result = conn.execute(text("SELECT COUNT(*) FROM filing_text_content"))
                count = result.scalar()
                logger.info(f"✅ Table has {count} rows")

                # Check columns
                result = conn.execute(text("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = 'filing_text_content'
                    ORDER BY ordinal_position
                """))
                columns = result.fetchall()
                logger.info(f"✅ Table has {len(columns)} columns:")
                for col_name, col_type in columns:
                    logger.info(f"   - {col_name}: {col_type}")

                return True
            else:
                logger.error("❌ filing_text_content table DOES NOT EXIST")
                return False

    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False


if __name__ == "__main__":
    success = verify_table()
    sys.exit(0 if success else 1)
