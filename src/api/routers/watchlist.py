"""
Watchlist API Endpoints.

Allows authenticated users to manage their watchlists.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import create_engine, text
from typing import List
import logging

from ..schemas import (
    WatchlistResponse,
    WatchlistItemCreate,
    WatchlistItemUpdate,
    WatchlistItemResponse
)
from ..dependencies import get_database_url
from ..middleware.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/watchlist", response_model=WatchlistResponse)
async def get_watchlist(
    user_id: str = Depends(get_current_user)
):
    """
    Get user's watchlist with all items and metrics.

    **Authentication Required:** Yes

    Returns the user's watchlist with enriched data including:
    - Manager names and latest portfolio values
    - Security names and latest prices
    - Period-over-period changes
    """
    try:
        database_url = get_database_url()
        engine = create_engine(database_url, pool_pre_ping=True)

        with engine.connect() as conn:
            # Ensure user exists in users table
            user_check = conn.execute(
                text("SELECT id FROM users WHERE id = :user_id"),
                {"user_id": user_id}
            ).fetchone()

            if not user_check:
                # Create user record if doesn't exist
                conn.execute(
                    text("INSERT INTO users (id, email) VALUES (:id, :email) ON CONFLICT DO NOTHING"),
                    {"id": user_id, "email": f"user_{user_id}@temp.com"}  # Temp email, will be updated
                )
                conn.commit()

            # Get watchlist
            watchlist_result = conn.execute(
                text("""
                    SELECT id, name, user_id, created_at, updated_at
                    FROM watchlists
                    WHERE user_id = :user_id
                    LIMIT 1
                """),
                {"user_id": user_id}
            ).fetchone()

            if not watchlist_result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Watchlist not found. This should have been created automatically."
                )

            watchlist_id = watchlist_result.id

            # Get watchlist items with details
            items_result = conn.execute(
                text("""
                    SELECT
                        wi.id,
                        wi.item_type,
                        wi.cik,
                        wi.cusip,
                        wi.notes,
                        wi.added_at,
                        CASE
                            WHEN wi.item_type = 'manager' THEN m.name
                            WHEN wi.item_type = 'security' THEN i.name
                        END as name,
                        CASE
                            WHEN wi.item_type = 'manager' THEN (
                                SELECT f.total_value
                                FROM filings f
                                WHERE f.cik = wi.cik
                                ORDER BY f.period_of_report DESC
                                LIMIT 1
                            )
                            WHEN wi.item_type = 'security' THEN (
                                SELECT SUM(h.value)
                                FROM holdings h
                                JOIN filings f ON h.accession_number = f.accession_number
                                WHERE h.cusip = wi.cusip
                                AND f.period_of_report = (
                                    SELECT MAX(period_of_report) FROM filings
                                )
                            )
                        END as latest_value,
                        CASE
                            WHEN wi.item_type = 'manager' THEN (
                                SELECT MAX(f.period_of_report)::TEXT
                                FROM filings f
                                WHERE f.cik = wi.cik
                            )
                            WHEN wi.item_type = 'security' THEN (
                                SELECT MAX(period_of_report)::TEXT FROM filings
                            )
                        END as latest_period
                    FROM watchlist_items wi
                    LEFT JOIN managers m ON wi.cik = m.cik
                    LEFT JOIN issuers i ON wi.cusip = i.cusip
                    WHERE wi.watchlist_id = :watchlist_id
                    ORDER BY wi.added_at DESC
                """),
                {"watchlist_id": watchlist_id}
            ).fetchall()

            items = []
            for row in items_result:
                items.append(WatchlistItemResponse(
                    id=row.id,
                    item_type=row.item_type,
                    cik=row.cik,
                    cusip=row.cusip,
                    name=row.name,
                    notes=row.notes,
                    added_at=row.added_at,
                    latest_value=row.latest_value,
                    value_change_percent=None,  # TODO: Calculate this
                    latest_period=row.latest_period
                ))

            return WatchlistResponse(
                id=watchlist_result.id,
                name=watchlist_result.name,
                user_id=watchlist_result.user_id,
                created_at=watchlist_result.created_at,
                updated_at=watchlist_result.updated_at,
                items=items
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting watchlist for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve watchlist: {str(e)}"
        )


@router.post("/watchlist/items", response_model=WatchlistItemResponse, status_code=status.HTTP_201_CREATED)
async def add_watchlist_item(
    item: WatchlistItemCreate,
    user_id: str = Depends(get_current_user)
):
    """
    Add a manager or security to user's watchlist.

    **Authentication Required:** Yes

    **Request Body:**
    - `item_type`: "manager" or "security"
    - `cik`: Manager CIK (required if type=manager)
    - `cusip`: Security CUSIP (required if type=security)
    - `notes`: Optional notes

    **Examples:**
    - Add Berkshire Hathaway: `{"item_type": "manager", "cik": "0001067983"}`
    - Add Apple: `{"item_type": "security", "cusip": "037833100"}`
    """
    try:
        # Validate item type
        if item.item_type not in ["manager", "security"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="item_type must be 'manager' or 'security'"
            )

        # Validate required fields
        if item.item_type == "manager" and not item.cik:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="cik is required when item_type is 'manager'"
            )

        if item.item_type == "security" and not item.cusip:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="cusip is required when item_type is 'security'"
            )

        database_url = get_database_url()
        engine = create_engine(database_url, pool_pre_ping=True)

        with engine.connect() as conn:
            # Get user's watchlist
            watchlist_result = conn.execute(
                text("SELECT id FROM watchlists WHERE user_id = :user_id LIMIT 1"),
                {"user_id": user_id}
            ).fetchone()

            if not watchlist_result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Watchlist not found"
                )

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
                    "item_type": item.item_type,
                    "cik": item.cik,
                    "cusip": item.cusip
                }
            ).fetchone()

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This item is already in your watchlist"
                )

            # Insert item
            result = conn.execute(
                text("""
                    INSERT INTO watchlist_items (watchlist_id, item_type, cik, cusip, notes)
                    VALUES (:watchlist_id, :item_type, :cik, :cusip, :notes)
                    RETURNING id, added_at
                """),
                {
                    "watchlist_id": watchlist_id,
                    "item_type": item.item_type,
                    "cik": item.cik,
                    "cusip": item.cusip,
                    "notes": item.notes
                }
            )
            conn.commit()

            inserted = result.fetchone()

            # Get name
            if item.item_type == "manager":
                name_result = conn.execute(
                    text("SELECT name FROM managers WHERE cik = :cik"),
                    {"cik": item.cik}
                ).fetchone()
                name = name_result.name if name_result else None
            else:
                name_result = conn.execute(
                    text("SELECT name FROM issuers WHERE cusip = :cusip"),
                    {"cusip": item.cusip}
                ).fetchone()
                name = name_result.name if name_result else None

            return WatchlistItemResponse(
                id=inserted.id,
                item_type=item.item_type,
                cik=item.cik,
                cusip=item.cusip,
                name=name,
                notes=item.notes,
                added_at=inserted.added_at,
                latest_value=None,
                value_change_percent=None,
                latest_period=None
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding watchlist item: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add item to watchlist: {str(e)}"
        )


@router.delete("/watchlist/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_watchlist_item(
    item_id: int,
    user_id: str = Depends(get_current_user)
):
    """
    Remove an item from user's watchlist.

    **Authentication Required:** Yes
    """
    try:
        database_url = get_database_url()
        engine = create_engine(database_url, pool_pre_ping=True)

        with engine.connect() as conn:
            # Verify item belongs to user's watchlist
            check_result = conn.execute(
                text("""
                    SELECT wi.id
                    FROM watchlist_items wi
                    JOIN watchlists w ON wi.watchlist_id = w.id
                    WHERE wi.id = :item_id AND w.user_id = :user_id
                """),
                {"item_id": item_id, "user_id": user_id}
            ).fetchone()

            if not check_result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Watchlist item not found"
                )

            # Delete item
            conn.execute(
                text("DELETE FROM watchlist_items WHERE id = :item_id"),
                {"item_id": item_id}
            )
            conn.commit()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing watchlist item {item_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove item from watchlist: {str(e)}"
        )


@router.patch("/watchlist/items/{item_id}", response_model=WatchlistItemResponse)
async def update_watchlist_item(
    item_id: int,
    update: WatchlistItemUpdate,
    user_id: str = Depends(get_current_user)
):
    """
    Update notes for a watchlist item.

    **Authentication Required:** Yes
    """
    try:
        database_url = get_database_url()
        engine = create_engine(database_url, pool_pre_ping=True)

        with engine.connect() as conn:
            # Verify item belongs to user and update
            result = conn.execute(
                text("""
                    UPDATE watchlist_items wi
                    SET notes = :notes
                    FROM watchlists w
                    WHERE wi.id = :item_id
                    AND wi.watchlist_id = w.id
                    AND w.user_id = :user_id
                    RETURNING wi.id, wi.item_type, wi.cik, wi.cusip, wi.notes, wi.added_at
                """),
                {"item_id": item_id, "notes": update.notes, "user_id": user_id}
            )
            conn.commit()

            updated = result.fetchone()

            if not updated:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Watchlist item not found"
                )

            # Get name
            if updated.item_type == "manager":
                name_result = conn.execute(
                    text("SELECT name FROM managers WHERE cik = :cik"),
                    {"cik": updated.cik}
                ).fetchone()
                name = name_result.name if name_result else None
            else:
                name_result = conn.execute(
                    text("SELECT name FROM issuers WHERE cusip = :cusip"),
                    {"cusip": updated.cusip}
                ).fetchone()
                name = name_result.name if name_result else None

            return WatchlistItemResponse(
                id=updated.id,
                item_type=updated.item_type,
                cik=updated.cik,
                cusip=updated.cusip,
                name=name,
                notes=updated.notes,
                added_at=updated.added_at,
                latest_value=None,
                value_change_percent=None,
                latest_period=None
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating watchlist item {item_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update watchlist item: {str(e)}"
        )
