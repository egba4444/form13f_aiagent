"""
Unit tests for UI visualization functions.

Tests visualization creation functions from src/ui/app.py
"""

import pytest
from unittest.mock import patch, MagicMock
import plotly.graph_objects as go


# Import visualization functions from app.py
# Note: We'll mock streamlit to avoid import errors
@pytest.fixture(autouse=True)
def mock_streamlit():
    """Mock streamlit module to prevent import errors"""
    with patch.dict('sys.modules', {'streamlit': MagicMock()}):
        yield


def get_visualization_functions():
    """Import and return visualization functions from app.py"""
    import sys
    import importlib.util

    # Load app.py as a module
    spec = importlib.util.spec_from_file_location(
        "app",
        "C:/Users/Hodol/Projects/form13f_aiagent/src/ui/app.py"
    )
    app_module = importlib.util.module_from_spec(spec)
    sys.modules["app"] = app_module
    spec.loader.exec_module(app_module)

    return {
        'create_portfolio_pie_chart': app_module.create_portfolio_pie_chart,
        'create_portfolio_bar_chart': app_module.create_portfolio_bar_chart,
        'create_security_ownership_chart': app_module.create_security_ownership_chart,
        'create_movers_chart': app_module.create_movers_chart,
    }


class TestPortfolioPieChart:
    """Test suite for create_portfolio_pie_chart function"""

    def test_pie_chart_creation(self, mock_streamlit):
        """Test pie chart is created with correct structure"""
        funcs = get_visualization_functions()
        create_portfolio_pie_chart = funcs['create_portfolio_pie_chart']

        portfolio_data = {
            "manager_name": "Berkshire Hathaway Inc",
            "total_value": 1000000000,
            "top_holdings": [
                {
                    "cusip": "037833100",
                    "title_of_class": "Apple Inc",
                    "value": 500000000,
                    "shares_or_principal": 5000000,
                    "percent_of_portfolio": 50.0
                },
                {
                    "cusip": "594918104",
                    "title_of_class": "Microsoft Corp",
                    "value": 300000000,
                    "shares_or_principal": 3000000,
                    "percent_of_portfolio": 30.0
                }
            ]
        }

        fig = create_portfolio_pie_chart(portfolio_data)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1
        assert isinstance(fig.data[0], go.Pie)
        assert len(fig.data[0].labels) == 2
        assert "Apple Inc" in fig.data[0].labels
        assert "Microsoft Corp" in fig.data[0].labels

    def test_pie_chart_empty_holdings(self, mock_streamlit):
        """Test pie chart with no holdings"""
        funcs = get_visualization_functions()
        create_portfolio_pie_chart = funcs['create_portfolio_pie_chart']

        portfolio_data = {
            "manager_name": "Test Manager",
            "total_value": 0,
            "top_holdings": []
        }

        fig = create_portfolio_pie_chart(portfolio_data)

        assert isinstance(fig, go.Figure)
        assert len(fig.data[0].labels) == 0


class TestPortfolioBarChart:
    """Test suite for create_portfolio_bar_chart function"""

    def test_bar_chart_creation(self, mock_streamlit):
        """Test bar chart is created with correct structure"""
        funcs = get_visualization_functions()
        create_portfolio_bar_chart = funcs['create_portfolio_bar_chart']

        portfolio_data = {
            "manager_name": "Vanguard Group Inc",
            "total_value": 2000000000,
            "top_holdings": [
                {
                    "cusip": "037833100",
                    "title_of_class": "Apple Inc",
                    "value": 800000000,
                    "shares_or_principal": 8000000,
                    "percent_of_portfolio": 40.0
                },
                {
                    "cusip": "594918104",
                    "title_of_class": "Microsoft Corp",
                    "value": 600000000,
                    "shares_or_principal": 6000000,
                    "percent_of_portfolio": 30.0
                }
            ]
        }

        fig = create_portfolio_bar_chart(portfolio_data)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1
        assert isinstance(fig.data[0], go.Bar)
        assert fig.data[0].orientation == 'h'  # Horizontal bars

    def test_bar_chart_sorting(self, mock_streamlit):
        """Test bar chart sorts holdings by value descending"""
        funcs = get_visualization_functions()
        create_portfolio_bar_chart = funcs['create_portfolio_bar_chart']

        portfolio_data = {
            "manager_name": "Test Manager",
            "total_value": 1000000000,
            "top_holdings": [
                {"title_of_class": "Stock A", "value": 100000000, "percent_of_portfolio": 10.0, "cusip": "1", "shares_or_principal": 1000},
                {"title_of_class": "Stock B", "value": 300000000, "percent_of_portfolio": 30.0, "cusip": "2", "shares_or_principal": 3000},
                {"title_of_class": "Stock C", "value": 200000000, "percent_of_portfolio": 20.0, "cusip": "3", "shares_or_principal": 2000},
            ]
        }

        fig = create_portfolio_bar_chart(portfolio_data)

        # First item should be smallest (bottom of horizontal bar chart)
        assert fig.data[0].y[0] == "Stock A"


class TestSecurityOwnershipChart:
    """Test suite for create_security_ownership_chart function"""

    def test_ownership_chart_creation(self, mock_streamlit):
        """Test security ownership chart is created correctly"""
        funcs = get_visualization_functions()
        create_security_ownership_chart = funcs['create_security_ownership_chart']

        security_data = {
            "title_of_class": "Apple Inc",
            "total_institutional_value": 3000000000000,
            "top_holders": [
                {
                    "cik": "0001067983",
                    "manager_name": "Berkshire Hathaway",
                    "shares": 500000000,
                    "value": 100000000000,
                    "percent_of_total": 3.33
                },
                {
                    "cik": "0001166559",
                    "manager_name": "Vanguard Group",
                    "shares": 400000000,
                    "value": 80000000000,
                    "percent_of_total": 2.67
                }
            ]
        }

        fig = create_security_ownership_chart(security_data)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1
        assert isinstance(fig.data[0], go.Bar)
        assert "Berkshire Hathaway" in str(fig.data[0].y)


