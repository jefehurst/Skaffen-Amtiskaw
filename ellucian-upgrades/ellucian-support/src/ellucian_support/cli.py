"""CLI for Ellucian Support Center."""

import os
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .auth import AuthSession, OktaAuthenticator
from .client import EllucianClient, EllucianCredentials
from .download import DownloadCenterError, FlexNetClient
from .fetch import FetchError, fetch_attachments, fetch_kb_article
from .release import (
    ReleaseError,
    enrich_release,
    get_release,
    get_release_with_details,
    search_releases,
)
from .search import SearchError, search
from .ticket import TicketError, add_comment, get_comments, get_ticket, list_tickets

app = typer.Typer(help="Ellucian Support Center CLI")
console = Console()


def load_env():
    """Load environment from local.env if present."""
    # Try project root first, then parent directories
    for parent in [Path.cwd()] + list(Path.cwd().parents)[:3]:
        env_file = parent / "local.env"
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        value = value.strip().strip('"').strip("'")
                        os.environ.setdefault(key.strip(), value)
            break


@app.command()
def login(force: bool = typer.Option(False, "--force", "-f", help="Force re-authentication")):
    """Authenticate with Ellucian Support Center."""
    load_env()

    try:
        creds = EllucianCredentials.from_env()
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    console.print(f"Logging in as: [cyan]{creds.username}[/cyan]")

    def mfa_prompt() -> str:
        return typer.prompt("Enter MFA code")

    with EllucianClient(credentials=creds, mfa_callback=mfa_prompt) as client:
        try:
            client.authenticate(force=force)
            console.print("[green]✓ Authentication successful![/green]")
            console.print(f"Session saved to: {AuthSession.load() and 'yes' or 'no'}")
        except Exception as e:
            console.print(f"[red]✗ Authentication failed:[/red] {e}")
            raise typer.Exit(1)


@app.command()
def status():
    """Check current authentication status."""
    session = AuthSession.load()
    if session is None:
        console.print("[yellow]No saved session found[/yellow]")
        raise typer.Exit(0)

    console.print("Checking session validity...")
    if OktaAuthenticator.validate_session(session):
        console.print("[green]✓ Session is valid[/green]")
    else:
        console.print("[yellow]Session expired - run 'login' to re-authenticate[/yellow]")


@app.command()
def logout():
    """Clear saved session."""
    AuthSession.clear()
    console.print("[green]Session cleared[/green]")


SOURCE_HELP = """Filter by source:
docs=documentation, kb=knowledge base, defect=bugs,
release=releases, idea=feature requests, community=forums"""

FILETYPE_HELP = """Filter by type:
html=web pages, pdf=attachments, kb=knowledge base articles"""


