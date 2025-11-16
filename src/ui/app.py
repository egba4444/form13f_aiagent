"""
Streamlit UI for Form 13F AI Agent

A chat interface for querying institutional holdings data.
"""

import streamlit as st
import httpx
import os
from typing import Optional, List, Dict, Any
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "https://form13f-aiagent-production.up.railway.app")
TIMEOUT = 120.0  # 2 minutes timeout for agent queries

# Page configuration
st.set_page_config(
    page_title="Form 13F AI Agent",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #6b7280;
        margin-bottom: 2rem;
    }
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        text-align: center;
    }
    .stat-value {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
        white-space: nowrap;
    }
    .stat-label {
        font-size: 0.875rem;
        opacity: 0.9;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .sql-box {
        background-color: #1e293b;
        color: #10b981;
        padding: 1rem;
        border-radius: 8px;
        font-family: 'Courier New', monospace;
        font-size: 0.875rem;
        overflow-x: auto;
    }
    .example-query {
        background-color: #f3f4f6;
        padding: 0.75rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 0.5rem 0;
        cursor: pointer;
        transition: background-color 0.2s;
    }
    .example-query:hover {
        background-color: #e5e7eb;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=60)
def fetch_stats() -> Optional[dict]:
    """Fetch database statistics"""
    try:
        response = httpx.get(f"{API_BASE_URL}/api/v1/stats", timeout=10.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch stats: {e}")
        return None


@st.cache_data(ttl=300)
def fetch_managers(name_filter: str = "") -> List[Dict[str, Any]]:
    """Fetch list of managers"""
    try:
        params = {"page_size": 100}
        if name_filter:
            params["name"] = name_filter
        response = httpx.get(f"{API_BASE_URL}/api/v1/managers", params=params, timeout=10.0)
        response.raise_for_status()
        return response.json()["managers"]
    except Exception as e:
        st.error(f"Failed to fetch managers: {e}")
        return []


@st.cache_data(ttl=300)
def fetch_portfolio_composition(cik: str, top_n: int = 20) -> Optional[Dict[str, Any]]:
    """Fetch portfolio composition for a manager"""
    try:
        response = httpx.get(
            f"{API_BASE_URL}/api/v1/analytics/portfolio/{cik}",
            params={"top_n": top_n},
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch portfolio: {e}")
        return None


@st.cache_data(ttl=300)
def fetch_security_analysis(cusip: str, top_n: int = 20) -> Optional[Dict[str, Any]]:
    """Fetch security ownership analysis"""
    try:
        response = httpx.get(
            f"{API_BASE_URL}/api/v1/analytics/security/{cusip}",
            params={"top_n": top_n},
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch security analysis: {e}")
        return None


@st.cache_data(ttl=300)
def fetch_top_movers(top_n: int = 10) -> Optional[Dict[str, Any]]:
    """Fetch top position movers"""
    try:
        response = httpx.get(
            f"{API_BASE_URL}/api/v1/analytics/movers",
            params={"top_n": top_n},
            timeout=60.0
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch top movers: {e}")
        return None


def query_agent(query: str) -> dict:
    """Send query to the AI agent"""
    try:
        response = httpx.post(
            f"{API_BASE_URL}/api/v1/query",
            json={"query": query},
            timeout=TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except httpx.TimeoutException:
        return {
            "success": False,
            "error": "Request timed out. The query is taking too long to execute."
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to send query: {str(e)}"
        }


def format_number(num: int) -> str:
    """Format large numbers with commas"""
    return f"{num:,}"


def create_portfolio_pie_chart(portfolio_data: Dict[str, Any]) -> go.Figure:
    """Create portfolio composition pie chart"""
    top_holdings = portfolio_data["top_holdings"]

    labels = [h["title_of_class"] for h in top_holdings]
    values = [h["value"] for h in top_holdings]
    percentages = [h["percent_of_portfolio"] for h in top_holdings]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        textinfo='label+percent',
        hovertemplate='<b>%{label}</b><br>Value: $%{value:,.0f}<br>Portfolio %: %{customdata:.2f}%<extra></extra>',
        customdata=percentages
    )])

    fig.update_layout(
        title=f"Top {len(top_holdings)} Holdings - {portfolio_data['manager_name']}",
        height=500
    )

    return fig


def create_portfolio_bar_chart(portfolio_data: Dict[str, Any]) -> go.Figure:
    """Create portfolio holdings bar chart"""
    top_holdings = portfolio_data["top_holdings"]

    df = pd.DataFrame(top_holdings)
    df = df.sort_values("value", ascending=True)

    fig = go.Figure(data=[go.Bar(
        y=df["title_of_class"],
        x=df["value"],
        orientation='h',
        text=df["percent_of_portfolio"].apply(lambda x: f"{x:.1f}%"),
        textposition='outside',
        hovertemplate='<b>%{y}</b><br>Value: $%{x:,.0f}<br>Shares: %{customdata:,.0f}<extra></extra>',
        customdata=df["shares_or_principal"]
    )])

    fig.update_layout(
        title=f"Portfolio Holdings - {portfolio_data['manager_name']}",
        xaxis_title="Value (USD)",
        yaxis_title="",
        height=max(400, len(top_holdings) * 30),
        showlegend=False
    )

    return fig


def create_security_ownership_chart(security_data: Dict[str, Any]) -> go.Figure:
    """Create security ownership bar chart"""
    top_holders = security_data["top_holders"]

    df = pd.DataFrame(top_holders)
    df = df.sort_values("value", ascending=True)

    fig = go.Figure(data=[go.Bar(
        y=df["manager_name"],
        x=df["shares"],
        orientation='h',
        text=df["percent_of_total"].apply(lambda x: f"{x:.1f}%"),
        textposition='outside',
        hovertemplate='<b>%{y}</b><br>Shares: %{x:,.0f}<br>Value: $%{customdata:,.0f}<extra></extra>',
        customdata=df["value"]
    )])

    fig.update_layout(
        title=f"Top Institutional Holders - {security_data['title_of_class']}",
        xaxis_title="Shares",
        yaxis_title="",
        height=max(400, len(top_holders) * 30),
        showlegend=False
    )

    return fig


def create_movers_chart(movers_data: Dict[str, Any]) -> go.Figure:
    """Create top movers chart"""
    increases = movers_data.get("biggest_increases", [])[:10]
    decreases = movers_data.get("biggest_decreases", [])[:10]

    # Combine and sort by absolute percentage change
    all_movers = []
    for mover in increases:
        all_movers.append({
            "name": f"{mover['manager_name'][:20]} - {mover['title_of_class'][:20]}",
            "change_pct": mover["value_change_percent"],
            "change_value": mover["value_change"]
        })
    for mover in decreases:
        all_movers.append({
            "name": f"{mover['manager_name'][:20]} - {mover['title_of_class'][:20]}",
            "change_pct": mover["value_change_percent"],
            "change_value": mover["value_change"]
        })

    df = pd.DataFrame(all_movers)
    df = df.sort_values("change_pct", ascending=True)

    # Color based on positive/negative
    colors = ['green' if x > 0 else 'red' for x in df["change_pct"]]

    fig = go.Figure(data=[go.Bar(
        y=df["name"],
        x=df["change_pct"],
        orientation='h',
        marker_color=colors,
        text=df["change_pct"].apply(lambda x: f"{x:+.1f}%"),
        textposition='outside',
        hovertemplate='<b>%{y}</b><br>Change: %{x:+.1f}%<br>Value Change: $%{customdata:+,.0f}<extra></extra>',
        customdata=df["change_value"]
    )])

    fig.update_layout(
        title="Biggest Position Changes (Quarter-over-Quarter)",
        xaxis_title="Value Change %",
        yaxis_title="",
        height=max(500, len(all_movers) * 25),
        showlegend=False
    )

    return fig


def main():
    # Initialize chat history FIRST (before any UI interactions)
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hello! I'm your Form 13F AI assistant. Ask me questions about institutional holdings data. Try one of the example queries in the sidebar!"
            }
        ]

    # Header
    st.markdown('<div class="main-header">📊 Form 13F AI Agent</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Ask questions about institutional investor holdings in natural language</div>', unsafe_allow_html=True)

    # Sidebar with stats
    with st.sidebar:
        st.header("Database Statistics")

        stats = fetch_stats()
        if stats:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value">{format_number(stats['managers_count'])}</div>
                    <div class="stat-label">Managers</div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value">{format_number(stats['filings_count'])}</div>
                    <div class="stat-label">Filings</div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value">{format_number(stats['issuers_count'])}</div>
                    <div class="stat-label">Issuers</div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value">{format_number(stats['holdings_count'])}</div>
                    <div class="stat-label">Holdings</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("---")
            st.info(f"**Latest Quarter:** {stats.get('latest_quarter', 'N/A')}")

            if stats.get('total_value'):
                total_value_trillions = stats['total_value'] / 1_000_000_000
                st.success(f"**Total Value:** ${total_value_trillions:.2f}T")

        st.markdown("---")

        # Example queries
        st.subheader("Example Queries")
        examples = [
            "Show me the 5 largest holdings by value",
            "Which managers filed in the last quarter?",
            "List all Apple holdings",
            "Show me Berkshire Hathaway's recent filings",
            "What are the top 10 holdings by share count?"
        ]

        for example in examples:
            if st.button(example, key=f"example_{hash(example)}", use_container_width=True):
                st.session_state.example_query = example

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            # Clean up any problematic markdown that causes rendering issues
            content = message["content"]
            # Remove any Unicode asterisks that might cause issues
            content = content.replace('∗', '*')
            st.markdown(content, unsafe_allow_html=False)

            # Display SQL if available
            if "sql" in message:
                st.markdown("**Generated SQL:**")
                st.markdown(f'<div class="sql-box">{message["sql"]}</div>', unsafe_allow_html=True)

            # Display table if available
            if "data" in message and message["data"]:
                st.markdown("**Query Results:**")
                df = pd.DataFrame(message["data"])
                st.dataframe(df, use_container_width=True)

                # Download button
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name="query_results.csv",
                    mime="text/csv"
                )

    # Handle example query from sidebar
    if "example_query" in st.session_state:
        user_input = st.session_state.example_query
        del st.session_state.example_query

        # Add user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = query_agent(user_input)

            if response.get("success"):
                # Format response
                answer = response.get("answer", "I found the results for your query.")
                # Clean up any problematic markdown that causes rendering issues
                answer = answer.replace('∗', '*')
                st.markdown(answer, unsafe_allow_html=False)

                message_data = {"role": "assistant", "content": answer}

                # Show SQL
                if response.get("sql_query"):
                    st.markdown("**Generated SQL:**")
                    st.markdown(f'<div class="sql-box">{response["sql_query"]}</div>', unsafe_allow_html=True)
                    message_data["sql"] = response["sql_query"]

                # Show data table
                if response.get("raw_data") and len(response["raw_data"]) > 0:
                    st.markdown("**Query Results:**")
                    df = pd.DataFrame(response["raw_data"])
                    st.dataframe(df, use_container_width=True)
                    message_data["data"] = response["raw_data"]

                    # Download button
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name="query_results.csv",
                        mime="text/csv"
                    )

                st.session_state.messages.append(message_data)
            else:
                # Show the answer field which contains the custom error message
                error_msg = response.get("answer", response.get("error", "Unknown error occurred"))
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"⚠️ {error_msg}"
                })

        st.rerun()

    # Chat input
    if prompt := st.chat_input("Ask a question about Form 13F holdings..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = query_agent(prompt)

            if response.get("success"):
                # Format response
                answer = response.get("answer", "I found the results for your query.")
                # Clean up any problematic markdown that causes rendering issues
                answer = answer.replace('∗', '*')
                st.markdown(answer, unsafe_allow_html=False)

                message_data = {"role": "assistant", "content": answer}

                # Show SQL
                if response.get("sql_query"):
                    st.markdown("**Generated SQL:**")
                    st.markdown(f'<div class="sql-box">{response["sql_query"]}</div>', unsafe_allow_html=True)
                    message_data["sql"] = response["sql_query"]

                # Show data table
                if response.get("raw_data") and len(response["raw_data"]) > 0:
                    st.markdown("**Query Results:**")
                    df = pd.DataFrame(response["raw_data"])
                    st.dataframe(df, use_container_width=True)
                    message_data["data"] = response["raw_data"]

                    # Download button
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name="query_results.csv",
                        mime="text/csv"
                    )

                st.session_state.messages.append(message_data)
            else:
                # Show the answer field which contains the custom error message
                error_msg = response.get("answer", response.get("error", "Unknown error occurred"))
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"⚠️ {error_msg}"
                })


if __name__ == "__main__":
    main()
