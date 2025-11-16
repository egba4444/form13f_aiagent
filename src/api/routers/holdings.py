"""
Holdings Router

REST endpoints for accessing holdings/positions data directly.
"""

from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import create_engine, text
from typing import Optional
import logging

from ..schemas import HoldingResponse, HoldingListResponse
from ..dependencies import get_database_url

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/holdings", response_model=HoldingListResponse)
async def list_holdings(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(100, ge=1, le=1000, description="Items per page"),
    accession_number: Optional[str] = Query(None, description="Filter by filing accession number"),
    cusip: Optional[str] = Query(None, description="Filter by security CUSIP"),
    issuer_name: Optional[str] = Query(None, description="Search by issuer name (partial match)")
):
    """
    List all holdings with pagination and optional filtering.

    Returns individual positions/holdings from Form 13F filings.

    **Examples:**
    - `/api/v1/holdings` - Get first 100 holdings
    - `/api/v1/holdings?accession_number=0001193125-24-123456` - Get all holdings in a filing
    - `/api/v1/holdings?cusip=037833100` - Get all holdings of Apple (CUSIP 037833100)
    - `/api/v1/holdings?issuer_name=Apple` - Search holdings by issuer name
    """
    try:
        database_url = get_database_url()
        engine = create_engine(database_url, pool_pre_ping=True)

        with engine.connect() as conn:
            # Build WHERE clause
            where_clauses = []
            params = {}

            if accession_number:
                where_clauses.append("h.accession_number = :accession_number")
                params["accession_number"] = accession_number

            if cusip:
                where_clauses.append("h.cusip = :cusip")
                params["cusip"] = cusip

            if issuer_name:
                where_clauses.append("LOWER(i.name) LIKE LOWER(:issuer_name)")
                params["issuer_name"] = f"%{issuer_name}%"

            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

            # Get total count
            count_query = text(f"""
                SELECT COUNT(*)
                FROM holdings h
                LEFT JOIN issuers i ON h.cusip = i.cusip
                {where_sql}
            """)
            total = conn.execute(count_query, params).scalar()

            # Get paginated results
            offset = (page - 1) * page_size
            params["limit"] = page_size
            params["offset"] = offset

            query = text(f"""
                SELECT
                    h.id,
                    h.accession_number,
                    h.cusip,
                    COALESCE(i.name, h.title_of_class) as title_of_class,
                    h.value,
                    h.shares_or_principal,
                    h.sh_or_prn,
                    h.investment_discretion,
                    h.put_call,
                    h.voting_authority_sole,
                    h.voting_authority_shared,
                    h.voting_authority_none
                FROM holdings h
                LEFT JOIN issuers i ON h.cusip = i.cusip
                {where_sql}
                ORDER BY h.value DESC
                LIMIT :limit OFFSET :offset
            """)

            result = conn.execute(query, params)
            holdings = [
                HoldingResponse(
                    id=row.id,
                    accession_number=row.accession_number,
                    cusip=row.cusip,
                    title_of_class=row.title_of_class,
                    value=row.value,
                    shares_or_principal=row.shares_or_principal,
                    sh_or_prn=row.sh_or_prn,
                    investment_discretion=row.investment_discretion,
                    put_call=row.put_call,
                    voting_authority_sole=row.voting_authority_sole,
                    voting_authority_shared=row.voting_authority_shared,
                    voting_authority_none=row.voting_authority_none
                )
                for row in result
            ]

        return HoldingListResponse(
            holdings=holdings,
            total=total,
            page=page,
            page_size=page_size
        )

    except Exception as e:
        logger.error(f"Error listing holdings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve holdings: {str(e)}")


@router.get("/holdings/{holding_id}", response_model=HoldingResponse)
async def get_holding(holding_id: int):
    """
    Get a specific holding by ID.

    **Parameters:**
    - `holding_id`: Internal holding ID

    **Example:**
    - `/api/v1/holdings/12345` - Get specific holding details
    """
    try:
        database_url = get_database_url()
        engine = create_engine(database_url, pool_pre_ping=True)

        with engine.connect() as conn:
            query = text("""
                SELECT
                    h.id,
                    h.accession_number,
                    h.cusip,
                    COALESCE(i.name, h.title_of_class) as title_of_class,
                    h.value,
                    h.shares_or_principal,
                    h.sh_or_prn,
                    h.investment_discretion,
                    h.put_call,
                    h.voting_authority_sole,
                    h.voting_authority_shared,
                    h.voting_authority_none
                FROM holdings h
                LEFT JOIN issuers i ON h.cusip = i.cusip
                WHERE h.id = :holding_id
            """)
            result = conn.execute(query, {"holding_id": holding_id}).fetchone()

            if not result:
                raise HTTPException(
                    status_code=404,
                    detail=f"Holding with ID {holding_id} not found"
                )

            return HoldingResponse(
                id=result.id,
                accession_number=result.accession_number,
                cusip=result.cusip,
                title_of_class=result.title_of_class,
                value=result.value,
                shares_or_principal=result.shares_or_principal,
                sh_or_prn=result.sh_or_prn,
                investment_discretion=result.investment_discretion,
                put_call=result.put_call,
                voting_authority_sole=result.voting_authority_sole,
                voting_authority_shared=result.voting_authority_shared,
                voting_authority_none=result.voting_authority_none
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting holding {holding_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve holding: {str(e)}")