@app.command()
def find(
    query: str = typer.Argument(..., help="Search query"),
    num: int = typer.Option(10, "--num", "-n", help="Number of results"),
    source: list[str] = typer.Option([], "--source", "-s", help=SOURCE_HELP),
    filetype: list[str] = typer.Option([], "--type", "-t", help=FILETYPE_HELP),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """Search the Ellucian Support Center.

    Examples:

        ellucian-support find "banner upgrade"

        ellucian-support find "installation" --source docs

        ellucian-support find "error" -s kb -s defect

        ellucian-support find "guide" --type pdf
    """
    session = AuthSession.load()
    if session is None:
        console.print("[yellow]No session found. Run 'login' first.[/yellow]")
        raise typer.Exit(1)

    if not OktaAuthenticator.validate_session(session):
        console.print("[yellow]Session expired. Run 'login' to re-authenticate.[/yellow]")
        raise typer.Exit(1)

    # Convert filter lists (empty list means no filter)
    source_filter = source if source else None
    filetype_filter = filetype if filetype else None

    try:
        results = search(
            session,
            query,
            num_results=num,
            source_filter=source_filter,
            filetype_filter=filetype_filter,
        )
    except SearchError as e:
        console.print(f"[red]Search failed:[/red] {e}")
        raise typer.Exit(1)

    if json_output:
        import json

        output = {
            "query": results.query,
            "total_count": results.total_count,
            "duration_ms": results.duration_ms,
            "results": [
                {
                    "title": r.title,
                    "url": r.url,
                    "excerpt": r.excerpt,
                    "source": r.source,
                }
                for r in results.results
            ],
        }
        console.print(json.dumps(output, indent=2))
    else:
        console.print(f"\n[bold]Results for:[/bold] {query}")
        console.print(f"[dim]Found {results.total_count} total ({results.duration_ms}ms)[/dim]\n")

        table = Table(show_header=True, header_style="bold")
        table.add_column("#", style="dim", width=3)
        table.add_column("Title", width=50)
        table.add_column("Type", width=8)

        for i, r in enumerate(results.results, 1):
            # Truncate title if too long
            title = r.title[:47] + "..." if len(r.title) > 50 else r.title
            table.add_row(str(i), title, r.source)

        console.print(table)

        # Show URLs below table
        console.print()
        for i, r in enumerate(results.results, 1):
            console.print(f"[dim]{i}.[/dim] {r.url}")


@app.command()
def fetch(
    url: str = typer.Argument(..., help="Article URL or sys_id"),
    attachments: bool = typer.Option(False, "--attachments", "-a", help="List attachments"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """Fetch full content of an Ellucian article.

    Examples:

        ellucian-support fetch "https://elluciansupport.service-now.com/nav_to.do?uri=kb_knowledge.do?sys_id=abc123"

        ellucian-support fetch abc123def456...

        ellucian-support fetch abc123... --attachments
    """
    session = AuthSession.load()
    if session is None:
        console.print("[yellow]No session found. Run 'login' first.[/yellow]")
        raise typer.Exit(1)

    if not OktaAuthenticator.validate_session(session):
        console.print("[yellow]Session expired. Run 'login' to re-authenticate.[/yellow]")
        raise typer.Exit(1)

    try:
        article = fetch_kb_article(session, url)
    except FetchError as e:
        console.print(f"[red]Fetch failed:[/red] {e}")
        raise typer.Exit(1)

    if json_output:
        import json

        output = {
            "sys_id": article.sys_id,
            "number": article.number,
            "title": article.title,
            "published": article.published,
            "category": article.category,
            "text": article.text,
        }
        if attachments:
            att_list = fetch_attachments(session, article.sys_id)
            output["attachments"] = [
                {
                    "file_name": a.get("file_name"),
                    "size_bytes": a.get("size_bytes"),
                    "content_type": a.get("content_type"),
                    "sys_id": a.get("sys_id"),
                }
                for a in att_list
            ]
        console.print(json.dumps(output, indent=2))
    else:
        console.print(f"\n[bold]{article.title}[/bold]")
        console.print(f"[dim]Ellucian Article {article.number} | Published: {article.published}[/dim]\n")
        # Escape Rich markup characters in article text to prevent parsing errors
        console.print(article.text, markup=False)

        if attachments:
            att_list = fetch_attachments(session, article.sys_id)
            if att_list:
                console.print(f"\n[bold]Attachments ({len(att_list)}):[/bold]")
                for a in att_list:
                    size = int(a.get("size_bytes", 0))
                    size_str = f"{size / 1024:.1f} KB" if size > 1024 else f"{size} B"
                    console.print(f"  - {a.get('file_name')} ({size_str})")
            else:
                console.print("\n[dim]No attachments[/dim]")


@app.command()
def ticket(
    number: str = typer.Argument(..., help="Case number"),
    comments: bool = typer.Option(False, "--comments", "-c", help="Show comments"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """Get a support ticket by case number.

    Examples:

        ellucian-support ticket CSC03683039

        ellucian-support ticket CSC03683039 --comments
    """
    session = AuthSession.load()
    if session is None:
        console.print("[yellow]No session found. Run 'login' first.[/yellow]")
        raise typer.Exit(1)

    if not OktaAuthenticator.validate_session(session):
        console.print("[yellow]Session expired. Run 'login' to re-authenticate.[/yellow]")
        raise typer.Exit(1)

    try:
        t = get_ticket(session, number)
    except TicketError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if json_output:
        import json

        output = {
            "number": t.number,
            "short_description": t.short_description,
            "description": t.description,
            "state": t.state,
            "priority": t.priority,
            "created_on": t.created_on,
            "updated_on": t.updated_on,
            "contact": t.contact,
        }
        if comments:
            comment_list = get_comments(session, t.sys_id)
            output["comments"] = [
                {
                    "value": c.value,
                    "created_on": c.created_on,
                    "created_by": c.created_by,
                    "type": c.element,
                }
                for c in comment_list
            ]
        console.print(json.dumps(output, indent=2))
    else:
        console.print(f"\n[bold]{t.number}[/bold]: {t.short_description}")
        console.print(f"[dim]State: {t.state} | Priority: {t.priority}[/dim]")
        console.print(f"[dim]Created: {t.created_on} | Updated: {t.updated_on}[/dim]")
        if t.contact:
            console.print(f"[dim]Contact: {t.contact}[/dim]")
        if t.description:
            console.print(f"\n{t.description[:500]}")

        if comments:
            comment_list = get_comments(session, t.sys_id)
            if comment_list:
                console.print(f"\n[bold]Comments ({len(comment_list)}):[/bold]")
                for c in comment_list:
                    console.print(f"\n[dim]{c.created_on} - {c.created_by}[/dim]")
                    console.print(c.value[:300])
            else:
                console.print("\n[dim]No comments[/dim]")


@app.command()
def tickets(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of tickets"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """List recent support tickets.

    Examples:

        ellucian-support tickets

        ellucian-support tickets -n 20
    """
    session = AuthSession.load()
    if session is None:
        console.print("[yellow]No session found. Run 'login' first.[/yellow]")
        raise typer.Exit(1)

    if not OktaAuthenticator.validate_session(session):
        console.print("[yellow]Session expired. Run 'login' to re-authenticate.[/yellow]")
        raise typer.Exit(1)

    try:
        ticket_list = list_tickets(session, limit=limit)
    except TicketError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if json_output:
        import json

        output = [
            {
                "number": t.number,
                "short_description": t.short_description,
                "state": t.state,
                "updated_on": t.updated_on,
            }
            for t in ticket_list
        ]
        console.print(json.dumps(output, indent=2))
    else:
        console.print(f"\n[bold]Recent Tickets ({len(ticket_list)})[/bold]\n")

        table = Table(show_header=True, header_style="bold")
        table.add_column("Number", width=14)
        table.add_column("Description", width=45)
        table.add_column("State", width=10)

        for t in ticket_list:
            desc = t.short_description[:42] + "..." if len(t.short_description) > 45 else t.short_description
            table.add_row(t.number, desc, t.state)

        console.print(table)


@app.command()
def comment(
    number: str = typer.Argument(..., help="Case number"),
    message: str = typer.Argument(..., help="Comment text"),
):
    """Add a comment to a support ticket.

    Examples:

        ellucian-support comment CSC03683039 "Following up on this issue"
    """
    session = AuthSession.load()
    if session is None:
        console.print("[yellow]No session found. Run 'login' first.[/yellow]")
        raise typer.Exit(1)

    if not OktaAuthenticator.validate_session(session):
        console.print("[yellow]Session expired. Run 'login' to re-authenticate.[/yellow]")
        raise typer.Exit(1)

    # First get the ticket to get its sys_id
    try:
        t = get_ticket(session, number)
    except TicketError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    try:
        add_comment(session, t.sys_id, message)
        console.print(f"[green]✓ Comment added to {number}[/green]")
    except TicketError as e:
        console.print(f"[red]Failed to add comment:[/red] {e}")
        raise typer.Exit(1)


# Download Center commands
download_app = typer.Typer(help="Download Center (FlexNet) commands")
app.add_typer(download_app, name="download")


def _require_session() -> AuthSession:
    """Get valid session or exit."""
    session = AuthSession.load()
    if session is None:
        console.print("[yellow]No session found. Run 'login' first.[/yellow]")
        raise typer.Exit(1)

    if not OktaAuthenticator.validate_session(session):
        console.print("[yellow]Session expired. Run 'login' to re-authenticate.[/yellow]")
        raise typer.Exit(1)

    return session


@download_app.command("products")
def download_products(
    query: str = typer.Option("", "--query", "-q", help="Filter products by name"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """List available products in the Download Center.

    Examples:

        ellucian-support download products

        ellucian-support download products -q ethos

        ellucian-support download products -q identity --json
    """
    session = _require_session()

    try:
        with FlexNetClient(session, progress_callback=lambda m: console.print(f"[dim]{m}[/dim]")) as client:
            if query:
                products = client.search_products(query)
            else:
                products = client.list_products()
    except DownloadCenterError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if json_output:
        import json

        output = [{"line_id": lid, "name": name} for lid, name in products]
        console.print(json.dumps(output, indent=2))
    else:
        if query:
            console.print(f"\n[bold]Products matching '{query}' ({len(products)})[/bold]\n")
        else:
            console.print(f"\n[bold]Available Products ({len(products)})[/bold]\n")

        table = Table(show_header=True, header_style="bold")
        table.add_column("#", style="dim", width=4)
        table.add_column("Product", width=60)
        table.add_column("Line ID", width=40)

        for i, (line_id, name) in enumerate(products, 1):
            table.add_row(str(i), name, line_id)

        console.print(table)


@download_app.command("files")
def download_files(
    product: str = typer.Argument(..., help="Product line ID or package ID"),
    pattern: str = typer.Option("", "--pattern", "-p", help="Filter files by pattern"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """List downloadable files for a product.

    Examples:

        ellucian-support download files "Ellucian-Ethos-Identity"

        ellucian-support download files "Ellucian - Ellucian Ethos Identity" -p "5.10"

        ellucian-support download files "Ellucian-Ethos-Identity" --json
    """
    session = _require_session()

    try:
        with FlexNetClient(session, progress_callback=lambda m: console.print(f"[dim]{m}[/dim]")) as client:
            files = client.get_files_for_product(product)

            # Filter by pattern if specified
            if pattern:
                pattern_lower = pattern.lower()
                files = [f for f in files if pattern_lower in f.name.lower()]

    except DownloadCenterError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if json_output:
        import json

        output = [
            {
                "name": f.name,
                "size": f.size,
                "url": f.download_url,
            }
            for f in files
        ]
        console.print(json.dumps(output, indent=2))
    else:
        console.print(f"\n[bold]Files for {product}[/bold]")
        if pattern:
            console.print(f"[dim]Filtered by: {pattern}[/dim]")
        console.print(f"[dim]Found {len(files)} files[/dim]\n")

        table = Table(show_header=True, header_style="bold")
        table.add_column("#", style="dim", width=4)
        table.add_column("File Name", width=55)
        table.add_column("Size", width=12)

        for i, f in enumerate(files, 1):
            table.add_row(str(i), f.name, f.size)

        console.print(table)


@download_app.command("get")
def download_get(
    product: str = typer.Argument(..., help="Product line ID or package ID"),
    pattern: str = typer.Option("", "--pattern", "-p", help="Download files matching pattern"),
    output_dir: Path = typer.Option(Path("."), "--output", "-o", help="Output directory"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be downloaded"),
):
    """Download files from the Download Center.

    Examples:

        ellucian-support download get "Ellucian-Ethos-Identity" -p "5.10" -o ./downloads

        ellucian-support download get "Ellucian-Ethos-Identity" -p "baseline-5.10.0" -n

        ellucian-support download get "Ellucian - Ellucian Ethos Identity" -p ".zip"
    """
    session = _require_session()

    try:
        with FlexNetClient(session, progress_callback=lambda m: console.print(f"[dim]{m}[/dim]")) as client:
            files = client.get_files_for_product(product)

            # Filter by pattern
            if pattern:
                pattern_lower = pattern.lower()
                files = [f for f in files if pattern_lower in f.name.lower()]

            if not files:
                console.print("[yellow]No files match the pattern[/yellow]")
                raise typer.Exit(0)

            console.print(f"\n[bold]Files to download ({len(files)}):[/bold]")
            for f in files:
                console.print(f"  - {f.name} ({f.size})")

            if dry_run:
                console.print("\n[yellow]Dry run - no files downloaded[/yellow]")
                return

            console.print(f"\nDownloading to: {output_dir.absolute()}")

            from rich.progress import BarColumn, DownloadColumn, Progress, SpinnerColumn, TextColumn

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                DownloadColumn(),
                console=console,
            ) as progress:
                for f in files:
                    task = progress.add_task(f.name[:40], total=None)

                    def update_progress(downloaded: int, total: int):
                        if total > 0:
                            progress.update(task, total=total, completed=downloaded)

                    client.download_file(f, output_dir, progress_callback=update_progress)
                    progress.update(task, description=f"[green]✓[/green] {f.name[:40]}")

            console.print(f"\n[green]✓ Downloaded {len(files)} files to {output_dir}[/green]")

    except DownloadCenterError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


# Release commands
releases_app = typer.Typer(help="Product release commands")
app.add_typer(releases_app, name="releases")


@releases_app.command("search")
def releases_search(
    query: str = typer.Argument("", help="Search query (e.g., 'Banner Financial Aid')"),
    num: int = typer.Option(20, "--num", "-n", help="Number of results"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """Search for product releases.

    Examples:

        ellucian-support releases search "Banner Financial Aid"

        ellucian-support releases search "Banner" -n 50

        ellucian-support releases search --json
    """
    session = _require_session()

    try:
        releases = search_releases(session, query, num_results=num)
    except ReleaseError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if json_output:
        import json

        output = [r.to_dict() for r in releases]
        console.print(json.dumps(output, indent=2))
    else:
        console.print(f"\n[bold]Releases[/bold]")
        if query:
            console.print(f"[dim]Query: {query}[/dim]")
        console.print(f"[dim]Found {len(releases)} results[/dim]\n")

        table = Table(show_header=True, header_style="bold")
        table.add_column("#", style="dim", width=3)
        table.add_column("Number", width=12)
        table.add_column("Description", width=40)
        table.add_column("Date", width=12)

        for i, r in enumerate(releases, 1):
            desc = r.short_description[:37] + "..." if len(r.short_description) > 40 else r.short_description
            table.add_row(str(i), r.number, desc, r.date_released[:10] if r.date_released else "")

        console.print(table)

        # Show sys_ids for reference
        console.print("\n[dim]sys_ids for 'releases show':[/dim]")
        for i, r in enumerate(releases, 1):
            console.print(f"[dim]{i}. {r.sys_id}[/dim]")


@releases_app.command("show")
def releases_show(
    sys_id: str = typer.Argument(..., help="Release sys_id"),
    with_defects: bool = typer.Option(False, "--defects", "-d", help="Include related defects"),
    with_enhancements: bool = typer.Option(False, "--enhancements", "-e", help="Include related enhancements"),
    full: bool = typer.Option(False, "--full", "-f", help="Include both defects and enhancements"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """Show release details with optional defects/enhancements.

    Examples:

        ellucian-support releases show 45cce3d283b20298c2649550ceaad3d8

        ellucian-support releases show 45cce3d2... --defects

        ellucian-support releases show 45cce3d2... --full --json
    """
    session = _require_session()

    try:
        if full or with_defects or with_enhancements:
            release = get_release_with_details(session, sys_id)
            # Filter if only one type requested
            if not full:
                if not with_defects:
                    release.defects = []
                if not with_enhancements:
                    release.enhancements = []
        else:
            release = get_release(session, sys_id)
    except ReleaseError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if json_output:
        import json

        console.print(json.dumps(release.to_dict(), indent=2))
    else:
        console.print(f"\n[bold]{release.short_description}[/bold]")
        console.print(f"[dim]Number: {release.number} | Released: {release.date_released}[/dim]")
        if release.product_line:
            console.print(f"[dim]Product: {release.product_line}[/dim]")
        if release.url:
            console.print(f"[dim]URL: {release.url}[/dim]")

        if release.defects:
            console.print(f"\n[bold]Related Defects ({len(release.defects)})[/bold]")
            table = Table(show_header=True, header_style="bold")
            table.add_column("Number", width=12)
            table.add_column("Summary", width=60)

            for d in release.defects:
                summary = d.summary[:57] + "..." if len(d.summary) > 60 else d.summary
                table.add_row(d.number, summary)

            console.print(table)

        if release.enhancements:
            console.print(f"\n[bold]Related Enhancements ({len(release.enhancements)})[/bold]")
            table = Table(show_header=True, header_style="bold")
            table.add_column("Number", width=12)
            table.add_column("Summary", width=60)

            for e in release.enhancements:
                summary = e.summary[:57] + "..." if len(e.summary) > 60 else e.summary
                table.add_row(e.number, summary)

            console.print(table)

        if not release.defects and not release.enhancements and (full or with_defects or with_enhancements):
            console.print("\n[dim]No related defects or enhancements found[/dim]")


@releases_app.command("export")
def releases_export(
    query: str = typer.Argument("", help="Search query"),
    num: int = typer.Option(20, "--num", "-n", help="Number of releases"),
    enrich: bool = typer.Option(False, "--enrich", "-e", help="Include defects/enhancements (slower)"),
    output: Path = typer.Option(None, "--output", "-o", help="Output file (default: stdout)"),
):
    """Export releases to JSON for further processing.

    Examples:

        ellucian-support releases export "Banner" -n 50 -o releases.json

        ellucian-support releases export "Financial Aid" --enrich -o enriched.json
    """
    session = _require_session()

    try:
        releases = search_releases(session, query, num_results=num)

        if enrich:
            console.print(f"[dim]Enriching {len(releases)} releases with defects/enhancements...[/dim]")
            for i, r in enumerate(releases, 1):
                console.print(f"[dim]  ({i}/{len(releases)}) {r.number}...[/dim]")
                enrich_release(session, r)

    except ReleaseError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    import json

    data = {
        "query": query,
        "count": len(releases),
        "releases": [r.to_dict() for r in releases],
    }

    json_str = json.dumps(data, indent=2)

    if output:
        output.write_text(json_str)
        console.print(f"[green]Exported {len(releases)} releases to {output}[/green]")
    else:
        console.print(json_str)


def main():
    """Entry point."""
    app()


if __name__ == "__main__":
    main()
