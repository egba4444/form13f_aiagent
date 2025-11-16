"""
Managers Router

REST endpoints for accessing manager data directly.
"""

from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import create_engine, text
from typing import Optional
import logging

from ..schemas import ManagerResponse, ManagerListResponse
from ..dependencies import get_database_url

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/managers", response_model=ManagerListResponse)
async def list_managers(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(100, ge=1, le=1000, description="Items per page"),
    name: Optional[str] = Query(None, description="Filter by manager name (case-insensitive partial match)"),
    cik: Optional[str] = Query(None, description="Filter by exact CIK")
):
    """
    List all managers with pagination and optional filtering.

    Returns paginated list of institutional investment managers who filed Form 13F.

    **Examples:**
    - `/api/v1/managers` - Get first 100 managers
    - `/api/v1/managers?page=2&page_size=50` - Get page 2 with 50 items
    - `/api/v1/managers?name=Berkshire` - Search for managers by name
    - `/api/v1/managers?cik=0001067983` - Get specific manager by CIK
    """
    try:
        database_url = get_database_url()
        engine = create_engine(database_url, pool_pre_ping=True)

        with engine.connect() as conn:
            # Build WHERE clause
            where_clauses = []
            params = {}

            if name:
                where_clauses.append("LOWER(name) LIKE LOWER(:name)")
                params["name"] = f"%{name}%"

            if cik:
                where_clauses.append("cik = :cik")
                params["cik"] = cik

            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

            # Get total count
            count_query = text(f"SELECT COUNT(*) FROM managers {where_sql}")
            total = conn.execute(count_query, params).scalar()

            # Get paginated results
            offset = (page - 1) * page_size
            params["limit"] = page_size
            params["offset"] = offset

            query = text(f"""
                SELECT cik, name
                FROM managers
                {where_sql}
                ORDER BY name
                LIMIT :limit OFFSET :offset
            """)

            result = conn.execute(query, params)
            managers = [
                ManagerResponse(cik=row.cik, name=row.name)
                for row in result
            ]

        return ManagerListResponse(
            managers=managers,
            total=total,
            page=page,
            page_size=page_size
        )

    except Exception as e:
        logger.error(f"Error listing managers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve managers: {str(e)}")


@router.get("/managers/{cik}", response_model=ManagerResponse)
async def get_manager(cik: str):
    """
    Get a specific manager by CIK.

    **Parameters:**
    - `cik`: Central Index Key (10 digits, e.g., "0001067983" for Berkshire Hathaway)

    **Example:**
    - `/api/v1/managers/0001067983` - Get Berkshire Hathaway details
    """
    try:
        database_url = get_database_url()
        engine = create_engine(database_url, pool_pre_ping=True)

        with engine.connect() as conn:
            query = text("SELECT cik, name FROM managers WHERE cik = :cik")
            result = conn.execute(query, {"cik": cik}).fetchone()

            if not result:
                raise HTTPException(status_code=404, detail=f"Manager with CIK {cik} not found")

            return ManagerResponse(cik=result.cik, name=result.name)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting manager {cik}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve manager: {str(e)}")
