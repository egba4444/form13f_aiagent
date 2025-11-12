"""
SQL Query Validator

Validates SQL queries for safety before execution.
Ensures only safe SELECT queries are allowed.
"""

from typing import Set, Optional
import sqlparse
from sqlparse.sql import Statement
from sqlparse.tokens import Keyword, DML


class SQLValidationError(Exception):
    """Raised when SQL validation fails"""
    pass


class SQLValidator:
    """
    Validates SQL queries for safety.

    Safety checks:
    - Only SELECT statements allowed
    - No data modification (INSERT, UPDATE, DELETE, DROP, etc.)
    - Only whitelisted tables
    - No multiple statements (SQL injection prevention)
    - Must include LIMIT clause (or auto-add it)
    """

    # Dangerous keywords that should never appear
    DANGEROUS_KEYWORDS = {
        'DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'TRUNCATE',
        'CREATE', 'REPLACE', 'GRANT', 'REVOKE', 'EXECUTE',
        'EXEC', 'CALL', 'COPY', 'IMPORT', 'LOAD'
    }

    # Allowed tables (whitelist)
    ALLOWED_TABLES = {
        'managers', 'issuers', 'filings', 'holdings'
    }

    def __init__(self, allowed_tables: Optional[Set[str]] = None):
        """
        Initialize validator.

        Args:
            allowed_tables: Set of allowed table names (defaults to Form 13F tables)
        """
        self.allowed_tables = allowed_tables or self.ALLOWED_TABLES

    def validate(self, sql: str, max_limit: int = 1000) -> str:
        """
        Validate SQL query and return sanitized version.

        Args:
            sql: SQL query to validate
            max_limit: Maximum LIMIT value allowed

        Returns:
            Sanitized SQL query (with LIMIT added if missing)

        Raises:
            SQLValidationError: If validation fails
        """
        if not sql or not sql.strip():
            raise SQLValidationError("Empty SQL query")

        # Parse SQL
        statements = sqlparse.parse(sql)

        if not statements:
            raise SQLValidationError("Could not parse SQL query")

        if len(statements) > 1:
            raise SQLValidationError(
                "Multiple SQL statements not allowed (SQL injection prevention)"
            )

        statement = statements[0]

        # Check it's a SELECT statement
        self._validate_statement_type(statement)

        # Check for dangerous keywords
        self._validate_no_dangerous_keywords(sql)

        # Extract and validate table names
        tables = self._extract_tables(statement)
        self._validate_tables(tables)

        # Ensure LIMIT clause exists
        sanitized_sql = self._ensure_limit(sql, statement, max_limit)

        return sanitized_sql

    def _validate_statement_type(self, statement: Statement):
        """Validate statement is SELECT only"""
        # Get first token (should be SELECT)
        first_token = None
        for token in statement.tokens:
            if not token.is_whitespace:
                first_token = token
                break

        if not first_token:
            raise SQLValidationError("Empty statement")

        # Check if it's a SELECT
        if first_token.ttype is Keyword.DML:
            if first_token.value.upper() != 'SELECT':
                raise SQLValidationError(
                    f"Only SELECT statements allowed, got {first_token.value.upper()}"
                )
        elif hasattr(first_token, 'get_real_name'):
            if first_token.get_real_name().upper() != 'SELECT':
                raise SQLValidationError(
                    f"Only SELECT statements allowed, got {first_token.get_real_name()}"
                )
        else:
            # Check string representation
            token_str = str(first_token).strip().upper()
            if not token_str.startswith('SELECT'):
                raise SQLValidationError(
                    f"Only SELECT statements allowed, got {token_str[:20]}"
                )

    def _validate_no_dangerous_keywords(self, sql: str):
        """Check for dangerous keywords"""
        sql_upper = sql.upper()

        for keyword in self.DANGEROUS_KEYWORDS:
            # Check for keyword as whole word (not substring)
            # E.g., "DROP" in "DROP TABLE" but not in "AIRDROP"
            if f' {keyword} ' in f' {sql_upper} ':
                raise SQLValidationError(
                    f"Dangerous keyword not allowed: {keyword}"
                )

    def _extract_tables(self, statement: Statement) -> Set[str]:
        """
        Extract table names from SQL statement.

        This is a simplified extraction that looks for:
        - FROM table_name
        - JOIN table_name

        Returns:
            Set of table names
        """
        tables = set()
        tokens = list(statement.flatten())

        for i, token in enumerate(tokens):
            # Look for FROM or JOIN keywords
            if token.ttype is Keyword and token.value.upper() in ('FROM', 'JOIN'):
                # Next non-whitespace token should be table name
                for next_token in tokens[i + 1:]:
                    if next_token.ttype is not sqlparse.tokens.Whitespace:
                        # Get table name (remove quotes if present)
                        table_name = next_token.value.strip('"`\'').lower()
                        # Handle schema.table format
                        if '.' in table_name:
                            table_name = table_name.split('.')[-1]
                        tables.add(table_name)
                        break

        return tables

    def _validate_tables(self, tables: Set[str]):
        """Validate all tables are in whitelist"""
        if not tables:
            raise SQLValidationError("No tables found in query")

        invalid_tables = tables - self.allowed_tables

        if invalid_tables:
            raise SQLValidationError(
                f"Invalid table(s): {', '.join(invalid_tables)}. "
                f"Allowed tables: {', '.join(sorted(self.allowed_tables))}"
            )

    def _ensure_limit(self, sql: str, statement: Statement, max_limit: int) -> str:
        """
        Ensure query has LIMIT clause.

        If LIMIT exists, validate it's not too large.
        If LIMIT missing, add it.

        Returns:
            SQL with LIMIT clause
        """
        sql_upper = sql.upper()

        # Check if LIMIT already exists
        if 'LIMIT' in sql_upper:
            # Extract LIMIT value
            limit_idx = sql_upper.find('LIMIT')
            after_limit = sql[limit_idx + 5:].strip()

            # Get first token after LIMIT (should be number)
            limit_value_str = after_limit.split()[0] if after_limit else '0'

            try:
                limit_value = int(limit_value_str.rstrip(';'))
                if limit_value > max_limit:
                    raise SQLValidationError(
                        f"LIMIT {limit_value} exceeds maximum allowed ({max_limit})"
                    )
                return sql  # LIMIT exists and is valid
            except ValueError:
                raise SQLValidationError(
                    f"Invalid LIMIT value: {limit_value_str}"
                )

        # Add LIMIT
        sql_clean = sql.rstrip().rstrip(';')
        return f"{sql_clean} LIMIT {max_limit};"


