-- Schema Migration 004: Add 10-K Support and Companies Table
-- Purpose: Enable Form 10-K RAG functionality with company CIK/ticker mapping
-- Date: 2025-12-04

-- ============================================================================
-- 1. CREATE COMPANIES TABLE
-- ============================================================================
-- Stores public company information for CIK-to-ticker mapping
-- Source: SEC company_tickers.json (https://www.sec.gov/files/company_tickers.json)

CREATE TABLE IF NOT EXISTS companies (
    cik VARCHAR(10) PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    company_name VARCHAR(200) NOT NULL,
    exchange VARCHAR(10),              -- NASDAQ, NYSE, etc.
    is_sp500 BOOLEAN DEFAULT FALSE,    -- Flag for S&P 500 companies
    market_cap BIGINT,                 -- Market capitalization (optional)
    sector VARCHAR(50),                -- Sector classification (optional)
    added_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT companies_ticker_unique UNIQUE (ticker)
);

-- Indexes for companies table
CREATE INDEX IF NOT EXISTS idx_companies_ticker ON companies(ticker);
CREATE INDEX IF NOT EXISTS idx_companies_sp500 ON companies(is_sp500) WHERE is_sp500 = TRUE;
CREATE INDEX IF NOT EXISTS idx_companies_sector ON companies(sector);

COMMENT ON TABLE companies IS 'Public company information for CIK-to-ticker mapping';
COMMENT ON COLUMN companies.cik IS 'SEC Central Index Key (10-digit padded)';
COMMENT ON COLUMN companies.ticker IS 'Stock ticker symbol';
COMMENT ON COLUMN companies.is_sp500 IS 'True if company is in S&P 500 index';

-- ============================================================================
-- 2. EXTEND filing_text_content TABLE FOR 10-K SUPPORT
-- ============================================================================

-- Add new columns for 10-K support
ALTER TABLE filing_text_content
ADD COLUMN IF NOT EXISTS filing_type VARCHAR(10) DEFAULT '10-K',
ADD COLUMN IF NOT EXISTS document_url TEXT,
ADD COLUMN IF NOT EXISTS section_name VARCHAR(100),
ADD COLUMN IF NOT EXISTS cik_company VARCHAR(10);

-- Delete existing 13F text content (not useful for RAG - just structured tables)
-- Only if the filing_type column now exists
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'filing_text_content' AND column_name = 'filing_type') THEN
        DELETE FROM filing_text_content WHERE filing_type = '13F-HR' OR filing_type IS NULL;
        RAISE NOTICE 'Deleted existing 13F text content from filing_text_content table';
    END IF;
END
$$;

-- Update constraint to ensure filing_type is set
ALTER TABLE filing_text_content
ALTER COLUMN filing_type SET NOT NULL,
ALTER COLUMN filing_type SET DEFAULT '10-K';

-- Add indexes for 10-K queries
CREATE INDEX IF NOT EXISTS idx_filing_text_cik_company ON filing_text_content(cik_company);
CREATE INDEX IF NOT EXISTS idx_filing_text_section ON filing_text_content(section_name);
CREATE INDEX IF NOT EXISTS idx_filing_text_10k_lookup
    ON filing_text_content(cik_company, section_name);

-- Add comments
COMMENT ON COLUMN filing_text_content.filing_type IS 'Filing type: 10-K, 10-Q, etc. (13F removed - use SQL for structured data)';
COMMENT ON COLUMN filing_text_content.cik_company IS 'Company CIK (for 10-K) - different from manager CIK in 13F';
COMMENT ON COLUMN filing_text_content.section_name IS '10-K section: Item 1, Item 1A, Item 7, etc.';
COMMENT ON COLUMN filing_text_content.document_url IS 'URL to original SEC filing document';

-- ============================================================================
-- 3. INSERT TOP 10 S&P 500 COMPANIES (Placeholder)
-- ============================================================================
-- These will be populated by scripts/load_company_tickers.py
-- But we can pre-insert the top 10 for reference

INSERT INTO companies (cik, ticker, company_name, is_sp500, market_cap) VALUES
    ('0000320193', 'AAPL', 'Apple Inc.', TRUE, 3000000000000),
    ('0000789019', 'MSFT', 'Microsoft Corp', TRUE, 2800000000000),
    ('0001652044', 'GOOGL', 'Alphabet Inc.', TRUE, 1700000000000),
    ('0001018724', 'AMZN', 'Amazon.com Inc', TRUE, 1600000000000),
    ('0001045810', 'NVDA', 'NVIDIA Corp', TRUE, 1200000000000),
    ('0001326801', 'META', 'Meta Platforms Inc', TRUE, 900000000000),
    ('0001067983', 'BRK.B', 'Berkshire Hathaway Inc', TRUE, 850000000000),
    ('0001318605', 'TSLA', 'Tesla Inc', TRUE, 800000000000),
    ('0001403161', 'V', 'Visa Inc.', TRUE, 550000000000),
    ('0000731766', 'UNH', 'UnitedHealth Group Inc', TRUE, 500000000000)
ON CONFLICT (cik) DO UPDATE SET
    ticker = EXCLUDED.ticker,
    company_name = EXCLUDED.company_name,
    is_sp500 = EXCLUDED.is_sp500,
    market_cap = EXCLUDED.market_cap,
    updated_at = NOW();

-- ============================================================================
-- 4. VERIFICATION QUERIES
-- ============================================================================

-- Verify companies table
-- SELECT COUNT(*) as total_companies FROM companies;
-- SELECT COUNT(*) as sp500_companies FROM companies WHERE is_sp500 = TRUE;

-- Verify filing_text_content structure
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_name = 'filing_text_content'
-- ORDER BY ordinal_position;

-- Show sample data
-- SELECT * FROM companies WHERE is_sp500 = TRUE ORDER BY market_cap DESC LIMIT 5;

-- Migration 004 complete: 10-K support and companies table ready
-- Next steps:
-- 1. Run: python scripts/load_company_tickers.py --mark-sp500
-- 2. Run: python scripts/ingest_10k_filings.py --companies SP500_TOP10 --year 2023
-- 3. Run: python scripts/generate_embeddings.py --clear-first
