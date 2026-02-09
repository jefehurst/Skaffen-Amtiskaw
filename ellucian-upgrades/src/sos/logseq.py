"""Logseq HTTP API client."""

import os
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class LogseqConfig:
    """Configuration for Logseq API connection."""

    token: str
    host: str = "127.0.0.1"
    port: int = 12315

    @classmethod
    def from_env(cls) -> "LogseqConfig":
        """Create config from environment variables."""
        token = os.environ.get("LOGSEQ_TOKEN")
        if not token:
            raise ValueError("LOGSEQ_TOKEN environment variable required")

        return cls(
            token=token,
            host=os.environ.get("LOGSEQ_HOST", "127.0.0.1"),
            port=int(os.environ.get("LOGSEQ_PORT", "12315")),
        )

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


def call_api(config: LogseqConfig, method: str, *args: Any) -> Any:
    """Make a call to the Logseq HTTP API.

    Args:
        config: Logseq connection configuration
        method: API method name (e.g., "logseq.Editor.getAllPages")
        *args: Arguments to pass to the method

    Returns:
        API response data, or None if empty response

    Raises:
        httpx.HTTPStatusError: If the request fails
    """
    response = httpx.post(
        f"{config.base_url}/api",
        headers={
            "Authorization": f"Bearer {config.token}",
            "Content-Type": "application/json",
        },
        json={"method": method, "args": list(args)},
        timeout=30.0,
    )
    response.raise_for_status()
    # Some API calls return empty body (void)
    if not response.content:
        return None
    return response.json()


def datascript_query(config: LogseqConfig, query: str, *inputs: Any) -> list[Any]:
    """Run a Datalog query against the Logseq graph database.

    Args:
        config: Logseq connection configuration
        query: Datalog query string
        *inputs: Additional inputs for the query (bound to ?in variables)

    Returns:
        Query results as a list

    Example:
        >>> query = '''
        ... [:find ?content ?updated
        ...  :where
        ...  [?b :block/content ?content]
        ...  [?b :block/updated-at ?updated]
        ...  [(> ?updated 1733400000000)]]
        ... '''
        >>> results = datascript_query(config, query)
    """
    return call_api(config, "logseq.DB.datascriptQuery", query, *inputs)


def get_changed_pages(config: LogseqConfig, since_ms: int) -> list[dict[str, Any]]:
    """Get pages modified since a given timestamp.

    Note: Logseq only tracks updated-at on pages, not individual blocks.
    When any block on a page changes, the page's updated-at is updated.

    Args:
        config: Logseq connection configuration
        since_ms: Unix timestamp in milliseconds

    Returns:
        List of page data with uuid, name, and updated-at
    """
    query = """
    [:find (pull ?p [:block/uuid :block/name :block/original-name
                     :block/updated-at :block/journal-day])
     :in $ ?since
     :where
     [?p :block/name _]
     [?p :block/updated-at ?updated]
     [(>= ?updated ?since)]]
    """
    results = datascript_query(config, query, since_ms)
    return [r[0] for r in results if r and r[0]]


def get_recent_blocks(config: LogseqConfig, since_ms: int) -> list[dict[str, Any]]:
    """Get blocks from pages modified since a given timestamp.

    Note: Logseq tracks updated-at on pages, not blocks. This returns
    all blocks from recently-modified pages along with page metadata.

    Args:
        config: Logseq connection configuration
        since_ms: Unix timestamp in milliseconds

    Returns:
        List of dicts with 'page' info and 'blocks' from that page
    """
    changed_pages = get_changed_pages(config, since_ms)
    if not changed_pages:
        return []

    results = []
    for page in changed_pages:
        page_name = page.get("name") or page.get("original-name")
        if page_name:
            blocks = get_page_blocks_tree(config, page_name)
            results.append(
                {
                    "page": page,
                    "blocks": blocks,
                }
            )
    return results


def get_page_blocks_tree(config: LogseqConfig, page_name: str) -> list[dict[str, Any]]:
    """Get all blocks on a page as a tree structure.

    Args:
        config: Logseq connection configuration
        page_name: Name of the page

    Returns:
        List of block entities with children
    """
    return call_api(config, "logseq.Editor.getPageBlocksTree", page_name)


def update_block(
    config: LogseqConfig,
    block_uuid: str,
    content: str,
    properties: dict[str, Any] | None = None,
) -> None:
    """Update a block's content.

    Args:
        config: Logseq connection configuration
        block_uuid: UUID of the block to update
        content: New content for the block
        properties: Optional properties to set (replaces existing!)
    """
    opts = {"properties": properties} if properties else {}
    call_api(config, "logseq.Editor.updateBlock", block_uuid, content, opts)


def remove_block(config: LogseqConfig, block_uuid: str) -> None:
    """Delete a block.

    Args:
        config: Logseq connection configuration
        block_uuid: UUID of the block to remove
    """
    call_api(config, "logseq.Editor.removeBlock", block_uuid)


