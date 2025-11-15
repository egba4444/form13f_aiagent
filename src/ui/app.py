"""
Streamlit UI for Form 13F AI Agent

A chat interface for querying institutional holdings data.
"""

import streamlit as st
import httpx
import os
from typing import Optional
import pandas as pd

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


def main():
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

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hello! I'm your Form 13F AI assistant. Ask me questions about institutional holdings data. Try one of the example queries in the sidebar!"
            }
        ]

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
