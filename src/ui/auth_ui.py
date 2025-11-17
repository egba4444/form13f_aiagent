"""
Authentication UI Components for Streamlit

Handles login, signup, and session management.
"""

import streamlit as st
import httpx
from typing import Optional, Dict, Any


def show_login_page(api_base_url: str) -> bool:
    """
    Display login/signup page and handle authentication.

    Args:
        api_base_url: Base URL for the API

    Returns:
        True if user is authenticated, False otherwise
    """
    # Check if already authenticated
    if st.session_state.get("authenticated", False):
        return True

    # Custom CSS for login page
    st.markdown("""
    <style>
        .login-container {
            max-width: 400px;
            margin: 5rem auto;
            padding: 2rem;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        .login-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        .login-title {
            font-size: 2rem;
            font-weight: 700;
            color: #1f2937;
            margin-bottom: 0.5rem;
        }
        .login-subtitle {
            font-size: 1rem;
            color: #6b7280;
        }
    </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown("""
    <div class="login-header">
        <div class="login-title">📊 Form 13F AI Agent</div>
        <div class="login-subtitle">Sign in to track your watchlist</div>
    </div>
    """, unsafe_allow_html=True)

    # Create tabs for login/signup
    tab1, tab2 = st.tabs(["Sign In", "Sign Up"])

    with tab1:
        _show_signin_form(api_base_url)

    with tab2:
        _show_signup_form(api_base_url)

    return False


def _show_signin_form(api_base_url: str):
    """Display sign-in form"""
    with st.form("signin_form"):
        email = st.text_input("Email", key="signin_email")
        password = st.text_input("Password", type="password", key="signin_password")
        submit = st.form_submit_button("Sign In", use_container_width=True)

        if submit:
            if not email or not password:
                st.error("Please enter both email and password")
                return

            # Call signin API
            try:
                with httpx.Client(timeout=30.0) as client:
                    response = client.post(
                        f"{api_base_url}/api/v1/auth/signin",
                        json={"email": email, "password": password}
                    )

                    if response.status_code == 200:
                        data = response.json()

                        if data.get("success") and data.get("session"):
                            # Store auth token in session state
                            st.session_state.authenticated = True
                            st.session_state.auth_token = data["session"]["access_token"]
                            st.session_state.user = data.get("user", {})
                            st.success("✅ Signed in successfully!")
                            st.rerun()
                        else:
                            st.error(data.get("error", "Sign in failed"))
                    else:
                        error_detail = response.json().get("detail", "Sign in failed")
                        st.error(f"❌ {error_detail}")

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")


def _show_signup_form(api_base_url: str):
    """Display sign-up form"""
    with st.form("signup_form"):
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_password",
                                help="Minimum 6 characters")
        password_confirm = st.text_input("Confirm Password", type="password", key="signup_password_confirm")
        submit = st.form_submit_button("Sign Up", use_container_width=True)

        if submit:
            # Validation
            if not email or not password:
                st.error("Please enter both email and password")
                return

            if len(password) < 6:
                st.error("Password must be at least 6 characters")
                return

            if password != password_confirm:
                st.error("Passwords do not match")
                return

            # Call signup API
            try:
                with httpx.Client(timeout=30.0) as client:
                    response = client.post(
                        f"{api_base_url}/api/v1/auth/signup",
                        json={"email": email, "password": password}
                    )

                    if response.status_code == 200 or response.status_code == 201:
                        data = response.json()

                        if data.get("success"):
                            if data.get("session"):
                                # Auto sign-in (no email confirmation required)
                                st.session_state.authenticated = True
                                st.session_state.auth_token = data["session"]["access_token"]
                                st.session_state.user = data.get("user", {})
                                st.success("✅ Account created and signed in!")
                                st.rerun()
                            else:
                                # Email confirmation required
                                st.success("✅ " + data.get("message", "Account created! Please check your email to confirm."))
                                st.info("After confirming your email, use the Sign In tab to log in.")
                        else:
                            st.error(data.get("error", "Sign up failed"))
                    else:
                        error_detail = response.json().get("detail", "Sign up failed")
                        st.error(f"❌ {error_detail}")

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")


def show_logout_button():
    """Display logout button in sidebar"""
    if st.session_state.get("authenticated", False):
        user_email = st.session_state.get("user", {}).get("email", "User")

        with st.sidebar:
            st.divider()
            st.caption(f"Signed in as: {user_email}")

            if st.button("🚪 Sign Out", use_container_width=True):
                # Clear session state
                st.session_state.authenticated = False
                st.session_state.auth_token = None
                st.session_state.user = None
                st.session_state.watchlist = None
                st.success("Signed out successfully")
                st.rerun()


def get_auth_headers() -> Optional[Dict[str, str]]:
    """
    Get authentication headers for API requests.

    Returns:
        Dict with Authorization header if authenticated, None otherwise
    """
    if st.session_state.get("authenticated") and st.session_state.get("auth_token"):
        return {
            "Authorization": f"Bearer {st.session_state.auth_token}"
        }
    return None


def require_auth(api_base_url: str) -> bool:
    """
    Require authentication to access the page.

    Shows login page if not authenticated.

    Args:
        api_base_url: Base URL for the API

    Returns:
        True if authenticated, False otherwise
    """
    if not st.session_state.get("authenticated", False):
        show_login_page(api_base_url)
        return False
    return True
