-- Migration: Add filing_text_content table for RAG Phase 8
--
-- This table stores extracted text sections from Form 13F-HR XML filings.
-- Text is stored separately from structured holdings data to enable semantic search.
--
-- Storage strategy:
-- - Text content stored in PostgreSQL (1-2GB for all filings)
-- - XML files stored temporarily or for recent filings only
-- - Embeddings stored in Qdrant vector database

-- ============================================================
-- Table: filing_text_content
-- ============================================================

CREATE TABLE IF NOT EXISTS filing_text_content (
    id SERIAL PRIMARY KEY,

    -- Link to filing
    accession_number VARCHAR(25) NOT NULL REFERENCES filings(accession_number) ON DELETE CASCADE,

    -- Content type (for different sections of the filing)
    content_type VARCHAR(50) NOT NULL,
    -- Possible values:
    --   'cover_page_info'    - Manager details, addresses, period info
    --   'explanatory_notes'  - Additional information field (main qualitative text)
    --   'other_documents'    - Other included documents or exhibits
    --   'amendment_info'     - Amendment-specific explanatory text

    -- The actual text content
    text_content TEXT NOT NULL,

    -- XML file storage tracking
    xml_stored BOOLEAN DEFAULT FALSE,
    xml_storage_path TEXT,  -- Path if XML is stored (null if deleted)

    -- Metadata
    extracted_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Ensure we don't duplicate sections for same filing
    CONSTRAINT filing_text_content_unique UNIQUE (accession_number, content_type)
);

-- ============================================================
-- Indexes
-- ============================================================

-- Fast lookup by filing
CREATE INDEX idx_filing_text_accession
ON filing_text_content(accession_number);

-- Filter by content type
CREATE INDEX idx_filing_text_type
ON filing_text_content(content_type);

-- Full-text search index (PostgreSQL native, as fallback to RAG)
CREATE INDEX idx_filing_text_fts
ON filing_text_content USING GIN(to_tsvector('english', text_content));

-- Combined index for common query pattern
CREATE INDEX idx_filing_text_accession_type
ON filing_text_content(accession_number, content_type);

-- ============================================================
-- Trigger: Update updated_at timestamp
-- ============================================================

CREATE OR REPLACE FUNCTION update_filing_text_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_filing_text_updated_at
BEFORE UPDATE ON filing_text_content
FOR EACH ROW
EXECUTE FUNCTION update_filing_text_updated_at();

-- ============================================================
-- View: Enriched filing text with manager info
-- ============================================================

CREATE OR REPLACE VIEW filing_text_enriched AS
SELECT
    ftc.id,
    ftc.accession_number,
    ftc.content_type,
    ftc.text_content,
    ftc.xml_stored,
    ftc.xml_storage_path,
    ftc.extracted_at,

    -- Filing metadata
    f.cik,
    f.filing_date,
    f.period_of_report,
    f.total_value,
    f.number_of_holdings,

    -- Manager info
    m.name as manager_name

FROM filing_text_content ftc
JOIN filings f ON ftc.accession_number = f.accession_number
JOIN managers m ON f.cik = m.cik;

-- ============================================================
-- Helper functions
-- ============================================================

-- Function: Check if filing has text content
CREATE OR REPLACE FUNCTION filing_has_text_content(p_accession_number VARCHAR)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1
        FROM filing_text_content
        WHERE accession_number = p_accession_number
    );
END;
$$ LANGUAGE plpgsql;

-- Function: Get text content for a filing
CREATE OR REPLACE FUNCTION get_filing_text_sections(p_accession_number VARCHAR)
RETURNS TABLE (
    content_type VARCHAR,
    text_content TEXT,
    char_length INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ftc.content_type,
        ftc.text_content,
        LENGTH(ftc.text_content) as char_length
    FROM filing_text_content ftc
    WHERE ftc.accession_number = p_accession_number
    ORDER BY ftc.id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- Comments for documentation
-- ============================================================

COMMENT ON TABLE filing_text_content IS
'Stores extracted text sections from Form 13F-HR XML filings for RAG/semantic search';

COMMENT ON COLUMN filing_text_content.content_type IS
'Type of text section: cover_page_info, explanatory_notes, other_documents, amendment_info';

COMMENT ON COLUMN filing_text_content.xml_stored IS
'Whether original XML file is still stored (true for recent filings, false if deleted)';

COMMENT ON COLUMN filing_text_content.xml_storage_path IS
'Path to stored XML file if xml_stored=true, null if deleted';

-- ============================================================
-- Sample queries
-- ============================================================

-- Find all filings with explanatory notes
-- SELECT
--     m.name,
--     f.period_of_report,
--     LENGTH(ftc.text_content) as text_length
-- FROM filing_text_content ftc
-- JOIN filings f ON ftc.accession_number = f.accession_number
-- JOIN managers m ON f.cik = m.cik
-- WHERE ftc.content_type = 'explanatory_notes'
-- ORDER BY LENGTH(ftc.text_content) DESC
-- LIMIT 10;

-- Search text using PostgreSQL full-text search (fallback)
-- SELECT
--     m.name,
--     f.period_of_report,
--     ftc.content_type,
--     ts_headline('english', ftc.text_content, to_tsquery('english', 'Apple & iPhone'))
-- FROM filing_text_content ftc
-- JOIN filings f ON ftc.accession_number = f.accession_number
-- JOIN managers m ON f.cik = m.cik
-- WHERE to_tsvector('english', ftc.text_content) @@ to_tsquery('english', 'Apple & iPhone')
-- LIMIT 10;
