"""Logseq CLI - Logseq API extensions."""

import json
import sys
import time
from typing import Annotated, Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.json import JSON
from rich.table import Table

from sos.logseq import (
    LogseqConfig,
    datascript_query,
    find_section_uuid,
    get_changed_pages,
    get_descendants,
    get_page_blocks_tree,
    insert_block,
    remove_block,
    update_block,
)

app = typer.Typer(
    name="lsq",
    help="Logseq API extensions CLI",
    no_args_is_help=True,
)
console = Console()


def get_config() -> LogseqConfig:
    """Get Logseq config from environment, with error handling."""
    try:
        return LogseqConfig.from_env()
    except ValueError as e:
        rprint(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command()
def query(
    datalog: Annotated[str, typer.Argument(help="Datalog query string")],
    raw: Annotated[bool, typer.Option("--raw", "-r", help="Output raw JSON")] = False,
) -> None:
    """Run a Datalog query against the Logseq graph database.

    Example:
        lsq query '[:find ?name :where [?p :block/name ?name]]'
    """
    config = get_config()
    try:
        results = datascript_query(config, datalog)
        if raw:
            print(json.dumps(results, indent=2, default=str))
        else:
            rprint(JSON(json.dumps(results, default=str)))
    except Exception as e:
        rprint(f"[red]Query failed:[/red] {e}")
        raise typer.Exit(1) from e


@app.command()
def recent(
    minutes: Annotated[int, typer.Option("--minutes", "-m", help="Look back N minutes")] = 5,
    raw: Annotated[bool, typer.Option("--raw", "-r", help="Output raw JSON")] = False,
) -> None:
    """Get pages modified in the last N minutes.

    Useful for detecting changes made in Logseq.
    Note: Logseq tracks changes at page level, not block level.
    """
    config = get_config()
    since_ms = int((time.time() - (minutes * 60)) * 1000)

    try:
        pages = get_changed_pages(config, since_ms)
        if raw:
            print(json.dumps(pages, indent=2, default=str))
        elif not pages:
            rprint(f"[dim]No pages modified in the last {minutes} minutes[/dim]")
        else:
            table = Table(title=f"Pages modified in last {minutes} minutes")
            table.add_column("Page", max_width=40)
            table.add_column("Updated", style="cyan")
            table.add_column("Journal", style="dim")

            for page in pages:
                name = page.get("original-name") or page.get("name", "")
                updated = page.get("updated-at", "")
                journal = "Yes" if page.get("journal-day") else ""
                table.add_row(name, str(updated), journal)

            console.print(table)
    except Exception as e:
        rprint(f"[red]Failed to get recent pages:[/red] {e}")
        raise typer.Exit(1) from e


@app.command()
def journals(
    raw: Annotated[bool, typer.Option("--raw", "-r", help="Output raw JSON")] = False,
    limit: Annotated[Optional[int], typer.Option("--limit", "-n", help="Limit number of results")] = None,
    asc: Annotated[bool, typer.Option("--asc", "-a", help="Sort ascending (oldest first)")] = False,
) -> None:
    """List all journal pages sorted by date.

    By default, returns newest first. Use --asc for oldest first.

    Example:
        lsq journals              # All journals, newest first
        lsq journals -n 30        # Last 30 days
        lsq journals -r           # Raw JSON output
    """
    config = get_config()
    query_str = """
    [:find ?name ?day
     :where
     [?p :block/journal? true]
     [?p :block/name ?name]
     [?p :block/journal-day ?day]]
    """
    try:
        results = datascript_query(config, query_str)
        # Sort by journal-day (second element)
        sorted_results = sorted(results, key=lambda x: x[1], reverse=not asc)

        if limit:
            sorted_results = sorted_results[:limit]

        if raw:
            # Output as list of date strings
            dates = [r[0] for r in sorted_results]
            print(json.dumps(dates, indent=2))
        else:
            table = Table(title=f"Journal Pages ({len(sorted_results)} total)")
            table.add_column("Date", style="cyan")
            table.add_column("Day", style="dim")

            for name, day in sorted_results:
                table.add_row(name, str(day))

            console.print(table)
    except Exception as e:
        rprint(f"[red]Failed to get journals:[/red] {e}")
        raise typer.Exit(1) from e


def extract_block_text(blocks: list[dict], indent: int = 0) -> list[str]:
    """Recursively extract text content from block tree."""
    lines = []
    for block in blocks:
        content = block.get("content", "").strip()
        if content:
            prefix = "  " * indent
            lines.append(f"{prefix}- {content}")
        children = block.get("children", [])
        if children:
            lines.extend(extract_block_text(children, indent + 1))
    return lines


@app.command()
def blocks(
    page: Annotated[str, typer.Argument(help="Page name")],
    raw: Annotated[bool, typer.Option("--raw", "-r", help="Output raw JSON")] = False,
) -> None:
    """Get all blocks on a page as a tree."""
    config = get_config()
    try:
        tree = get_page_blocks_tree(config, page)
        if raw:
            print(json.dumps(tree, indent=2, default=str))
        else:
            rprint(JSON(json.dumps(tree, default=str)))
    except Exception as e:
        rprint(f"[red]Failed to get blocks:[/red] {e}")
        raise typer.Exit(1) from e


@app.command()
def page_text(
    page: Annotated[str, typer.Argument(help="Page name")],
) -> None:
    """Get page content as plain text (one line per block)."""
    config = get_config()
    try:
        tree = get_page_blocks_tree(config, page)
        if not tree:
            rprint(f"[dim]Page '{page}' is empty or not found[/dim]")
            raise typer.Exit(0)
        lines = extract_block_text(tree)
        for line in lines:
            print(line)
    except Exception as e:
        rprint(f"[red]Failed to get page text:[/red] {e}")
        raise typer.Exit(1) from e


@app.command()
def update(
    uuid: Annotated[str, typer.Argument(help="Block UUID")],
    content: Annotated[Optional[str], typer.Argument(help="New content (or pipe via stdin)")] = None,
) -> None:
    """Update a block's content.

    Content can be provided as an argument or piped via stdin.
    Stdin is preferred for content containing backticks or special characters.

    Examples:
        lsq update <uuid> "simple content"
        echo "content with backticks" | lsq update <uuid>
    """
    if content is None:
        if sys.stdin.isatty():
            rprint("[red]Error:[/red] No content provided. Pass as argument or pipe via stdin.")
            raise typer.Exit(1)
        content = sys.stdin.read().rstrip("\n")

    assert content is not None  # for type checker: stdin path guarantees str
    config = get_config()
    try:
        update_block(config, uuid, content)
        rprint(f"[green]Updated block {uuid}[/green]")
    except Exception as e:
        rprint(f"[red]Failed to update block:[/red] {e}")
        raise typer.Exit(1) from e


@app.command()
def remove(
    uuid: Annotated[str, typer.Argument(help="Block UUID")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Delete a block."""
    config = get_config()

    if not force:
        confirm = typer.confirm(f"Delete block {uuid}?")
        if not confirm:
            rprint("[dim]Cancelled[/dim]")
            raise typer.Exit(0)

    try:
        remove_block(config, uuid)
        rprint(f"[green]Removed block {uuid}[/green]")
    except Exception as e:
        rprint(f"[red]Failed to remove block:[/red] {e}")
        raise typer.Exit(1) from e


@app.command()
def reply(
    uuid: Annotated[str, typer.Argument(help="Parent block UUID to reply under")],
    content: Annotated[Optional[str], typer.Argument(help="Reply content (or pipe via stdin)")] = None,
    sibling: Annotated[bool, typer.Option("--sibling", "-s", help="Insert as sibling instead of child")] = False,
) -> None:
    """Reply to a block (insert as child or sibling).

    Content can be provided as an argument or piped via stdin.
    Stdin is preferred for content containing backticks or special characters.

    Examples:
        lsq reply <uuid> "simple content"
        echo "content with backticks" | lsq reply <uuid>
        cat file.md | lsq reply <uuid>
    """
    if content is None:
        if sys.stdin.isatty():
            rprint("[red]Error:[/red] No content provided. Pass as argument or pipe via stdin.")
            raise typer.Exit(1)
        content = sys.stdin.read().rstrip("\n")

    assert content is not None  # for type checker: stdin path guarantees str
    config = get_config()
    try:
        result = insert_block(config, uuid, content, sibling=sibling)
        new_uuid = result.get("uuid", "unknown")
        print(json.dumps({"uuid": new_uuid, "content": content}, indent=2))
    except Exception as e:
        rprint(f"[red]Failed to reply:[/red] {e}")
        raise typer.Exit(1) from e


@app.command()
def await_change(
    since: Annotated[
        Optional[int],
        typer.Option("--since", "-s", help="Timestamp (ms) to check from; defaults to now"),
    ] = None,
    timeout: Annotated[int, typer.Option("--timeout", "-t", help="Max seconds to wait (0=forever)")] = 300,
    interval: Annotated[int, typer.Option("--interval", "-i", help="Poll interval in seconds")] = 2,
) -> None:
    """Block until a change occurs in Logseq, then output the changes.

    Returns JSON with 'timestamp' (for next call's --since) and 'pages' array.
    Exit code 0 on changes, 2 on timeout.

    Example workflow:
        # First call - wait for changes from now
        result=$(lsq await-change)

        # Subsequent calls - use returned timestamp to avoid gaps
        next_since=$(echo "$result" | jq -r '.timestamp')
        result=$(lsq await-change --since "$next_since")
    """
    config = get_config()

    # Default to current time if no since provided
    check_from = since if since is not None else int(time.time() * 1000)
    start_time = time.time()

    try:
        while True:
            pages = get_changed_pages(config, check_from)

            if pages:
                # Found changes - output and exit
                now = int(time.time() * 1000)
                output = {
                    "timestamp": now,
                    "since": check_from,
                    "pages": pages,
                }
                print(json.dumps(output, indent=2, default=str))
                raise typer.Exit(0)

            # Check timeout
            if timeout > 0 and (time.time() - start_time) >= timeout:
                now = int(time.time() * 1000)
                output = {
                    "timestamp": now,
                    "since": check_from,
                    "pages": [],
                    "timeout": True,
                }
                print(json.dumps(output, indent=2, default=str))
                raise typer.Exit(2)

            time.sleep(interval)

    except KeyboardInterrupt:
        now = int(time.time() * 1000)
        output = {
            "timestamp": now,
            "since": check_from,
            "pages": [],
            "interrupted": True,
        }
        print(json.dumps(output, indent=2, default=str))
        raise typer.Exit(1)


@app.command()
def watch(
    interval: Annotated[int, typer.Option("--interval", "-i", help="Poll interval in seconds")] = 10,
) -> None:
    """Watch for changes in Logseq (polls periodically).

    Press Ctrl+C to stop.
    """
    config = get_config()
    last_check = int(time.time() * 1000)

    rprint(f"[dim]Watching for changes (polling every {interval}s)...[/dim]")
    rprint("[dim]Press Ctrl+C to stop[/dim]\n")

    try:
        while True:
            time.sleep(interval)
            now = int(time.time() * 1000)

            pages = get_changed_pages(config, last_check)

            if pages:
                for page in pages:
                    name = page.get("original-name") or page.get("name", "")
                    rprint(f"[cyan]Changed:[/cyan] {name}")

            last_check = now
    except KeyboardInterrupt:
        rprint("\n[dim]Stopped watching[/dim]")


@app.command()
def find_blocks(
    page: Annotated[str, typer.Argument(help="Page name to search")],
    marker: Annotated[
        Optional[str], typer.Option("--marker", "-m", help="Filter by marker (DONE, LATER, TODO)")
    ] = None,
    pattern: Annotated[Optional[str], typer.Option("--pattern", "-p", help="Regex pattern to match content")] = None,
    section: Annotated[Optional[str], typer.Option("--section", "-s", help="Section heading to search under")] = None,
    raw: Annotated[bool, typer.Option("--raw", "-r", help="Output raw JSON")] = False,
) -> None:
    """Find blocks matching criteria on a page.

    Examples:
        lsq find-blocks "My Page" --marker DONE
        lsq find-blocks "My Page" --section "### PROD" --marker DONE
        lsq find-blocks "My Page" --pattern "deployment.*ID"
    """
    import re

    config = get_config()

    try:
        # Find section UUID if specified
        parent_uuid = None
        if section:
            parent_uuid = find_section_uuid(config, page, section)
            if not parent_uuid:
                rprint(f"[red]Section '{section}' not found on page '{page}'[/red]")
                raise typer.Exit(1)

        # Get blocks to search
        if parent_uuid:
            blocks_list = get_descendants(config, parent_uuid)
        else:
            # Get all blocks on page via query
            query_str = f"""[:find ?uuid ?content ?marker
             :where
             [?p :block/name "{page.lower()}"]
             [?b :block/page ?p]
             [?b :block/uuid ?uuid]
             [?b :block/content ?content]
             [(get-else $ ?b :block/marker "") ?marker]]"""
            results = datascript_query(config, query_str)
            blocks_list = [{"uuid": str(r[0]), "content": r[1], "marker": r[2]} for r in results]

        # Filter by marker
        if marker:
            blocks_list = [b for b in blocks_list if b.get("marker") == marker]

        # Filter by pattern
        if pattern:
            try:
                regex = re.compile(pattern, re.IGNORECASE)
                blocks_list = [b for b in blocks_list if regex.search(b.get("content", ""))]
            except re.error as e:
                rprint(f"[red]Invalid regex pattern:[/red] {e}")
                raise typer.Exit(1) from e

        if raw:
            print(json.dumps(blocks_list, indent=2, default=str))
        elif not blocks_list:
            rprint("[dim]No matching blocks found[/dim]")
        else:
            table = Table(title=f"Found {len(blocks_list)} blocks")
            table.add_column("UUID", style="dim", max_width=12)
            table.add_column("Marker", style="cyan", max_width=8)
            table.add_column("Content", max_width=60)

            for block in blocks_list:
                block_uuid = block.get("uuid", "")[:12]
                block_marker = block.get("marker", "")
                block_content = block.get("content", "").replace("\n", " ")[:60]
                table.add_row(block_uuid, block_marker, block_content)

            console.print(table)

    except Exception as e:
        rprint(f"[red]Failed to find blocks:[/red] {e}")
        raise typer.Exit(1) from e


@app.command()
def bulk_update(
    page: Annotated[str, typer.Argument(help="Page name")],
    marker: Annotated[Optional[str], typer.Option("--marker", "-m", help="Filter by marker")] = None,
    section: Annotated[Optional[str], typer.Option("--section", "-s", help="Section heading to update under")] = None,
    set_marker: Annotated[Optional[str], typer.Option("--set-marker", help="Change marker to this value")] = None,
    replace: Annotated[Optional[str], typer.Option("--replace", help="Regex pattern to replace")] = None,
    with_: Annotated[Optional[str], typer.Option("--with", help="Replacement string")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", "-n", help="Preview changes without applying")] = False,
) -> None:
    """Bulk update blocks matching criteria.

    Examples:
        # Change all DONE to LATER under PROD section
        lsq bulk-update "My Page" --section "### PROD" --marker DONE --set-marker LATER

        # Strip deployment IDs from blocks
        lsq bulk-update "My Page" --section "### Deployments" --replace "\\s*\\(\\d+\\)\\s*$" --with ""

        # Preview changes first
        lsq bulk-update "My Page" --marker DONE --set-marker LATER --dry-run
    """
    import re

    config = get_config()

    # Validate options
    if set_marker is None and replace is None:
        rprint("[red]Must specify --set-marker or --replace[/red]")
        raise typer.Exit(1)

    if replace is not None and with_ is None:
        rprint("[red]--replace requires --with[/red]")
        raise typer.Exit(1)

    try:
        # Find section UUID if specified
        parent_uuid = None
        if section:
            parent_uuid = find_section_uuid(config, page, section)
            if not parent_uuid:
                rprint(f"[red]Section '{section}' not found on page '{page}'[/red]")
                raise typer.Exit(1)

        # Get blocks to update
        if parent_uuid:
            blocks_list = get_descendants(config, parent_uuid)
        else:
            query_str = f"""[:find ?uuid ?content ?marker
             :where
             [?p :block/name "{page.lower()}"]
             [?b :block/page ?p]
             [?b :block/uuid ?uuid]
             [?b :block/content ?content]
             [(get-else $ ?b :block/marker "") ?marker]]"""
            results = datascript_query(config, query_str)
            blocks_list = [{"uuid": str(r[0]), "content": r[1], "marker": r[2]} for r in results]

        # Filter by marker
        if marker:
            blocks_list = [b for b in blocks_list if b.get("marker") == marker]

        if not blocks_list:
            rprint("[dim]No matching blocks found[/dim]")
            raise typer.Exit(0)

        # Compile regex if needed
        replace_regex = None
        if replace:
            try:
                replace_regex = re.compile(replace)
            except re.error as e:
                rprint(f"[red]Invalid regex pattern:[/red] {e}")
                raise typer.Exit(1) from e

        # Compute changes
        changes = []
        for block in blocks_list:
            block_uuid = block.get("uuid", "")
            old_content = block.get("content", "")
            new_content = old_content

            # Apply marker change
            if set_marker and block.get("marker"):
                # Replace the marker at the start of content
                old_marker = str(block.get("marker", ""))
                new_content = re.sub(f"^{re.escape(old_marker)}\\b", set_marker, new_content)

            # Apply regex replacement
            if replace_regex and with_ is not None:
                new_content = replace_regex.sub(with_, new_content)

            if new_content != old_content:
                changes.append(
                    {
                        "uuid": block_uuid,
                        "old": old_content,
                        "new": new_content,
                    }
                )

        if not changes:
            rprint("[dim]No changes to apply[/dim]")
            raise typer.Exit(0)

        # Show changes
        rprint(f"\n[bold]{'Would update' if dry_run else 'Updating'} {len(changes)} blocks:[/bold]\n")
        for change in changes:
            old_preview = change["old"].replace("\n", " ")[:50]
            new_preview = change["new"].replace("\n", " ")[:50]
            rprint(f"  {change['uuid'][:8]}...")
            rprint(f"    [red]- {old_preview}[/red]")
            rprint(f"    [green]+ {new_preview}[/green]")

        if dry_run:
            rprint("\n[yellow]Dry run - no changes applied[/yellow]")
            raise typer.Exit(0)

        # Apply changes
        success = 0
        for change in changes:
            try:
                update_block(config, change["uuid"], change["new"])
                success += 1
            except Exception as e:
                rprint(f"[red]Failed to update {change['uuid'][:8]}:[/red] {e}")

        rprint(f"\n[green]Updated {success}/{len(changes)} blocks[/green]")

    except typer.Exit:
        raise
    except Exception as e:
        rprint(f"[red]Failed to bulk update:[/red] {e}")
        raise typer.Exit(1) from e


@app.command()
def section_uuid(
    page: Annotated[str, typer.Argument(help="Page name")],
    heading: Annotated[str, typer.Argument(help="Section heading to find (e.g., '### PROD')")],
) -> None:
    """Find the UUID of a section heading on a page.

    Example:
        lsq section-uuid "My Page" "### PROD"
    """
    config = get_config()

    try:
        uuid = find_section_uuid(config, page, heading)
        if uuid:
            print(uuid)
        else:
            rprint(f"[red]Section '{heading}' not found on page '{page}'[/red]")
            raise typer.Exit(1)
    except Exception as e:
        rprint(f"[red]Failed to find section:[/red] {e}")
        raise typer.Exit(1) from e


def main() -> None:
    """Entry point."""
    app()


if __name__ == "__main__":
    main()
