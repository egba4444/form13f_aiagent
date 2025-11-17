"""
Watchlist Tool for AI Agent.

Enables the agent to add managers or securities to the user's watchlist.
"""

from typing import Optional, Dict, Any
import logging
from ..services.watchlist_service import WatchlistService

logger = logging.getLogger(__name__)


class WatchlistTool:
    """Tool for managing user's watchlist."""

    def __init__(self, database_url: str, user_id: str):
        """
        Initialize watchlist tool.

        Args:
            database_url: PostgreSQL connection string
            user_id: User's UUID
        """
        self.database_url = database_url
        self.user_id = user_id
        self.service = WatchlistService(database_url)

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
        return self.service.add_item(
            user_id=self.user_id,
            item_type=item_type,
            cik=cik,
            cusip=cusip,
            notes=notes
        )

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
