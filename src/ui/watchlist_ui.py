"""
Watchlist UI Components for Streamlit

Displays and manages user's watchlist in the sidebar.
"""

import streamlit as st
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime


def fetch_watchlist(api_base_url: str, auth_headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """
    Fetch user's watchlist from API.

    Args:
        api_base_url: Base URL for the API
        auth_headers: Authorization headers with Bearer token

    Returns:
        Watchlist data dict or None if error
    """
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{api_base_url}/api/v1/watchlist",
                headers=auth_headers
            )

            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"Failed to fetch watchlist: {response.status_code}")
                return None

    except Exception as e:
        st.error(f"Error fetching watchlist: {str(e)}")
        return None


def add_to_watchlist(
    api_base_url: str,
    auth_headers: Dict[str, str],
    item_type: str,
    cik: Optional[str] = None,
    cusip: Optional[str] = None,
    notes: Optional[str] = None
) -> bool:
    """
    Add item to watchlist.

    Args:
        api_base_url: Base URL for the API
        auth_headers: Authorization headers
        item_type: 'manager' or 'security'
        cik: Manager CIK (if item_type='manager')
        cusip: Security CUSIP (if item_type='security')
        notes: Optional notes

    Returns:
        True if successful, False otherwise
    """
    try:
        payload = {
            "item_type": item_type,
            "notes": notes
        }

        if item_type == "manager" and cik:
            payload["cik"] = cik
        elif item_type == "security" and cusip:
            payload["cusip"] = cusip
        else:
            st.error("Invalid item type or missing identifier")
            return False

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{api_base_url}/api/v1/watchlist/items",
                headers=auth_headers,
                json=payload
            )

            if response.status_code in [200, 201]:
                return True
            else:
                error_detail = response.json().get("detail", "Unknown error")
                st.error(f"Failed to add to watchlist: {error_detail}")
                return False

    except Exception as e:
        st.error(f"Error adding to watchlist: {str(e)}")
        return False


def remove_from_watchlist(
    api_base_url: str,
    auth_headers: Dict[str, str],
    item_id: int
) -> bool:
    """
    Remove item from watchlist.

    Args:
        api_base_url: Base URL for the API
        auth_headers: Authorization headers
        item_id: Watchlist item ID

    Returns:
        True if successful, False otherwise
    """
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.delete(
                f"{api_base_url}/api/v1/watchlist/items/{item_id}",
                headers=auth_headers
            )

            if response.status_code == 204:
                return True
            else:
                st.error(f"Failed to remove from watchlist: {response.status_code}")
                return False

    except Exception as e:
        st.error(f"Error removing from watchlist: {str(e)}")
        return False


def update_watchlist_notes(
    api_base_url: str,
    auth_headers: Dict[str, str],
    item_id: int,
    notes: str
) -> bool:
    """
    Update notes for a watchlist item.

    Args:
        api_base_url: Base URL for the API
        auth_headers: Authorization headers
        item_id: Watchlist item ID
        notes: New notes text

    Returns:
        True if successful, False otherwise
    """
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.patch(
                f"{api_base_url}/api/v1/watchlist/items/{item_id}",
                headers=auth_headers,
                json={"notes": notes}
            )

            if response.status_code == 200:
                return True
            else:
                st.error(f"Failed to update notes: {response.status_code}")
                return False

    except Exception as e:
        st.error(f"Error updating notes: {str(e)}")
        return False


def format_value(value: Optional[int]) -> str:
    """Format large numbers with commas and abbreviations."""
    if value is None:
        return "N/A"

    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    elif value >= 1_000:
        return f"${value / 1_000:.2f}K"
    else:
        return f"${value:,.0f}"


def format_change(change: Optional[float]) -> str:
    """Format percentage change with color."""
    if change is None:
        return ""

    color = "green" if change >= 0 else "red"
    sign = "+" if change >= 0 else ""
    return f"<span style='color: {color};'>{sign}{change:.1f}%</span>"


