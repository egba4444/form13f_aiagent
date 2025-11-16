"""
Analytics Endpoints Router

Advanced analytics endpoints for portfolio analysis, position tracking,
and institutional ownership insights.
"""

from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import create_engine, text
from typing import Optional
import logging

from ..schemas import (
    PortfolioCompositionResponse,
    PortfolioHolding,
    PositionHistoryResponse,
    PositionChange,
    TopMoversResponse,
    TopMover,
    SecurityAnalysisResponse,
    SecurityOwnership
)
from ..dependencies import get_database_url

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/analytics/portfolio/{cik}", response_model=PortfolioCompositionResponse)
async def get_portfolio_composition(
    cik: str,
    period: Optional[str] = Query(None, description="Period of report (YYYY-MM-DD). Defaults to latest."),
    top_n: int = Query(10, ge=1, le=50, description="Number of top holdings to return")
):
    """
    Get portfolio composition for a manager.

    Returns top holdings, concentration metrics, and portfolio statistics.

    **Examples:**
    - `/api/v1/analytics/portfolio/0001067983` - Berkshire Hathaway's latest portfolio
    - `/api/v1/analytics/portfolio/0001067983?period=2025-06-30&top_n=20` - Top 20 holdings for Q2 2025
    """
    try:
        database_url = get_database_url()
        engine = create_engine(database_url, pool_pre_ping=True)

        with engine.connect() as conn:
            # Get manager name
            manager_result = conn.execute(
                text("SELECT name FROM managers WHERE cik = :cik"),
                {"cik": cik}
            ).fetchone()

            if not manager_result:
                raise HTTPException(status_code=404, detail=f"Manager with CIK {cik} not found")

            manager_name = manager_result.name

            # Get period (use latest if not specified)
            if not period:
                period_result = conn.execute(
                    text("""
                        SELECT period_of_report
                        FROM filings
                        WHERE cik = :cik
                        ORDER BY period_of_report DESC
                        LIMIT 1
                    """),
                    {"cik": cik}
                ).fetchone()

                if not period_result:
                    raise HTTPException(status_code=404, detail=f"No filings found for CIK {cik}")

                period = str(period_result.period_of_report)

            # Get filing
            filing_result = conn.execute(
                text("""
                    SELECT accession_number, total_value, number_of_holdings
                    FROM filings
                    WHERE cik = :cik AND period_of_report = :period
                """),
                {"cik": cik, "period": period}
            ).fetchone()

            if not filing_result:
                raise HTTPException(
                    status_code=404,
                    detail=f"No filing found for CIK {cik} in period {period}"
                )

            accession_number = filing_result.accession_number
            total_value = filing_result.total_value
            number_of_holdings = filing_result.number_of_holdings

            # Get top holdings
            holdings_result = conn.execute(
                text("""
                    SELECT
                        h.cusip,
                        COALESCE(i.name, h.title_of_class) as title_of_class,
                        h.value,
                        h.shares_or_principal
                    FROM holdings h
                    LEFT JOIN issuers i ON h.cusip = i.cusip
                    WHERE h.accession_number = :accession_number
                    ORDER BY h.value DESC
                    LIMIT :top_n
                """),
                {"accession_number": accession_number, "top_n": top_n}
            )

            top_holdings = []
            for row in holdings_result:
                percent_of_portfolio = (row.value / total_value * 100) if total_value > 0 else 0
                top_holdings.append(PortfolioHolding(
                    cusip=row.cusip,
                    title_of_class=row.title_of_class,
                    value=row.value,
                    shares_or_principal=row.shares_or_principal,
                    percent_of_portfolio=round(percent_of_portfolio, 2)
                ))

            # Calculate concentration metrics
            top5_value = sum(h.value for h in top_holdings[:5]) if len(top_holdings) >= 5 else sum(h.value for h in top_holdings)
            top10_value = sum(h.value for h in top_holdings[:10]) if len(top_holdings) >= 10 else sum(h.value for h in top_holdings)

            concentration = {
                "top5_percent": round((top5_value / total_value * 100) if total_value > 0 else 0, 2),
                "top10_percent": round((top10_value / total_value * 100) if total_value > 0 else 0, 2)
            }

            return PortfolioCompositionResponse(
                cik=cik,
                manager_name=manager_name,
                period=period,
                total_value=total_value,
                number_of_holdings=number_of_holdings,
                top_holdings=top_holdings,
                concentration=concentration
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting portfolio composition for CIK {cik}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve portfolio composition: {str(e)}")


@router.get("/analytics/security/{cusip}", response_model=SecurityAnalysisResponse)
async def get_security_analysis(
    cusip: str,
    period: Optional[str] = Query(None, description="Period of report (YYYY-MM-DD). Defaults to latest."),
    top_n: int = Query(10, ge=1, le=50, description="Number of top holders to return")
):
    """
    Get institutional ownership analysis for a security.

    Returns total institutional holdings, top holders, and concentration metrics.

    **Examples:**
    - `/api/v1/analytics/security/037833100` - Apple (AAPL) institutional ownership
    - `/api/v1/analytics/security/67066G104?top_n=20` - NVIDIA top 20 holders
    """
    try:
        database_url = get_database_url()
        engine = create_engine(database_url, pool_pre_ping=True)

        with engine.connect() as conn:
            # Get security name
            issuer_result = conn.execute(
                text("SELECT name FROM issuers WHERE cusip = :cusip"),
                {"cusip": cusip}
            ).fetchone()

            if not issuer_result:
                raise HTTPException(status_code=404, detail=f"Security with CUSIP {cusip} not found")

            title_of_class = issuer_result.name

            # Get period (use latest if not specified)
            if not period:
                period_result = conn.execute(
                    text("SELECT MAX(period_of_report) as period FROM filings")
                ).fetchone()
                period = str(period_result.period)

            # Get total institutional holdings
            totals_result = conn.execute(
                text("""
                    SELECT
                        SUM(h.shares_or_principal) as total_shares,
                        SUM(h.value) as total_value,
                        COUNT(DISTINCT h.accession_number) as holder_count
                    FROM holdings h
                    JOIN filings f ON h.accession_number = f.accession_number
                    WHERE h.cusip = :cusip AND f.period_of_report = :period
                """),
                {"cusip": cusip, "period": period}
            ).fetchone()

            total_shares = totals_result.total_shares or 0
            total_value = totals_result.total_value or 0
            holder_count = totals_result.holder_count or 0

            # Get top holders
            holders_result = conn.execute(
                text("""
                    SELECT
                        f.cik,
                        m.name as manager_name,
                        h.shares_or_principal as shares,
                        h.value
                    FROM holdings h
                    JOIN filings f ON h.accession_number = f.accession_number
                    JOIN managers m ON f.cik = m.cik
                    WHERE h.cusip = :cusip AND f.period_of_report = :period
                    ORDER BY h.value DESC
                    LIMIT :top_n
                """),
                {"cusip": cusip, "period": period, "top_n": top_n}
            )

            top_holders = []
            for row in holders_result:
                percent_of_total = (row.value / total_value * 100) if total_value > 0 else 0
                top_holders.append(SecurityOwnership(
                    cik=row.cik,
                    manager_name=row.manager_name,
                    shares=row.shares,
                    value=row.value,
                    percent_of_total=round(percent_of_total, 2)
                ))

            # Calculate concentration
            top5_value = sum(h.value for h in top_holders[:5]) if len(top_holders) >= 5 else sum(h.value for h in top_holders)
            top10_value = sum(h.value for h in top_holders[:10]) if len(top_holders) >= 10 else sum(h.value for h in top_holders)

            concentration = {
                "top5_percent": round((top5_value / total_value * 100) if total_value > 0 else 0, 2),
                "top10_percent": round((top10_value / total_value * 100) if total_value > 0 else 0, 2),
                "herfindahl_index": round(sum((h.value / total_value) ** 2 for h in top_holders) if total_value > 0 else 0, 4)
            }

            return SecurityAnalysisResponse(
                cusip=cusip,
                title_of_class=title_of_class,
                period=period,
                total_institutional_shares=total_shares,
                total_institutional_value=total_value,
                number_of_holders=holder_count,
                top_holders=top_holders,
                concentration=concentration
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting security analysis for CUSIP {cusip}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve security analysis: {str(e)}")


@router.get("/analytics/movers", response_model=TopMoversResponse)
async def get_top_movers(
    period_from: Optional[str] = Query(None, description="Starting period (YYYY-MM-DD)"),
    period_to: Optional[str] = Query(None, description="Ending period (YYYY-MM-DD)"),
    top_n: int = Query(10, ge=1, le=50, description="Number of top movers to return")
):
    """
    Get biggest position changes between two periods.

    Returns positions with the largest increases, decreases, new positions, and closed positions.

    **Examples:**
    - `/api/v1/analytics/movers` - Latest quarter changes
    - `/api/v1/analytics/movers?period_from=2024-12-31&period_to=2025-06-30&top_n=20` - Top 20 movers
    """
    try:
        database_url = get_database_url()
        engine = create_engine(database_url, pool_pre_ping=True)

        with engine.connect() as conn:
            # Get latest two periods if not specified
            if not period_from or not period_to:
                periods_result = conn.execute(
                    text("""
                        SELECT DISTINCT period_of_report
                        FROM filings
                        ORDER BY period_of_report DESC
                        LIMIT 2
                    """)
                ).fetchall()

                if len(periods_result) < 2:
                    raise HTTPException(status_code=404, detail="Insufficient periods for comparison")

                period_to = str(periods_result[0].period_of_report)
                period_from = str(periods_result[1].period_of_report)

            # Get position changes
            changes_result = conn.execute(
                text("""
                    WITH current_positions AS (
                        SELECT
                            f.cik,
                            m.name as manager_name,
                            h.cusip,
                            COALESCE(i.name, h.title_of_class) as title_of_class,
                            h.value as current_value,
                            h.shares_or_principal as current_shares
                        FROM holdings h
                        JOIN filings f ON h.accession_number = f.accession_number
                        JOIN managers m ON f.cik = m.cik
                        LEFT JOIN issuers i ON h.cusip = i.cusip
                        WHERE f.period_of_report = :period_to
                    ),
                    previous_positions AS (
                        SELECT
                            f.cik,
                            h.cusip,
                            h.value as previous_value,
                            h.shares_or_principal as previous_shares
                        FROM holdings h
                        JOIN filings f ON h.accession_number = f.accession_number
                        WHERE f.period_of_report = :period_from
                    )
                    SELECT
                        c.cik,
                        c.manager_name,
                        c.cusip,
                        c.title_of_class,
                        COALESCE(p.previous_value, 0) as previous_value,
                        c.current_value,
                        c.current_value - COALESCE(p.previous_value, 0) as value_change,
                        COALESCE(p.previous_shares, 0) as previous_shares,
                        c.current_shares,
                        c.current_shares - COALESCE(p.previous_shares, 0) as shares_change
                    FROM current_positions c
                    LEFT JOIN previous_positions p ON c.cik = p.cik AND c.cusip = p.cusip
                    WHERE c.current_value - COALESCE(p.previous_value, 0) != 0
                        AND COALESCE(p.previous_value, 0) > 0
                    ORDER BY ABS(c.current_value - COALESCE(p.previous_value, 0)) DESC
                    LIMIT :top_n_increases
                """),
                {"period_from": period_from, "period_to": period_to, "top_n_increases": top_n * 2}
            ).fetchall()

            # Split into increases and decreases
            increases = []
            decreases = []

            for row in changes_result:
                value_change_percent = (row.value_change / row.previous_value * 100) if row.previous_value > 0 else 0
                shares_change_percent = (row.shares_change / row.previous_shares * 100) if row.previous_shares > 0 else 0

                mover = TopMover(
                    cik=row.cik,
                    manager_name=row.manager_name,
                    cusip=row.cusip,
                    title_of_class=row.title_of_class,
                    previous_value=row.previous_value,
                    current_value=row.current_value,
                    value_change=row.value_change,
                    value_change_percent=round(value_change_percent, 2),
                    previous_shares=row.previous_shares,
                    current_shares=row.current_shares,
                    shares_change=row.shares_change,
                    shares_change_percent=round(shares_change_percent, 2)
                )

                if row.value_change > 0:
                    increases.append(mover)
                else:
                    decreases.append(mover)

            # Limit to top_n for each category
            increases = sorted(increases, key=lambda x: x.value_change, reverse=True)[:top_n]
            decreases = sorted(decreases, key=lambda x: x.value_change)[:top_n]

            # Get new positions
            new_positions_result = conn.execute(
                text("""
                    SELECT
                        f.cik,
                        m.name as manager_name,
                        h.cusip,
                        COALESCE(i.name, h.title_of_class) as title_of_class,
                        h.value,
                        h.shares_or_principal as shares
                    FROM holdings h
                    JOIN filings f ON h.accession_number = f.accession_number
                    JOIN managers m ON f.cik = m.cik
                    LEFT JOIN issuers i ON h.cusip = i.cusip
                    WHERE f.period_of_report = :period_to
                        AND NOT EXISTS (
                            SELECT 1 FROM holdings h2
                            JOIN filings f2 ON h2.accession_number = f2.accession_number
                            WHERE f2.cik = f.cik
                                AND h2.cusip = h.cusip
                                AND f2.period_of_report = :period_from
                        )
                    ORDER BY h.value DESC
                    LIMIT :top_n
                """),
                {"period_from": period_from, "period_to": period_to, "top_n": top_n}
            ).fetchall()

            new_positions = [
                {
                    "cik": row.cik,
                    "manager_name": row.manager_name,
                    "cusip": row.cusip,
                    "title_of_class": row.title_of_class,
                    "value": row.value,
                    "shares": row.shares
                }
                for row in new_positions_result
            ]

            # Get closed positions
            closed_positions_result = conn.execute(
                text("""
                    SELECT
                        f.cik,
                        m.name as manager_name,
                        h.cusip,
                        COALESCE(i.name, h.title_of_class) as title_of_class,
                        h.value,
                        h.shares_or_principal as shares
                    FROM holdings h
                    JOIN filings f ON h.accession_number = f.accession_number
                    JOIN managers m ON f.cik = m.cik
                    LEFT JOIN issuers i ON h.cusip = i.cusip
                    WHERE f.period_of_report = :period_from
                        AND NOT EXISTS (
                            SELECT 1 FROM holdings h2
                            JOIN filings f2 ON h2.accession_number = f2.accession_number
                            WHERE f2.cik = f.cik
                                AND h2.cusip = h.cusip
                                AND f2.period_of_report = :period_to
                        )
                    ORDER BY h.value DESC
                    LIMIT :top_n
                """),
                {"period_from": period_from, "period_to": period_to, "top_n": top_n}
            ).fetchall()

            closed_positions = [
                {
                    "cik": row.cik,
                    "manager_name": row.manager_name,
                    "cusip": row.cusip,
                    "title_of_class": row.title_of_class,
                    "value": row.value,
                    "shares": row.shares
                }
                for row in closed_positions_result
            ]

            return TopMoversResponse(
                period_from=period_from,
                period_to=period_to,
                biggest_increases=increases,
                biggest_decreases=decreases,
                new_positions=new_positions,
                closed_positions=closed_positions
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting top movers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve top movers: {str(e)}")
