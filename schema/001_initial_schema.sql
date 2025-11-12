-- Form 13F Database Schema
-- Initial schema with managers, issuers, filings, and holdings
-- Created: 2025-01-11

-- ============================================================================
-- Table: managers
-- Stores institutional investment manager information
-- ============================================================================

CREATE TABLE IF NOT EXISTS managers (
    cik VARCHAR(10) PRIMARY KEY,
    name VARCHAR(150) NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_managers_cik ON managers(cik);

-- ============================================================================
-- Table: issuers
-- Stores security issuer information (companies)
-- ============================================================================

CREATE TABLE IF NOT EXISTS issuers (
    cusip VARCHAR(9) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    figi VARCHAR(12)  -- Financial Instrument Global Identifier (optional)
);

CREATE INDEX IF NOT EXISTS ix_issuers_cusip ON issuers(cusip);
CREATE INDEX IF NOT EXISTS ix_issuers_figi ON issuers(figi);

-- ============================================================================
-- Table: filings
-- Stores Form 13F filing metadata
-- ============================================================================

CREATE TABLE IF NOT EXISTS filings (
    accession_number VARCHAR(25) PRIMARY KEY,
    cik VARCHAR(10) NOT NULL REFERENCES managers(cik) ON DELETE CASCADE,
    filing_date DATE NOT NULL,
    period_of_report DATE NOT NULL,
    submission_type VARCHAR(10) NOT NULL,
    report_type VARCHAR(30) NOT NULL,
    total_value BIGINT NOT NULL,
    number_of_holdings INTEGER NOT NULL,

    -- Constraints
    CONSTRAINT check_total_value_positive CHECK (total_value >= 0),
    CONSTRAINT check_holdings_count_positive CHECK (number_of_holdings >= 0)
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS ix_filings_accession_number ON filings(accession_number);
CREATE INDEX IF NOT EXISTS ix_filings_cik ON filings(cik);
CREATE INDEX IF NOT EXISTS ix_filings_filing_date ON filings(filing_date);
CREATE INDEX IF NOT EXISTS ix_filings_period_of_report ON filings(period_of_report);
CREATE INDEX IF NOT EXISTS ix_filings_total_value ON filings(total_value);

-- Composite indexes for common JOIN and WHERE patterns
CREATE INDEX IF NOT EXISTS ix_filings_cik_period ON filings(cik, period_of_report);
CREATE INDEX IF NOT EXISTS ix_filings_period_value ON filings(period_of_report, total_value);

-- ============================================================================
-- Table: holdings
-- Stores individual holdings (positions) within each filing
-- ============================================================================

CREATE TABLE IF NOT EXISTS holdings (
    id SERIAL PRIMARY KEY,
    accession_number VARCHAR(25) NOT NULL REFERENCES filings(accession_number) ON DELETE CASCADE,
    cusip VARCHAR(9) NOT NULL REFERENCES issuers(cusip) ON DELETE RESTRICT,
    title_of_class VARCHAR(150) NOT NULL,
    value BIGINT NOT NULL,
    shares_or_principal BIGINT NOT NULL,
    sh_or_prn VARCHAR(10) NOT NULL,  -- 'SH' (shares) or 'PRN' (principal amount)
    investment_discretion VARCHAR(10) NOT NULL,  -- 'SOLE', 'DFND', 'SHARED'
    put_call VARCHAR(10),  -- NULL, 'PUT', or 'CALL'
    voting_authority_sole BIGINT NOT NULL DEFAULT 0,
    voting_authority_shared BIGINT NOT NULL DEFAULT 0,
    voting_authority_none BIGINT NOT NULL DEFAULT 0,

    -- Constraints
    CONSTRAINT check_value_positive CHECK (value >= 0),
    CONSTRAINT check_shares_positive CHECK (shares_or_principal >= 0),
    CONSTRAINT check_voting_sole_positive CHECK (voting_authority_sole >= 0),
    CONSTRAINT check_voting_shared_positive CHECK (voting_authority_shared >= 0),
    CONSTRAINT check_voting_none_positive CHECK (voting_authority_none >= 0)
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS ix_holdings_accession_number ON holdings(accession_number);
CREATE INDEX IF NOT EXISTS ix_holdings_cusip ON holdings(cusip);
CREATE INDEX IF NOT EXISTS ix_holdings_value ON holdings(value);

-- Composite indexes for common JOIN and WHERE patterns
CREATE INDEX IF NOT EXISTS ix_holdings_accession_cusip ON holdings(accession_number, cusip);
CREATE INDEX IF NOT EXISTS ix_holdings_cusip_value ON holdings(cusip, value);

-- Descending index for "top holdings by value" queries
CREATE INDEX IF NOT EXISTS ix_holdings_value_desc ON holdings(value DESC);

-- ============================================================================
-- Helpful comments for query patterns
-- ============================================================================

-- Common queries this schema supports efficiently:
--
-- 1. Find all holdings for a manager in a specific quarter:
--    SELECT h.* FROM holdings h
--    JOIN filings f ON h.accession_number = f.accession_number
--    WHERE f.cik = '0001067983' AND f.period_of_report = '2024-12-31';
--
-- 2. Top 10 holdings by value across all managers:
--    SELECT h.*, i.name FROM holdings h
--    JOIN issuers i ON h.cusip = i.cusip
--    ORDER BY h.value DESC LIMIT 10;
--
-- 3. Total portfolio value for all managers in Q4 2024:
--    SELECT m.name, f.total_value FROM filings f
--    JOIN managers m ON f.cik = m.cik
--    WHERE f.period_of_report BETWEEN '2024-10-01' AND '2024-12-31'
--    ORDER BY f.total_value DESC;
--
-- 4. Find all managers holding a specific security (e.g., CUSIP):
--    SELECT DISTINCT m.name, f.period_of_report, h.value, h.shares_or_principal
--    FROM holdings h
--    JOIN filings f ON h.accession_number = f.accession_number
--    JOIN managers m ON f.cik = m.cik
--    WHERE h.cusip = '037833100'  -- Apple Inc
--    ORDER BY f.period_of_report DESC;