def show_watchlist_sidebar(api_base_url: str, auth_headers: Dict[str, str]):
    """
    Display watchlist in the sidebar.

    Args:
        api_base_url: Base URL for the API
        auth_headers: Authorization headers with Bearer token
    """
    st.markdown("---")
    st.subheader("📋 My Watchlist")

    # Fetch watchlist
    watchlist = fetch_watchlist(api_base_url, auth_headers)

    if not watchlist:
        st.info("Your watchlist is empty. Add managers or securities to track them!")
        return

    items = watchlist.get("items", [])

    if not items:
        st.info("Your watchlist is empty. Add managers or securities to track them!")
        return

    # Separate managers and securities
    managers = [item for item in items if item["item_type"] == "manager"]
    securities = [item for item in items if item["item_type"] == "security"]

    # Display managers
    if managers:
        st.markdown("**📊 Managers**")
        for item in managers:
            with st.expander(f"{item.get('name', 'Unknown Manager')}", expanded=False):
                # Display metrics
                if item.get('latest_value'):
                    st.metric(
                        "Portfolio Value",
                        format_value(item['latest_value']),
                        delta=f"{item.get('value_change_percent', 0):.1f}%" if item.get('value_change_percent') is not None else None
                    )

                if item.get('latest_period'):
                    st.caption(f"As of {item['latest_period']}")

                # Notes
                if item.get('notes'):
                    st.caption(f"📝 {item['notes']}")

                # Actions
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🗑️ Remove", key=f"remove_mgr_{item['id']}"):
                        if remove_from_watchlist(api_base_url, auth_headers, item['id']):
                            st.success("Removed from watchlist!")
                            st.rerun()

                with col2:
                    if st.button("✏️ Notes", key=f"notes_mgr_{item['id']}"):
                        st.session_state[f"editing_notes_{item['id']}"] = True

                # Edit notes inline
                if st.session_state.get(f"editing_notes_{item['id']}", False):
                    new_notes = st.text_area(
                        "Notes",
                        value=item.get('notes', ''),
                        key=f"notes_input_mgr_{item['id']}"
                    )
                    if st.button("Save Notes", key=f"save_notes_mgr_{item['id']}"):
                        if update_watchlist_notes(api_base_url, auth_headers, item['id'], new_notes):
                            st.success("Notes updated!")
                            st.session_state[f"editing_notes_{item['id']}"] = False
                            st.rerun()

    # Display securities
    if securities:
        st.markdown("**💼 Securities**")
        for item in securities:
            with st.expander(f"{item.get('name', 'Unknown Security')}", expanded=False):
                # Display metrics
                if item.get('latest_value'):
                    st.metric(
                        "Latest Value",
                        format_value(item['latest_value']),
                        delta=f"{item.get('value_change_percent', 0):.1f}%" if item.get('value_change_percent') is not None else None
                    )

                if item.get('latest_period'):
                    st.caption(f"As of {item['latest_period']}")

                # Notes
                if item.get('notes'):
                    st.caption(f"📝 {item['notes']}")

                # Actions
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🗑️ Remove", key=f"remove_sec_{item['id']}"):
                        if remove_from_watchlist(api_base_url, auth_headers, item['id']):
                            st.success("Removed from watchlist!")
                            st.rerun()

                with col2:
                    if st.button("✏️ Notes", key=f"notes_sec_{item['id']}"):
                        st.session_state[f"editing_notes_{item['id']}"] = True

                # Edit notes inline
                if st.session_state.get(f"editing_notes_{item['id']}", False):
                    new_notes = st.text_area(
                        "Notes",
                        value=item.get('notes', ''),
                        key=f"notes_input_sec_{item['id']}"
                    )
                    if st.button("Save Notes", key=f"save_notes_sec_{item['id']}"):
                        if update_watchlist_notes(api_base_url, auth_headers, item['id'], new_notes):
                            st.success("Notes updated!")
                            st.session_state[f"editing_notes_{item['id']}"] = False
                            st.rerun()

    st.caption(f"Total items: {len(items)}")
