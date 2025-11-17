"""
Watchlist Service - Direct database operations for watchlist management.

This service provides direct database access for watchlist operations,
avoiding the need for HTTP calls within the same application.
"""

from typing import Optional, Dict, Any
from sqlalchemy import create_engine, text
import logging

logger = logging.getLogger(__name__)


class WatchlistService:
    """Service for managing user watchlists via direct database access."""

    def __init__(self, database_url: str):
        """
        Initialize watchlist service.

        Args:
            database_url: PostgreSQL connection string
        """
        self.database_url = database_url

    def add_item(
        self,
        user_id: str,
        item_type: str,
        cik: Optional[str] = None,
        cusip: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add a manager or security to user's watchlist.

        Args:
            user_id: User's UUID
            item_type: Type of item - must be "manager" or "security"
            cik: Manager CIK (required if item_type="manager")
            cusip: Security CUSIP (required if item_type="security")
            notes: Optional notes about the item

        Returns:
            Dict with success status and result data or error message
        """
        try:
            # Validate inputs
            if item_type not in ["manager", "security"]:
                return {
                    "success": False,
                    "error": "item_type must be 'manager' or 'security'"
                }

            if item_type == "manager" and not cik:
                return {
                    "success": False,
                    "error": "cik is required when item_type is 'manager'"
                }

            if item_type == "security" and not cusip:
                return {
                    "success": False,
                    "error": "cusip is required when item_type is 'security'"
                }

            engine = create_engine(self.database_url, pool_pre_ping=True)

            with engine.connect() as conn:
                # Get user's watchlist
                watchlist_result = conn.execute(
                    text("SELECT id FROM watchlists WHERE user_id = :user_id LIMIT 1"),
                    {"user_id": user_id}
                ).fetchone()

                if not watchlist_result:
                    return {
                        "success": False,
                        "error": "Watchlist not found for this user"
                    }

                watchlist_id = watchlist_result.id

                # Check if item already exists
                existing = conn.execute(
                    text("""
                        SELECT id FROM watchlist_items
                        WHERE watchlist_id = :watchlist_id
                        AND item_type = :item_type
                        AND (
                            (cik = :cik AND :cik IS NOT NULL) OR
                            (cusip = :cusip AND :cusip IS NOT NULL)
                        )
                    """),
                    {
                        "watchlist_id": watchlist_id,
                        "item_type": item_type,
                        "cik": cik,
                        "cusip": cusip
                    }
                ).fetchone()

                if existing:
                    return {
                        "success": False,
                        "error": "This item is already in your watchlist"
                    }

                # Verify the item exists in the database
                if item_type == "manager":
                    manager_check = conn.execute(
                        text("SELECT name FROM managers WHERE cik = :cik"),
                        {"cik": cik}
                    ).fetchone()

                    if not manager_check:
                        return {
                            "success": False,
                            "error": f"Manager with CIK {cik} not found in database"
                        }

                    item_name = manager_check.name

                elif item_type == "security":
                    security_check = conn.execute(
                        text("SELECT name FROM issuers WHERE cusip = :cusip"),
                        {"cusip": cusip}
                    ).fetchone()

                    if not security_check:
                        return {
                            "success": False,
                            "error": f"Security with CUSIP {cusip} not found in database"
                        }

                    item_name = security_check.name

                # Insert item
                result = conn.execute(
                    text("""
                        INSERT INTO watchlist_items (watchlist_id, item_type, cik, cusip, notes)
                        VALUES (:watchlist_id, :item_type, :cik, :cusip, :notes)
                        RETURNING id, added_at
                    """),
                    {
                        "watchlist_id": watchlist_id,
                        "item_type": item_type,
                        "cik": cik,
                        "cusip": cusip,
                        "notes": notes
                    }
                )
                conn.commit()

                row = result.fetchone()

                return {
                    "success": True,
                    "item": {
                        "id": row.id,
                        "item_type": item_type,
                        "cik": cik,
                        "cusip": cusip,
                        "name": item_name,
                        "notes": notes,
                        "added_at": row.added_at.isoformat()
                    },
                    "message": f"Successfully added {item_name} to your watchlist"
                }

        except Exception as e:
            logger.error(f"Error adding item to watchlist: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Error adding to watchlist: {str(e)}"
            }