class TestMoversChart:
    """Test suite for create_movers_chart function"""

    def test_movers_chart_creation(self, mock_streamlit):
        """Test movers chart is created with color coding"""
        funcs = get_visualization_functions()
        create_movers_chart = funcs['create_movers_chart']

        movers_data = {
            "biggest_increases": [
                {
                    "cik": "0001067983",
                    "manager_name": "Berkshire Hathaway",
                    "cusip": "037833100",
                    "title_of_class": "Apple Inc",
                    "value_change": 50000000,
                    "value_change_percent": 25.5
                },
                {
                    "cik": "0001166559",
                    "manager_name": "Vanguard Group",
                    "cusip": "594918104",
                    "title_of_class": "Microsoft Corp",
                    "value_change": 30000000,
                    "value_change_percent": 15.2
                }
            ],
            "biggest_decreases": [
                {
                    "cik": "0001234567",
                    "manager_name": "Test Fund",
                    "cusip": "88160R101",
                    "title_of_class": "Tesla Inc",
                    "value_change": -20000000,
                    "value_change_percent": -10.5
                }
            ]
        }

        fig = create_movers_chart(movers_data)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1
        assert isinstance(fig.data[0], go.Bar)
        # Chart should have both positive and negative values
        assert any(x > 0 for x in fig.data[0].x)
        assert any(x < 0 for x in fig.data[0].x)

    def test_movers_chart_color_coding(self, mock_streamlit):
        """Test movers chart uses green for increases and red for decreases"""
        funcs = get_visualization_functions()
        create_movers_chart = funcs['create_movers_chart']

        movers_data = {
            "biggest_increases": [
                {
                    "cik": "0001067983",
                    "manager_name": "Test Manager A",
                    "cusip": "037833100",
                    "title_of_class": "Stock A",
                    "value_change": 50000000,
                    "value_change_percent": 25.0
                }
            ],
            "biggest_decreases": [
                {
                    "cik": "0001234567",
                    "manager_name": "Test Manager B",
                    "cusip": "88160R101",
                    "title_of_class": "Stock B",
                    "value_change": -20000000,
                    "value_change_percent": -10.0
                }
            ]
        }

        fig = create_movers_chart(movers_data)

        # Check that marker colors include both green and red
        colors = fig.data[0].marker.color
        assert 'green' in colors
        assert 'red' in colors

    def test_movers_chart_empty_data(self, mock_streamlit):
        """Test movers chart with no data"""
        funcs = get_visualization_functions()
        create_movers_chart = funcs['create_movers_chart']

        movers_data = {
            "biggest_increases": [],
            "biggest_decreases": []
        }

        fig = create_movers_chart(movers_data)

        assert isinstance(fig, go.Figure)
        assert len(fig.data[0].x) == 0


class TestDataCaching:
    """Test suite for data fetching and caching functions"""

    @patch('httpx.get')
    def test_fetch_managers_caching(self, mock_get, mock_streamlit):
        """Test that fetch_managers uses caching"""
        # This test would need streamlit.cache_data to work properly
        # For now, we just verify the function exists and can be called
        funcs = get_visualization_functions()

        # Verify all fetch functions exist
        import inspect
        app_source = inspect.getsource(funcs['create_portfolio_pie_chart'].__globals__['__loader__'].get_data(
            funcs['create_portfolio_pie_chart'].__globals__['__file__']
        ).decode())

        assert 'fetch_managers' in app_source
        assert 'fetch_portfolio_composition' in app_source
        assert 'fetch_security_analysis' in app_source
        assert 'fetch_top_movers' in app_source
        assert '@st.cache_data' in app_source


class TestVisualizationProperties:
    """Test suite for visualization properties and configurations"""

    def test_all_charts_have_titles(self, mock_streamlit):
        """Test that all visualization functions create charts with titles"""
        funcs = get_visualization_functions()

        # Test pie chart
        portfolio_data = {
            "manager_name": "Test Manager",
            "top_holdings": [
                {"title_of_class": "Stock A", "value": 100, "percent_of_portfolio": 100, "cusip": "1", "shares_or_principal": 1}
            ]
        }
        fig = funcs['create_portfolio_pie_chart'](portfolio_data)
        assert fig.layout.title.text is not None

        # Test bar chart
        fig = funcs['create_portfolio_bar_chart'](portfolio_data)
        assert fig.layout.title.text is not None

        # Test ownership chart
        security_data = {
            "title_of_class": "Test Stock",
            "top_holders": [
                {"manager_name": "Manager A", "value": 100, "percent_of_total": 10, "cik": "1", "shares": 100}
            ]
        }
        fig = funcs['create_security_ownership_chart'](security_data)
        assert fig.layout.title.text is not None

    def test_charts_have_proper_height(self, mock_streamlit):
        """Test that charts have appropriate height settings"""
        funcs = get_visualization_functions()

        portfolio_data = {
            "manager_name": "Test Manager",
            "top_holdings": [
                {"title_of_class": "Stock A", "value": 100, "percent_of_portfolio": 100, "cusip": "1", "shares_or_principal": 1}
            ]
        }

        fig = funcs['create_portfolio_pie_chart'](portfolio_data)
        assert fig.layout.height is not None
        assert fig.layout.height > 0
