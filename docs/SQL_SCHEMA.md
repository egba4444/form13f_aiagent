# PostgreSQL Database Schema

## Overview

This document details the PostgreSQL database schema for the Form 13F AI Agent.

---

## Core Tables

### 1. `filings`

```sql
CREATE TABLE filings (
    accession_number VARCHAR(20) PRIMARY KEY,
    cik VARCHAR(10) NOT NULL,
    manager_name VARCHAR(255) NOT NULL,
    filing_date DATE NOT NULL,
    period_of_report DATE NOT NULL,
    total_value_thousands BIGINT NOT NULL,
    number_of_holdings INTEGER NOT NULL,
    raw_xml_url TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_filings_cik ON filings(cik);
CREATE INDEX idx_filings_period ON filings(period_of_report);
CREATE INDEX idx_filings_cik_period ON filings(cik, period_of_report DESC);
```

### 2. `holdings`

```sql
CREATE TABLE holdings (
    id SERIAL PRIMARY KEY,
    accession_number VARCHAR(20) REFERENCES filings(accession_number) ON DELETE CASCADE,
    cusip VARCHAR(9) NOT NULL,
    issuer_name VARCHAR(255) NOT NULL,
    ticker VARCHAR(10),
    value_thousands BIGINT NOT NULL,
    shares_or_principal BIGINT NOT NULL,
    sh_or_prn VARCHAR(3),
    investment_discretion VARCHAR(10)
);

CREATE INDEX idx_holdings_ticker ON holdings(ticker);
CREATE INDEX idx_holdings_cusip ON holdings(cusip);
CREATE INDEX idx_holdings_value ON holdings(value_thousands DESC);
```

### 3. `issuers` (Reference Data)

```sql
CREATE TABLE issuers (
    cusip VARCHAR(9) PRIMARY KEY,
    ticker VARCHAR(10),
    issuer_name VARCHAR(255),
    sector VARCHAR(50)
);
```

### 4. `managers` (Reference Data)

```sql
CREATE TABLE managers (
    cik VARCHAR(10) PRIMARY KEY,
    manager_name VARCHAR(255) NOT NULL
);
```

---

## Common Queries

### Top 10 Holdings

```sql
SELECT ticker, issuer_name, value_thousands, shares_or_principal
FROM holdings h
JOIN filings f ON h.accession_number = f.accession_number
WHERE f.cik = '0001067983' AND f.period_of_report = '2024-12-31'
ORDER BY value_thousands DESC
LIMIT 10;
```

### All Managers Holding a Stock

```sql
SELECT f.manager_name, h.shares_or_principal, h.value_thousands
FROM holdings h
JOIN filings f ON h.accession_number = f.accession_number
WHERE h.ticker = 'AAPL' AND f.period_of_report = '2024-12-31'
ORDER BY h.value_thousands DESC;
```

---

**Last Updated**: 2025-01-10
