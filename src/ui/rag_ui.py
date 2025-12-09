"""
RAG UI Components for Streamlit

Provides semantic search and filing text exploration features.
"""

import streamlit as st
import httpx
from typing import Optional, List, Dict, Any
import pandas as pd


def semantic_search(api_base_url: str, query: str, top_k: int = 5,
                   filter_accession: Optional[str] = None,
                   filter_content_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Execute semantic search via API.

    Args:
        api_base_url: Base URL of the API
        query: Search query
        top_k: Number of results to return
        filter_accession: Optional accession number filter
        filter_content_type: Optional content type filter

    Returns:
        Search results dict or None if error
    """
    try:
        payload = {
            "query": query,
            "top_k": top_k
        }

        if filter_accession:
            payload["filter_accession"] = filter_accession
        if filter_content_type:
            payload["filter_content_type"] = filter_content_type

        response = httpx.post(
            f"{api_base_url}/api/v1/search/semantic",
            json=payload,
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Semantic search failed: {e}")
        return None


def summarize_results(api_base_url: str, query: str, results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Summarize search results using AI.

    Args:
        api_base_url: Base URL of the API
        query: Original search query
        results: Search results to summarize

    Returns:
        Summary dict or None if error
    """
    try:
        payload = {
            "query": query,
            "results": results
        }

        response = httpx.post(
            f"{api_base_url}/api/v1/search/summarize",
            json=payload,
            timeout=60.0  # Longer timeout for AI processing
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"AI summarization failed: {e}")
        return None


def get_filing_text(api_base_url: str, accession_number: str,
                   content_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get filing text content via API.

    Args:
        api_base_url: Base URL of the API
        accession_number: Filing accession number
        content_type: Optional content type filter

    Returns:
        Filing text dict or None if error
    """
    try:
        params = {}
        if content_type:
            params["content_type"] = content_type

        response = httpx.get(
            f"{api_base_url}/api/v1/filings/{accession_number}/text",
            params=params,
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to get filing text: {e}")
        return None


def display_search_result(result: Dict[str, Any], index: int):
    """
    Display a single semantic search result with citation.

    Args:
        result: Search result dictionary
        index: Result index (1-based)
    """
    # Extract result data
    text = result.get("text", "")
    accession = result.get("accession_number", "N/A")
    content_type = result.get("content_type", "N/A")
    score = result.get("relevance_score", 0.0)

    # Format content type for display
    content_type_display = content_type.replace("_", " ").title()

    # Determine relevance color based on score
    if score >= 0.7:
        score_color = "#10b981"  # Green
        relevance = "High"
    elif score >= 0.5:
        score_color = "#f59e0b"  # Orange
        relevance = "Medium"
    else:
        score_color = "#ef4444"  # Red
        relevance = "Low"

    # Display result card
    st.markdown(f"""
    <div style="
        background-color: #f9fafb;
        border-left: 4px solid {score_color};
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.5rem;
    ">
        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem;">
            <div style="font-weight: 600; color: #1f2937;">
                Result {index}
            </div>
            <div style="
                background-color: {score_color};
                color: white;
                padding: 0.25rem 0.75rem;
                border-radius: 1rem;
                font-size: 0.75rem;
                font-weight: 600;
            ">
                {relevance} ({score:.3f})
            </div>
        </div>
        <div style="color: #374151; margin-bottom: 0.75rem; line-height: 1.6;">
            {text}
        </div>
        <div style="
            display: flex;
            gap: 1rem;
            font-size: 0.75rem;
            color: #6b7280;
            padding-top: 0.5rem;
            border-top: 1px solid #e5e7eb;
        ">
            <div>
                <strong>Filing:</strong> {accession}
            </div>
            <div>
                <strong>Section:</strong> {content_type_display}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Add expander with filing details
    with st.expander(f"📄 View full filing text ({accession})"):
        with st.spinner("Loading filing text..."):
            filing_data = get_filing_text(st.session_state.get("api_base_url", ""), accession)

        if filing_data:
            sections = filing_data.get("sections", {})

            if sections:
                # Create tabs for different sections
                section_names = list(sections.keys())
                tabs = st.tabs([name.replace("_", " ").title() for name in section_names])

                for tab, section_name in zip(tabs, section_names):
                    with tab:
                        section_text = sections[section_name]
                        st.markdown(f"""
                        <div style="
                            background-color: white;
                            padding: 1rem;
                            border-radius: 0.5rem;
                            border: 1px solid #e5e7eb;
                            max-height: 400px;
                            overflow-y: auto;
                        ">
                            {section_text}
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("No text sections found for this filing.")
        else:
            st.warning("Could not load filing text.")


def render_semantic_search_tab(api_base_url: str):
    """
    Render the semantic search tab.

    Args:
        api_base_url: Base URL of the API
    """
    st.subheader("🔍 Semantic Search")
    st.markdown("""
    Search filing text content using AI-powered semantic search.
    This understands the **meaning** of your query, not just keywords.

    **⚠️ Important Limitations:**
    Form 13F filings are regulatory documents that report holdings. They typically **do NOT contain**:
    - Investment strategies or philosophies
    - Investment theses or market commentary
    - Future plans or outlooks

    **✅ Best used for:**
    - Manager contact information
    - Amendment notices and explanations
    - Filing structure and disclosures

    **For investment holdings and position data, use the Chat or Portfolio tabs instead.**
    """)

    # Search configuration
    col1, col2 = st.columns([3, 1])

    with col1:
        search_query = st.text_input(
            "Search query",
            placeholder="e.g., investment strategies, risk management, technology sector",
            help="Enter a natural language query to search filing text"
        )

    with col2:
        top_k = st.slider(
            "Results",
            min_value=1,
            max_value=20,
            value=5,
            help="Number of results to return"
        )

    # Advanced filters
    with st.expander("⚙️ Advanced Filters"):
        col_a, col_b = st.columns(2)

        with col_a:
            filter_accession = st.text_input(
                "Filter by filing (accession number)",
                placeholder="e.g., 0001067983-25-000001",
                help="Optional: Search only within a specific filing"
            )

        with col_b:
            filter_content_type = st.selectbox(
                "Filter by section type",
                options=["All Sections", "cover_page_info", "explanatory_notes", "information_table"],
                help="Optional: Search only in specific section types"
            )

            # Convert "All Sections" to None
            if filter_content_type == "All Sections":
                filter_content_type = None

    # Example queries
    st.markdown("**Example Queries:**")
    example_col1, example_col2, example_col3 = st.columns(3)

    with example_col1:
        if st.button("📋 Filing Manager Info", use_container_width=True):
            search_query = "filing manager"
            st.rerun()

    with example_col2:
        if st.button("🏢 Relying Advisers", use_container_width=True):
            search_query = "relying adviser"
            st.rerun()

    with example_col3:
        if st.button("🔒 Confidential Treatment", use_container_width=True):
            search_query = "confidential treatment"
            st.rerun()

    # Search button
    if st.button("🔎 Search", type="primary", use_container_width=True, disabled=not search_query):
        if search_query:
            with st.spinner("Searching..."):
                # Store API URL in session state for use in expanders
                st.session_state["api_base_url"] = api_base_url

                results = semantic_search(
                    api_base_url,
                    search_query,
                    top_k=top_k,
                    filter_accession=filter_accession if filter_accession else None,
                    filter_content_type=filter_content_type
                )

            if results and results.get("success"):
                result_list = results.get("results", [])
                result_count = results.get("results_count", 0)

                if result_count > 0:
                    # Check if results are low quality (all scores below 0.5)
                    max_score = max([r.get("relevance_score", 0) for r in result_list]) if result_list else 0

                    if max_score < 0.5:
                        st.warning(f"⚠️ Found {result_count} result(s), but relevance scores are low.")
                        st.info("""
                        **Tip:** Form 13F filings typically don't contain detailed investment strategies or commentary.

                        If you're looking for:
                        - Investment strategies → Not disclosed in 13F filings
                        - Portfolio positions → Use the **Chat** or **Portfolio** tabs instead
                        - Holdings analysis → Try the SQL query interface

                        Best semantic search uses: manager contact info, amendments, regulatory disclosures
                        """)
                    else:
                        st.success(f"Found {result_count} result{'s' if result_count != 1 else ''}")

                    # AI Summarization button
                    if max_score >= 0.5:  # Only show if results are decent quality
                        st.markdown("---")
                        if st.button("✨ Summarize with AI", type="secondary", use_container_width=True,
                                   help="Generate a financial analyst-style summary using Claude (~$0.01 cost)"):
                            with st.spinner("AI is analyzing the results..."):
                                summary = summarize_results(api_base_url, search_query, result_list)

                            if summary and summary.get("success"):
                                st.info("**✨ AI Financial Analysis** (Powered by Claude)")
                                st.markdown(summary.get("summary", ""))
                            else:
                                st.error("Failed to generate summary. Please try again.")
                        st.markdown("---")

                    # Display results
                    for i, result in enumerate(result_list, 1):
                        display_search_result(result, i)
                else:
                    st.info("No results found. Try a different query or adjust filters.")
            else:
                st.error("Search failed. Please try again.")


def render_filing_text_explorer_tab(api_base_url: str):
    """
    Render the filing text explorer tab.

    Args:
        api_base_url: Base URL of the API
    """
    st.subheader("📄 Filing Text Explorer")
    st.markdown("""
    View the complete text content of any Form 13F filing, organized by section.
    """)

    # Accession number input
    accession_number = st.text_input(
        "Filing Accession Number",
        placeholder="e.g., 0001067983-25-000001",
        help="Enter the SEC accession number for the filing you want to view"
    )

    # Content type filter
    content_type_filter = st.selectbox(
        "Section Filter",
        options=["All Sections", "cover_page_info", "explanatory_notes", "information_table"],
        help="View all sections or filter to a specific type"
    )

    # Convert "All Sections" to None
    if content_type_filter == "All Sections":
        content_type_filter = None

    if st.button("📖 Load Filing Text", type="primary", disabled=not accession_number):
        if accession_number:
            with st.spinner("Loading filing text..."):
                filing_data = get_filing_text(api_base_url, accession_number, content_type_filter)

            if filing_data and filing_data.get("success"):
                sections = filing_data.get("sections", {})
                sections_found = filing_data.get("sections_found", [])
                total_sections = filing_data.get("total_sections", 0)

                if total_sections > 0:
                    # Display filing metadata
                    st.success(f"Loaded {total_sections} section{'s' if total_sections != 1 else ''}")

                    st.markdown(f"""
                    <div style="
                        background-color: #eff6ff;
                        padding: 1rem;
                        border-radius: 0.5rem;
                        margin: 1rem 0;
                        border-left: 4px solid #3b82f6;
                    ">
                        <strong>Filing:</strong> {filing_data.get('accession_number', 'N/A')}<br>
                        <strong>Sections:</strong> {', '.join([s.replace('_', ' ').title() for s in sections_found])}
                    </div>
                    """, unsafe_allow_html=True)

                    # Display sections in tabs
                    tabs = st.tabs([name.replace("_", " ").title() for name in sections_found])

                    for tab, section_name in zip(tabs, sections_found):
                        with tab:
                            section_text = sections[section_name]

                            # Character count
                            st.caption(f"Length: {len(section_text):,} characters")

                            # Display text in a scrollable container
                            st.markdown(f"""
                            <div style="
                                background-color: white;
                                padding: 1.5rem;
                                border-radius: 0.5rem;
                                border: 1px solid #e5e7eb;
                                max-height: 600px;
                                overflow-y: auto;
                                line-height: 1.6;
                            ">
                                {section_text}
                            </div>
                            """, unsafe_allow_html=True)

                            # Download button for this section
                            st.download_button(
                                label=f"Download {section_name.replace('_', ' ').title()}",
                                data=section_text,
                                file_name=f"{accession_number}_{section_name}.txt",
                                mime="text/plain"
                            )
                else:
                    st.info("No text sections found for this filing.")
            else:
                st.error("Filing not found or no text content available.")
