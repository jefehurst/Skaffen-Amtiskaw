"""Fetch and interact with Ellucian Support tickets (ServiceNow cases)."""

from dataclasses import dataclass
from typing import Any

import httpx

from .auth import AuthSession

SERVICENOW_BASE = "https://elluciansupport.service-now.com"
CASE_TABLE = "sn_customerservice_case"


class TicketError(Exception):
    """Ticket operation failed."""

    pass


@dataclass
class Ticket:
    """Support ticket/case."""

    sys_id: str
    number: str
    short_description: str
    description: str
    state: str
    priority: str
    created_on: str
    updated_on: str
    contact: str
    raw: dict[str, Any]

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Ticket":
        """Create from ServiceNow API response."""
        return cls(
            sys_id=data.get("sys_id", ""),
            number=data.get("number", ""),
            short_description=data.get("short_description", ""),
            description=data.get("description", ""),
            state=data.get("state", ""),
            priority=data.get("priority", ""),
            created_on=data.get("sys_created_on", ""),
            updated_on=data.get("sys_updated_on", ""),
            contact=data.get("contact", {}).get("display_value", "")
            if isinstance(data.get("contact"), dict)
            else str(data.get("contact", "")),
            raw=data,
        )


@dataclass
class TicketComment:
    """Comment/work note on a ticket."""

    sys_id: str
    value: str
    created_on: str
    created_by: str
    element: str  # 'comments' or 'work_notes'

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "TicketComment":
        """Create from ServiceNow API response."""
        created_by = data.get("sys_created_by", "")
        if isinstance(created_by, dict):
            created_by = created_by.get("display_value", "")
        return cls(
            sys_id=data.get("sys_id", ""),
            value=data.get("value", ""),
            created_on=data.get("sys_created_on", ""),
            created_by=created_by,
            element=data.get("element", ""),
        )


def _get_client(session: AuthSession) -> httpx.Client:
    """Create HTTP client with session cookies."""
    client = httpx.Client(timeout=30.0)
    for name, value in session.cookies.items():
        client.cookies.set(name, value, domain="elluciansupport.service-now.com")
    return client


def get_ticket(session: AuthSession, number: str) -> Ticket:
    """Fetch a ticket by case number.

    Args:
        session: Authenticated session.
        number: Case number (e.g., 'CSC03683039' or '02510949').

    Returns:
        Ticket object.

    Raises:
        TicketError: If ticket not found or fetch fails.
    """
    with _get_client(session) as client:
        url = f"{SERVICENOW_BASE}/api/now/table/{CASE_TABLE}"
        resp = client.get(
            url,
            params={
                "sysparm_query": f"number={number}",
                "sysparm_limit": 1,
                "sysparm_display_value": "true",
            },
            headers={"Accept": "application/json"},
        )

        if resp.status_code != 200:
            raise TicketError(f"Failed to fetch ticket (status {resp.status_code})")

        data = resp.json()
        results = data.get("result", [])

        if not results:
            raise TicketError(f"Ticket not found: {number}")

        return Ticket.from_api(results[0])


def list_tickets(
    session: AuthSession,
    limit: int = 10,
    state: str | None = None,
) -> list[Ticket]:
    """List tickets for the authenticated user.

    Args:
        session: Authenticated session.
        limit: Maximum number of tickets to return.
        state: Filter by state (e.g., 'open', 'closed').

    Returns:
        List of Ticket objects.
    """
    with _get_client(session) as client:
        url = f"{SERVICENOW_BASE}/api/now/table/{CASE_TABLE}"

        query_parts = []
        if state:
            query_parts.append(f"state={state}")
        query = "^".join(query_parts) if query_parts else None

        params = {
            "sysparm_limit": limit,
            "sysparm_display_value": "true",
            "sysparm_order_by": "sys_updated_on",
            "sysparm_order_direction": "desc",
        }
        if query:
            params["sysparm_query"] = query

        resp = client.get(url, params=params, headers={"Accept": "application/json"})

        if resp.status_code != 200:
            raise TicketError(f"Failed to list tickets (status {resp.status_code})")

        data = resp.json()
        return [Ticket.from_api(r) for r in data.get("result", [])]


def get_comments(session: AuthSession, ticket_sys_id: str) -> list[TicketComment]:
    """Get comments/work notes for a ticket.

    Args:
        session: Authenticated session.
        ticket_sys_id: The sys_id of the ticket.

    Returns:
        List of TicketComment objects, newest first.
    """
    with _get_client(session) as client:
        url = f"{SERVICENOW_BASE}/api/now/table/sys_journal_field"
        resp = client.get(
            url,
            params={
                "sysparm_query": f"element_id={ticket_sys_id}^elementINcomments,work_notes",
                "sysparm_order_by": "sys_created_on",
                "sysparm_order_direction": "desc",
                "sysparm_display_value": "true",
            },
            headers={"Accept": "application/json"},
        )

        if resp.status_code != 200:
            return []

        data = resp.json()
        return [TicketComment.from_api(r) for r in data.get("result", [])]


def add_comment(session: AuthSession, ticket_sys_id: str, comment: str) -> bool:
    """Add a comment to a ticket.

    Args:
        session: Authenticated session.
        ticket_sys_id: The sys_id of the ticket.
        comment: Comment text to add.

    Returns:
        True if successful.

    Raises:
        TicketError: If comment fails.
    """
    with _get_client(session) as client:
        url = f"{SERVICENOW_BASE}/api/now/table/{CASE_TABLE}/{ticket_sys_id}"
        resp = client.patch(
            url,
            json={"comments": comment},
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

        if resp.status_code not in (200, 201):
            raise TicketError(f"Failed to add comment (status {resp.status_code}): {resp.text[:200]}")

        return True
