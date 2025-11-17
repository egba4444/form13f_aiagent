-- Auth and Watchlist Schema Migration
-- Adds user authentication and watchlist functionality
-- Created: 2025-01-16

-- ============================================================================
-- Table: users
-- Stores user profile information (syncs with Supabase Auth)
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,  -- Must match Supabase Auth user ID
    email VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,

    CONSTRAINT users_email_lowercase CHECK (email = LOWER(email))
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at DESC);

-- ============================================================================
-- Table: watchlists
-- Stores user watchlists (one per user for now, expandable later)
-- ============================================================================

CREATE TABLE IF NOT EXISTS watchlists (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL DEFAULT 'My Watchlist',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT watchlist_user_unique UNIQUE (user_id, name)
);

CREATE INDEX IF NOT EXISTS idx_watchlists_user_id ON watchlists(user_id);

-- ============================================================================
-- Table: watchlist_items
-- Stores individual items in watchlists (managers OR securities)
-- ============================================================================

CREATE TABLE IF NOT EXISTS watchlist_items (
    id SERIAL PRIMARY KEY,
    watchlist_id INTEGER NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE,
    item_type VARCHAR(20) NOT NULL CHECK (item_type IN ('manager', 'security')),

    -- For managers
    cik VARCHAR(10) REFERENCES managers(cik) ON DELETE CASCADE,

    -- For securities
    cusip VARCHAR(9) REFERENCES issuers(cusip) ON DELETE CASCADE,

    -- Metadata
    notes TEXT,
    added_at TIMESTAMP DEFAULT NOW(),

    -- Business logic constraints
    CONSTRAINT watchlist_item_type_check CHECK (
        (item_type = 'manager' AND cik IS NOT NULL AND cusip IS NULL) OR
        (item_type = 'security' AND cusip IS NOT NULL AND cik IS NULL)
    ),

    -- Prevent duplicates in same watchlist
    CONSTRAINT watchlist_item_unique UNIQUE (watchlist_id, item_type, cik, cusip)
);

CREATE INDEX IF NOT EXISTS idx_watchlist_items_watchlist_id ON watchlist_items(watchlist_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_items_cik ON watchlist_items(cik) WHERE cik IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_watchlist_items_cusip ON watchlist_items(cusip) WHERE cusip IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_watchlist_items_added_at ON watchlist_items(added_at DESC);

-- ============================================================================
-- Trigger: Update watchlist updated_at on item changes
-- ============================================================================

CREATE OR REPLACE FUNCTION update_watchlist_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE watchlists
    SET updated_at = NOW()
    WHERE id = NEW.watchlist_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_watchlist_timestamp ON watchlist_items;
CREATE TRIGGER trigger_update_watchlist_timestamp
    AFTER INSERT OR UPDATE OR DELETE ON watchlist_items
    FOR EACH ROW
    EXECUTE FUNCTION update_watchlist_timestamp();

-- ============================================================================
-- Function: Auto-create default watchlist for new users
-- ============================================================================

CREATE OR REPLACE FUNCTION create_default_watchlist()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO watchlists (user_id, name)
    VALUES (NEW.id, 'My Watchlist');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_create_default_watchlist ON users;
CREATE TRIGGER trigger_create_default_watchlist
    AFTER INSERT ON users
    FOR EACH ROW
    EXECUTE FUNCTION create_default_watchlist();

-- ============================================================================
-- Helpful comments for common queries
-- ============================================================================

-- Get user's watchlist with items:
--   SELECT w.*,
--          json_agg(
--              json_build_object(
--                  'id', wi.id,
--                  'type', wi.item_type,
--                  'cik', wi.cik,
--                  'cusip', wi.cusip,
--                  'notes', wi.notes,
--                  'added_at', wi.added_at
--              )
--          ) as items
--   FROM watchlists w
--   LEFT JOIN watchlist_items wi ON w.id = wi.watchlist_id
--   WHERE w.user_id = :user_id
--   GROUP BY w.id;

-- Get watchlist with manager/security details:
--   SELECT
--       wi.id,
--       wi.item_type,
--       wi.notes,
--       wi.added_at,
--       CASE
--           WHEN wi.item_type = 'manager' THEN m.name
--           WHEN wi.item_type = 'security' THEN i.name
--       END as name,
--       wi.cik,
--       wi.cusip
--   FROM watchlist_items wi
--   LEFT JOIN managers m ON wi.cik = m.cik
--   LEFT JOIN issuers i ON wi.cusip = i.cusip
--   WHERE wi.watchlist_id = :watchlist_id
--   ORDER BY wi.added_at DESC;
