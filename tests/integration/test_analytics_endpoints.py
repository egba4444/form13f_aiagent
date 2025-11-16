"""
Integration tests for analytics endpoints.

Tests portfolio composition, security analysis, and top movers endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.engine import Row

from src.api.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_db_connection():
    """Mock database connection for testing"""
    mock_conn = MagicMock()
    return mock_conn


class TestPortfolioComposition:
    """Test suite for /analytics/portfolio/{cik} endpoint"""

    @patch('src.api.routers.analytics_endpoints.create_engine')
    @patch('src.api.routers.analytics_endpoints.get_database_url')
    def test_portfolio_composition_success(self, mock_get_db_url, mock_create_engine, client):
        """Test successful portfolio composition retrieval"""
        # Mock database URL
        mock_get_db_url.return_value = "postgresql://test:test@localhost/test"

        # Mock engine and connection
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        # Mock manager query
        manager_row = MagicMock()
        manager_row.name = "Berkshire Hathaway Inc"
        mock_conn.execute.return_value.fetchone.side_effect = [
            manager_row,  # Manager name
            MagicMock(period_of_report="2024-12-31"),  # Latest period
            MagicMock(accession_number="0001234567", total_value=1000000000, number_of_holdings=50)  # Filing
        ]

        # Mock holdings query
        holding_rows = [
            MagicMock(cusip="037833100", title_of_class="Apple Inc", value=500000000, shares_or_principal=5000000),
            MagicMock(cusip="594918104", title_of_class="Microsoft Corp", value=300000000, shares_or_principal=3000000),
        ]
        mock_conn.execute.return_value.__iter__ = lambda self: iter(holding_rows)

        # Make request
        response = client.get("/api/v1/analytics/portfolio/0001067983")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["cik"] == "0001067983"
        assert data["manager_name"] == "Berkshire Hathaway Inc"
        assert data["total_value"] == 1000000000
        assert len(data["top_holdings"]) == 2
        assert "concentration" in data
        assert "top5_percent" in data["concentration"]

    @patch('src.api.routers.analytics_endpoints.create_engine')
    @patch('src.api.routers.analytics_endpoints.get_database_url')
    def test_portfolio_composition_manager_not_found(self, mock_get_db_url, mock_create_engine, client):
        """Test portfolio composition with non-existent manager"""
        mock_get_db_url.return_value = "postgresql://test:test@localhost/test"

        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        # Mock empty manager result
        mock_conn.execute.return_value.fetchone.return_value = None

        response = client.get("/api/v1/analytics/portfolio/9999999999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch('src.api.routers.analytics_endpoints.create_engine')
    @patch('src.api.routers.analytics_endpoints.get_database_url')
    def test_portfolio_composition_with_period(self, mock_get_db_url, mock_create_engine, client):
        """Test portfolio composition with specific period"""
        mock_get_db_url.return_value = "postgresql://test:test@localhost/test"

        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        # Mock responses
        manager_row = MagicMock()
        manager_row.name = "Vanguard Group Inc"
        mock_conn.execute.return_value.fetchone.side_effect = [
            manager_row,
            MagicMock(accession_number="0001234567", total_value=2000000000, number_of_holdings=100)
        ]

        mock_conn.execute.return_value.__iter__ = lambda self: iter([])

        response = client.get("/api/v1/analytics/portfolio/0001067983?period=2024-06-30&top_n=20")

        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "2024-06-30"


class TestSecurityAnalysis:
    """Test suite for /analytics/security/{cusip} endpoint"""

    @patch('src.api.routers.analytics_endpoints.create_engine')
    @patch('src.api.routers.analytics_endpoints.get_database_url')
    def test_security_analysis_success(self, mock_get_db_url, mock_create_engine, client):
        """Test successful security analysis retrieval"""
        mock_get_db_url.return_value = "postgresql://test:test@localhost/test"

        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        # Mock issuer query
        issuer_row = MagicMock()
        issuer_row.name = "Apple Inc"

        # Mock period query
        period_row = MagicMock()
        period_row.period = "2024-12-31"

        # Mock totals query
        totals_row = MagicMock()
        totals_row.total_shares = 15000000000
        totals_row.total_value = 3000000000000
        totals_row.holder_count = 500

        mock_conn.execute.return_value.fetchone.side_effect = [
            issuer_row,
            period_row,
            totals_row
        ]

        # Mock holders query
        holder_rows = [
            MagicMock(cik="0001067983", manager_name="Berkshire Hathaway", shares=500000000, value=100000000000),
            MagicMock(cik="0001166559", manager_name="Vanguard Group", shares=400000000, value=80000000000),
        ]
        mock_conn.execute.return_value.__iter__ = lambda self: iter(holder_rows)

        response = client.get("/api/v1/analytics/security/037833100")

        assert response.status_code == 200
        data = response.json()
        assert data["cusip"] == "037833100"
        assert data["title_of_class"] == "Apple Inc"
        assert data["total_institutional_shares"] == 15000000000
        assert len(data["top_holders"]) == 2
        assert "concentration" in data
        assert "herfindahl_index" in data["concentration"]

    @patch('src.api.routers.analytics_endpoints.create_engine')
    @patch('src.api.routers.analytics_endpoints.get_database_url')
    def test_security_analysis_security_not_found(self, mock_get_db_url, mock_create_engine, client):
        """Test security analysis with non-existent CUSIP"""
        mock_get_db_url.return_value = "postgresql://test:test@localhost/test"

        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        # Mock empty issuer result
        mock_conn.execute.return_value.fetchone.return_value = None

        response = client.get("/api/v1/analytics/security/000000000")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestTopMovers:
    """Test suite for /analytics/movers endpoint"""

    @patch('src.api.routers.analytics_endpoints.create_engine')
    @patch('src.api.routers.analytics_endpoints.get_database_url')
    def test_top_movers_success(self, mock_get_db_url, mock_create_engine, client):
        """Test successful top movers retrieval"""
        mock_get_db_url.return_value = "postgresql://test:test@localhost/test"

        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        # Mock periods query
        period_rows = [
            MagicMock(period_of_report="2024-12-31"),
            MagicMock(period_of_report="2024-09-30")
        ]
        mock_conn.execute.return_value.fetchall.side_effect = [
            period_rows,  # Latest periods
            [  # Position changes
                MagicMock(
                    cik="0001067983",
                    manager_name="Berkshire Hathaway",
                    cusip="037833100",
                    title_of_class="Apple Inc",
                    previous_value=100000000,
                    current_value=150000000,
                    value_change=50000000,
                    previous_shares=1000000,
                    current_shares=1500000,
                    shares_change=500000
                )
            ],
            [],  # New positions
            []   # Closed positions
        ]

        response = client.get("/api/v1/analytics/movers")

        assert response.status_code == 200
        data = response.json()
        assert "period_from" in data
        assert "period_to" in data
        assert "biggest_increases" in data
        assert "biggest_decreases" in data
        assert "new_positions" in data
        assert "closed_positions" in data

    @patch('src.api.routers.analytics_endpoints.create_engine')
    @patch('src.api.routers.analytics_endpoints.get_database_url')
    def test_top_movers_with_custom_periods(self, mock_get_db_url, mock_create_engine, client):
        """Test top movers with custom period range"""
        mock_get_db_url.return_value = "postgresql://test:test@localhost/test"

        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        # Mock empty results for all queries
        mock_conn.execute.return_value.fetchall.return_value = []

        response = client.get("/api/v1/analytics/movers?period_from=2024-06-30&period_to=2024-12-31&top_n=20")

        assert response.status_code == 200
        data = response.json()
        assert data["period_from"] == "2024-06-30"
        assert data["period_to"] == "2024-12-31"

    @patch('src.api.routers.analytics_endpoints.create_engine')
    @patch('src.api.routers.analytics_endpoints.get_database_url')
    def test_top_movers_insufficient_periods(self, mock_get_db_url, mock_create_engine, client):
        """Test top movers with insufficient periods in database"""
        mock_get_db_url.return_value = "postgresql://test:test@localhost/test"

        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        # Mock only one period available
        mock_conn.execute.return_value.fetchall.return_value = [
            MagicMock(period_of_report="2024-12-31")
        ]

        response = client.get("/api/v1/analytics/movers")

        assert response.status_code == 404
        assert "insufficient" in response.json()["detail"].lower()


class TestParameterValidation:
    """Test suite for parameter validation"""

    def test_top_n_parameter_validation(self, client):
        """Test top_n parameter bounds"""
        # Test too small
        response = client.get("/api/v1/analytics/portfolio/0001067983?top_n=0")
        assert response.status_code == 422

        # Test too large
        response = client.get("/api/v1/analytics/portfolio/0001067983?top_n=100")
        assert response.status_code == 422

    def test_period_format_validation(self, client):
        """Test period parameter format"""
        # Valid formats should be YYYY-MM-DD
        # Note: This test will fail if the CIK doesn't exist, but that's expected
        # We're just checking the parameter is accepted
        response = client.get("/api/v1/analytics/portfolio/0001067983?period=2024-12-31")
        # Should not be a 422 validation error (will be 404 or 500 from DB)
        assert response.status_code != 422
