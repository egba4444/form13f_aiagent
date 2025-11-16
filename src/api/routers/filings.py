"""
Filings Router

REST endpoints for accessing filing data directly.
"""

from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import create_engine, text
from typing import Optional
import logging

from ..schemas import FilingResponse, FilingListResponse
from ..dependencies import get_database_url

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/filings", response_model=FilingListResponse)
async def list_filings(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(100, ge=1, le=1000, description="Items per page"),
    cik: Optional[str] = Query(None, description="Filter by manager CIK"),
    period: Optional[str] = Query(None, description="Filter by period of report (YYYY-MM-DD)")
):
    """
    List all filings with pagination and optional filtering.

    Returns Form 13F filings submitted by institutional investment managers.

    **Examples:**
    - `/api/v1/filings` - Get first 100 filings
    - `/api/v1/filings?cik=0001067983` - Get all filings from Berkshire Hathaway
    - `/api/v1/filings?period=2024-12-31` - Get all filings for Q4 2024
    - `/api/v1/filings?cik=0001067983&period=2024-12-31` - Specific manager and quarter
    """
    try:
        database_url = get_database_url()
        engine = create_engine(database_url, pool_pre_ping=True)

        with engine.connect() as conn:
            # Build WHERE clause
            where_clauses = []
            params = {}

            if cik:
                where_clauses.append("cik = :cik")
                params["cik"] = cik

            if period:
                where_clauses.append("period_of_report = :period")
                params["period"] = period

            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

            # Get total count
            count_query = text(f"SELECT COUNT(*) FROM filings {where_sql}")
            total = conn.execute(count_query, params).scalar()

            # Get paginated results
            offset = (page - 1) * page_size
            params["limit"] = page_size
            params["offset"] = offset

            query = text(f"""
                SELECT
                    accession_number,
                    cik,
                    filing_date,
                    period_of_report,
                    submission_type,
                    report_type,
                    total_value,
                    number_of_holdings
                FROM filings
                {where_sql}
                ORDER BY period_of_report DESC, filing_date DESC
                LIMIT :limit OFFSET :offset
            """)

            result = conn.execute(query, params)
            filings = [
                FilingResponse(
                    accession_number=row.accession_number,
                    cik=row.cik,
                    filing_date=str(row.filing_date),
                    period_of_report=str(row.period_of_report),
                    submission_type=row.submission_type,
                    report_type=row.report_type,
                    total_value=row.total_value,
                    number_of_holdings=row.number_of_holdings
                )
                for row in result
            ]

        return FilingListResponse(
            filings=filings,
            total=total,
            page=page,
            page_size=page_size
        )

    except Exception as e:
        logger.error(f"Error listing filings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve filings: {str(e)}")


@router.get("/filings/{accession_number}", response_model=FilingResponse)
async def get_filing(accession_number: str):
    """
    Get a specific filing by accession number.

    **Parameters:**
    - `accession_number`: SEC accession number (format: 0001193125-24-123456)

    **Example:**
    - `/api/v1/filings/0001193125-24-123456` - Get specific filing details
    """
    try:
        database_url = get_database_url()
        engine = create_engine(database_url, pool_pre_ping=True)

        with engine.connect() as conn:
            query = text("""
                SELECT
                    accession_number,
                    cik,
                    filing_date,
                    period_of_report,
                    submission_type,
                    report_type,
                    total_value,
                    number_of_holdings
                FROM filings
                WHERE accession_number = :accession_number
            """)
            result = conn.execute(query, {"accession_number": accession_number}).fetchone()

            if not result:
                raise HTTPException(
                    status_code=404,
                    detail=f"Filing with accession number {accession_number} not found"
                )

            return FilingResponse(
                accession_number=result.accession_number,
                cik=result.cik,
                filing_date=str(result.filing_date),
                period_of_report=str(result.period_of_report),
                submission_type=result.submission_type,
                report_type=result.report_type,
                total_value=result.total_value,
                number_of_holdings=result.number_of_holdings
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting filing {accession_number}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve filing: {str(e)}")