# Convenience function
def validate_sql(sql: str, max_limit: int = 1000) -> str:
    """
    Validate SQL query and return sanitized version.

    Args:
        sql: SQL query to validate
        max_limit: Maximum LIMIT value allowed

    Returns:
        Sanitized SQL query

    Raises:
        SQLValidationError: If validation fails
    """
    validator = SQLValidator()
    return validator.validate(sql, max_limit)


# Example usage
if __name__ == "__main__":
    validator = SQLValidator()

    # Valid query
    try:
        safe_sql = validator.validate(
            "SELECT * FROM holdings WHERE value > 1000000"
        )
        print(f"✅ Valid: {safe_sql}")
    except SQLValidationError as e:
        print(f"❌ Invalid: {e}")

    # Invalid query (dangerous keyword)
    try:
        validator.validate("DROP TABLE holdings;")
    except SQLValidationError as e:
        print(f"✅ Caught dangerous query: {e}")

    # Invalid query (wrong table)
    try:
        validator.validate("SELECT * FROM users")
    except SQLValidationError as e:
        print(f"✅ Caught invalid table: {e}")

    # Invalid query (multiple statements)
    try:
        validator.validate("SELECT * FROM holdings; DELETE FROM holdings;")
    except SQLValidationError as e:
        print(f"✅ Caught multiple statements: {e}")
