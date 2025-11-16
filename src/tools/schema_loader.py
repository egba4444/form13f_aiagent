"""
Database Schema Loader

Loads database schema and formats it for LLM context.
Provides schema information to help Claude generate accurate SQL queries.
"""

from typing import Dict, List
from sqlalchemy import create_engine, inspect, MetaData
from sqlalchemy.engine import Engine


class SchemaLoader:
    """
    Loads database schema and formats it for LLM prompts.

    Provides:
    - Table names and column definitions
    - Data types
    - Primary keys and foreign keys
    - Indexes
    - Sample queries
    """

    def __init__(self, database_url: str):
        """
        Initialize schema loader.

        Args:
            database_url: SQLAlchemy database URL
        """
        self.engine = create_engine(database_url)
        self.inspector = inspect(self.engine)
        self.metadata = MetaData()
        self.metadata.reflect(bind=self.engine)

    def get_schema_text(self, include_samples: bool = True) -> str:
        """
        Get schema as formatted text for LLM context.

        Args:
            include_samples: Whether to include sample queries

        Returns:
            Formatted schema text
        """
        lines = []

        lines.append("# Form 13F Database Schema")
        lines.append("")
        lines.append("## Tables")
        lines.append("")

        # Get tables in logical order
        table_order = ['managers', 'issuers', 'filings', 'holdings']
        tables = [t for t in table_order if t in self.metadata.tables]

        for table_name in tables:
            lines.extend(self._format_table(table_name))
            lines.append("")

        if include_samples:
            lines.append("## Sample Queries")
            lines.append("")
            lines.extend(self._get_sample_queries())

        return "\n".join(lines)

    def _format_table(self, table_name: str) -> List[str]:
        """Format single table information"""
        lines = []

        table = self.metadata.tables[table_name]
        columns = self.inspector.get_columns(table_name)
        pk_constraint = self.inspector.get_pk_constraint(table_name)
        foreign_keys = self.inspector.get_foreign_keys(table_name)
        indexes = self.inspector.get_indexes(table_name)

        # Table header
        lines.append(f"### {table_name}")
        lines.append("")

        # Description based on table
        descriptions = {
            'managers': 'Institutional investment managers (filers)',
            'issuers': 'Security issuers (companies)',
            'filings': 'Form 13F filing metadata',
            'holdings': 'Individual security positions within filings'
        }
        if table_name in descriptions:
            lines.append(descriptions[table_name])
            lines.append("")

        # Columns
        lines.append("**Columns:**")
        for col in columns:
            col_name = col['name']
            col_type = str(col['type'])
            nullable = "" if col['nullable'] else " NOT NULL"
            default = f" DEFAULT {col['default']}" if col.get('default') else ""

            # Check if primary key
            is_pk = col_name in (pk_constraint.get('constrained_columns') or [])
            pk_marker = " (PRIMARY KEY)" if is_pk else ""

            # Check if foreign key
            fk_info = ""
            for fk in foreign_keys:
                if col_name in fk['constrained_columns']:
                    ref_table = fk['referred_table']
                    ref_col = fk['referred_columns'][0]
                    fk_info = f" → {ref_table}.{ref_col}"
                    break

            lines.append(f"- `{col_name}`: {col_type}{nullable}{default}{pk_marker}{fk_info}")

        # Indexes (show important ones)
        if indexes:
            lines.append("")
            lines.append("**Indexes:**")
            for idx in indexes[:5]:  # Top 5 indexes
                # Filter out None values from column_names
                col_names = [col for col in idx['column_names'] if col is not None]
                if col_names:  # Only show index if it has valid columns
                    idx_cols = ', '.join(col_names)
                    unique = " (UNIQUE)" if idx.get('unique') else ""
                    lines.append(f"- `{idx['name']}`: ({idx_cols}){unique}")

        return lines

    def _get_sample_queries(self) -> List[str]:
        """Get sample SQL queries"""
        return [
            "```sql",
            "-- Find all holdings for a specific manager (e.g., Berkshire Hathaway CIK: 0001067983)",
            "SELECT h.*, i.name as issuer_name",
            "FROM holdings h",
            "JOIN filings f ON h.accession_number = f.accession_number",
            "JOIN issuers i ON h.cusip = i.cusip",
            "WHERE f.cik = '0001067983'",
            "  AND f.period_of_report = '2024-12-31'",
            "ORDER BY h.value DESC",
            "LIMIT 10;",
            "",
            "-- Top 10 managers by total portfolio value in latest quarter",
            "SELECT m.name, f.total_value, f.period_of_report",
            "FROM filings f",
            "JOIN managers m ON f.cik = m.cik",
            "WHERE f.period_of_report = (SELECT MAX(period_of_report) FROM filings)",
            "ORDER BY f.total_value DESC",
            "LIMIT 10;",
            "",
            "-- Find all managers holding a specific security (e.g., Apple CUSIP: 037833100)",
            "SELECT m.name, h.value, h.shares_or_principal, f.period_of_report",
            "FROM holdings h",
            "JOIN filings f ON h.accession_number = f.accession_number",
            "JOIN managers m ON f.cik = m.cik",
            "WHERE h.cusip = '037833100'",
            "ORDER BY h.value DESC",
            "LIMIT 20;",
            "",
            "-- Count total holdings per manager",
            "SELECT m.name, COUNT(h.id) as holding_count, SUM(h.value) as total_value",
            "FROM managers m",
            "JOIN filings f ON m.cik = f.cik",
            "JOIN holdings h ON f.accession_number = h.accession_number",
            "GROUP BY m.cik, m.name",
            "ORDER BY total_value DESC",
            "LIMIT 10;",
            "```",
            "",
            "## Common Query Patterns",
            "",
            "1. **Manager's holdings**: Always JOIN filings → holdings → issuers",
            "2. **Portfolio value**: Use `total_value` from filings table (already aggregated)",
            "3. **Latest quarter**: `WHERE period_of_report = (SELECT MAX(period_of_report) FROM filings)`",
            "4. **Specific security**: Filter by `cusip` in holdings table",
            "5. **Time series**: GROUP BY period_of_report, ORDER BY period_of_report",
            "",
            "## Important Notes",
            "",
            "- All monetary values are in USD (not thousands)",
            "- `shares_or_principal` is number of shares (or principal amount for bonds)",
            "- `sh_or_prn` indicates type: 'SH' = shares, 'PRN' = principal amount",
            "- CIK is always 10 digits with leading zeros (e.g., '0001067983')",
            "- CUSIP is always 9 characters",
            "- Date format: YYYY-MM-DD (period_of_report is last day of quarter)",
        ]

    def get_compact_schema(self) -> str:
        """
        Get minimal schema for token efficiency.

        Returns only essential information.
        """
        lines = []

        lines.append("DATABASE SCHEMA:")
        lines.append("")

        for table_name in ['managers', 'issuers', 'filings', 'holdings']:
            if table_name not in self.metadata.tables:
                continue

            columns = self.inspector.get_columns(table_name)
            pk = self.inspector.get_pk_constraint(table_name)
            fks = self.inspector.get_foreign_keys(table_name)

            # Table and columns
            col_list = []
            for col in columns:
                col_str = f"{col['name']} {col['type']}"
                if col['name'] in (pk.get('constrained_columns') or []):
                    col_str += " PK"
                col_list.append(col_str)

            lines.append(f"{table_name}({', '.join(col_list)})")

            # Foreign keys
            for fk in fks:
                const_col = fk['constrained_columns'][0]
                ref_table = fk['referred_table']
                ref_col = fk['referred_columns'][0]
                lines.append(f"  └─ {const_col} → {ref_table}.{ref_col}")

            lines.append("")

        return "\n".join(lines)


# Convenience function
def get_schema(database_url: str, compact: bool = False) -> str:
    """
    Get database schema as text.

    Args:
        database_url: SQLAlchemy database URL
        compact: If True, return compact version (fewer tokens)

    Returns:
        Schema text
    """
    loader = SchemaLoader(database_url)
    if compact:
        return loader.get_compact_schema()
    return loader.get_schema_text()


# Example usage
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        loader = SchemaLoader(database_url)

        print("=" * 60)
        print("FULL SCHEMA")
        print("=" * 60)
        print(loader.get_schema_text())

        print("\n" + "=" * 60)
        print("COMPACT SCHEMA")
        print("=" * 60)
        print(loader.get_compact_schema())
    else:
        print("DATABASE_URL not set in .env")
