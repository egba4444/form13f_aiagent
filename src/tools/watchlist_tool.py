"""
Watchlist Tool for AI Agent.

Enables the agent to add managers or securities to the user's watchlist.
"""

import httpx
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class WatchlistTool:
    """Tool for managing user's watchlist."""

    def __init__(self, api_base_url: str, auth_token: str):
        """
        Initialize watchlist tool.

        Args:
            api_base_url: Base URL for the API
            auth_token: User's authentication token
        """
        self.api_base_url = api_base_url
        self.auth_headers = {
            "Authorization": f"Bearer {auth_token}"
        }

    def add_to_watchlist(
        self,
        item_type: str,
        cik: Optional[str] = None,
        cusip: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add a manager or security to the user's watchlist.

        Args:
            item_type: Type of item - must be "manager" or "security"
            cik: Manager CIK (required if item_type="manager")
            cusip: Security CUSIP (required if item_type="security")
            notes: Optional notes about the item

        Returns:
            Dict with success status and result data or error message

        Examples:
            # Add Berkshire Hathaway (manager)
            result = tool.add_to_watchlist(
                item_type="manager",
                cik="0001067983",
                notes="Warren Buffett's company"
            )

            # Add Apple (security)
            result = tool.add_to_watchlist(
                item_type="security",
                cusip="037833100",
                notes="Tech giant"
            )
        """
        try:
            # Validate inputs
            if item_type not in ["manager", "security"]:
                return {
                    "success": False,
                    "error": "item_type must be 'manager' or 'security'"
                }

            if item_type == "manager" and not cik:
                return {
                    "success": False,
                    "error": "cik is required when item_type is 'manager'"
                }

            if item_type == "security" and not cusip:
                return {
                    "success": False,
                    "error": "cusip is required when item_type is 'security'"
                }

            # Build payload
            payload = {
                "item_type": item_type,
                "notes": notes
            }

            if item_type == "manager":
                payload["cik"] = cik
            else:
                payload["cusip"] = cusip

            # Make API request
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.api_base_url}/api/v1/watchlist/items",
                    headers=self.auth_headers,
                    json=payload
                )

                if response.status_code in [200, 201]:
                    data = response.json()
                    return {
                        "success": True,
                        "item": data,
                        "message": f"Successfully added {data.get('name', 'item')} to your watchlist"
                    }
                elif response.status_code == 409:
                    return {
                        "success": False,
                        "error": "This item is already in your watchlist"
                    }
                elif response.status_code == 404:
                    error_detail = response.json().get("detail", "Not found")
                    return {
                        "success": False,
                        "error": f"Could not find that {item_type}: {error_detail}"
                    }
                else:
                    error_detail = response.json().get("detail", "Unknown error")
                    return {
                        "success": False,
                        "error": f"Failed to add to watchlist: {error_detail}"
                    }

        except Exception as e:
            logger.error(f"Error adding to watchlist: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Error adding to watchlist: {str(e)}"
            }

    def get_tool_definition(self) -> Dict[str, Any]:
        """
        Get LiteLLM tool definition for the watchlist tool.

        Returns:
            Tool definition dict compatible with LiteLLM function calling
        """
        return {
            "type": "function",
            "function": {
                "name": "add_to_watchlist",
                "description": "Add a manager (like Berkshire Hathaway) or security (like Apple stock) to the user's watchlist. Use this when the user asks to add, track, or watch a specific manager or security.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "item_type": {
                            "type": "string",
                            "enum": ["manager", "security"],
                            "description": "Type of item to add: 'manager' for institutional managers/hedge funds, 'security' for stocks/securities"
                        },
                        "cik": {
                            "type": "string",
                            "description": "Manager's CIK number (required if item_type is 'manager'). Must be 10 digits with leading zeros (e.g., '0001067983' for Berkshire Hathaway)"
                        },
                        "cusip": {
                            "type": "string",
                            "description": "Security's CUSIP number (required if item_type is 'security'). Must be 9 characters (e.g., '037833100' for Apple Inc)"
                        },
                        "notes": {
                            "type": "string",
                            "description": "Optional notes about why you're tracking this item"
                        }
                    },
                    "required": ["item_type"]
                }
            }
        }