def insert_block(
    config: LogseqConfig,
    parent_uuid: str,
    content: str,
    *,
    sibling: bool = False,
    before: bool = False,
    properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Insert a new block.

    Args:
        config: Logseq connection configuration
        parent_uuid: UUID of the parent/sibling block
        content: Content for the new block
        sibling: If True, insert as sibling; if False, as child
        before: If True, insert before the reference block
        properties: Optional properties for the block

    Returns:
        The created block entity
    """
    opts: dict[str, Any] = {"sibling": sibling, "before": before}
    if properties:
        opts["properties"] = properties
    return call_api(config, "logseq.Editor.insertBlock", parent_uuid, content, opts)


def flatten_blocks(blocks: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Flatten a block tree into a dict keyed by UUID.

    Args:
        blocks: Block tree from get_page_blocks_tree

    Returns:
        Dict mapping UUID -> block data (without children)
    """
    result = {}

    def walk(block_list: list[dict[str, Any]]) -> None:
        for block in block_list:
            uuid = block.get("uuid")
            if uuid:
                # Store block without children to avoid circular refs
                flat_block = {k: v for k, v in block.items() if k != "children"}
                result[uuid] = flat_block
            children = block.get("children", [])
            if children:
                walk(children)

    walk(blocks)
    return result


def diff_blocks(
    old_blocks: dict[str, dict[str, Any]],
    new_blocks: dict[str, dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Compute diff between two flattened block dicts.

    Args:
        old_blocks: Previous state (UUID -> block)
        new_blocks: Current state (UUID -> block)

    Returns:
        Dict with 'added', 'removed', 'modified' lists of blocks
    """
    old_uuids = set(old_blocks.keys())
    new_uuids = set(new_blocks.keys())

    added = [new_blocks[uuid] for uuid in (new_uuids - old_uuids)]
    removed = [old_blocks[uuid] for uuid in (old_uuids - new_uuids)]

    modified = []
    for uuid in old_uuids & new_uuids:
        old_content = old_blocks[uuid].get("content", "")
        new_content = new_blocks[uuid].get("content", "")
        if old_content != new_content:
            modified.append(
                {
                    "uuid": uuid,
                    "old_content": old_content,
                    "new_content": new_content,
                    "block": new_blocks[uuid],
                }
            )

    return {"added": added, "removed": removed, "modified": modified}


def get_descendants(config: LogseqConfig, parent_uuid: str) -> list[dict[str, Any]]:
    """Get all descendant blocks under a parent block recursively.

    Args:
        config: Logseq connection configuration
        parent_uuid: UUID of the parent block

    Returns:
        Flat list of all descendant blocks with uuid, content, marker
    """
    query = f"""[:find ?uuid ?content ?marker
     :where
     [?parent :block/uuid #uuid "{parent_uuid}"]
     [?b :block/parent ?parent]
     [?b :block/uuid ?uuid]
     [?b :block/content ?content]
     [(get-else $ ?b :block/marker "") ?marker]]"""

    results = datascript_query(config, query)
    all_blocks = []

    for uuid_val, content, marker in results:
        uuid_str = str(uuid_val)
        all_blocks.append({"uuid": uuid_str, "content": content, "marker": marker})
        # Recursively get children
        all_blocks.extend(get_descendants(config, uuid_str))

    return all_blocks


def find_blocks_by_marker(
    config: LogseqConfig,
    page_name: str,
    marker: str,
    parent_uuid: str | None = None,
) -> list[dict[str, Any]]:
    """Find blocks with a specific marker on a page.

    Args:
        config: Logseq connection configuration
        page_name: Name of the page to search
        marker: Task marker to filter by (e.g., "DONE", "LATER", "TODO")
        parent_uuid: Optional - only find blocks under this parent

    Returns:
        List of matching blocks with uuid, content, marker
    """
    if parent_uuid:
        # Get descendants of the parent and filter by marker
        descendants = get_descendants(config, parent_uuid)
        return [b for b in descendants if b.get("marker") == marker]
    else:
        # Search entire page
        query = f"""[:find ?uuid ?content ?marker
         :where
         [?p :block/name "{page_name.lower()}"]
         [?b :block/page ?p]
         [?b :block/uuid ?uuid]
         [?b :block/content ?content]
         [?b :block/marker "{marker}"]
         [(get-else $ ?b :block/marker "") ?marker]]"""
        results = datascript_query(config, query)
        return [{"uuid": str(r[0]), "content": r[1], "marker": r[2]} for r in results]


def find_section_uuid(config: LogseqConfig, page_name: str, heading: str) -> str | None:
    """Find the UUID of a section heading on a page.

    Args:
        config: Logseq connection configuration
        page_name: Name of the page
        heading: Heading text to find (e.g., "### PROD")

    Returns:
        UUID of the heading block, or None if not found
    """
    query = f"""[:find ?uuid ?content
     :where
     [?p :block/name "{page_name.lower()}"]
     [?b :block/page ?p]
     [?b :block/uuid ?uuid]
     [?b :block/content ?content]
     [(clojure.string/includes? ?content "{heading}")]]"""

    results = datascript_query(config, query)
    for uuid_val, content in results:
        if heading in content:
            return str(uuid_val)
    return None
