"""CLI for Ellucian Support Center."""

import os
from pathlib import Path

import httpx
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


# Upgrade documentation commands
upgrades_app = typer.Typer(help="Upgrade documentation commands")
app.add_typer(upgrades_app, name="upgrades")


@upgrades_app.command("gather")
def upgrades_gather(
    title: str = typer.Argument(..., help="Upgrade round title (e.g., 'Spring 2026')"),
    cutoff: str = typer.Option(..., "--cutoff", "-c", help="Cutoff date (YYYY-MM-DD)"),
    since: str = typer.Option("", "--since", "-s", help="Since date for recent releases"),
    enrich: bool = typer.Option(True, help="Fetch defects/enhancements/prerequisites"),
    output: Path = typer.Option(None, "--output", "-o", help="Output file (default: stdout)"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="JSON output"),
):
    """Gather release data for an upgrade round.

    Queries the ServiceNow Table API for upcoming and recent Banner releases,
    filters out excluded patterns, groups by module, and optionally enriches
    with defects/enhancements/prerequisites.

    Examples:

        ellucian-support upgrades gather "Spring 2026" --cutoff 2026-03-19 --since 2025-12-12

        ellucian-support upgrades gather "Spring 2026" -c 2026-03-19 -s 2025-12-12 --no-enrich -o spring2026.json
    """
    from .upgrade import gather_upgrade_round

    session = _require_session()

    try:
        round_ = gather_upgrade_round(
            session,
            title=title,
            cutoff_date=cutoff,
            since_date=since,
            enrich=enrich,
            progress_callback=lambda msg: console.print(f"[dim]{msg}[/dim]"),
        )
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    json_str = round_.to_json()

    if output:
        output.write_text(json_str)
        console.print(
            f"[green]Gathered {sum(len(m.releases) for m in round_.modules)} releases "
            f"in {len(round_.modules)} modules → {output}[/green]"
        )
    else:
        console.print(json_str)


@upgrades_app.command("preview")
def upgrades_preview(
    input_file: Path = typer.Argument(..., help="JSON file from 'upgrades gather'"),
):
    """Preview what would be published (module list, page count, etc.).

    Examples:

        ellucian-support upgrades preview spring2026.json
    """
    from .upgrade import UpgradeRound

    try:
        data = input_file.read_text()
        round_ = UpgradeRound.from_json(data)
    except Exception as e:
        console.print(f"[red]Error reading {input_file}:[/red] {e}")
        raise typer.Exit(1)

    console.print(f"\n[bold]{round_.title}[/bold]")
    console.print(f"[dim]Cutoff: {round_.cutoff_date} | Since: {round_.since_date or 'N/A'}[/dim]")
    console.print(f"[dim]Modules: {len(round_.modules)} | Total releases: {sum(len(m.releases) for m in round_.modules)}[/dim]\n")

    table = Table(show_header=True, header_style="bold")
    table.add_column("#", style="dim", width=3)
    table.add_column("Module", width=30)
    table.add_column("Versions", width=25)
    table.add_column("Releases", width=4)
    table.add_column("Defects", width=4)
    table.add_column("Enhancements", width=4)
    table.add_column("Prerequisites", width=4)

    from .confluence import _version_from_short_desc

    for i, mod in enumerate(round_.modules, 1):
        versions = "/".join(
            _version_from_short_desc(r.short_description)
            for r in mod.releases
        )
        defects = sum(len(r.defects) for r in mod.releases)
        enhancements = sum(len(r.enhancements) for r in mod.releases)
        prereqs = sum(len(r.prerequisites) for r in mod.releases)
        table.add_row(
            str(i), mod.name, versions,
            str(len(mod.releases)), str(defects), str(enhancements), str(prereqs),
        )

    console.print(table)
    console.print(f"\n[dim]Would create 1 root page + {len(round_.modules)} detail pages[/dim]")


@upgrades_app.command("publish")
def upgrades_publish(
    input_file: Path = typer.Argument(..., help="JSON file from 'upgrades gather'"),
    space_id: str = typer.Option(..., "--space-id", help="Confluence space ID"),
    parent_id: str = typer.Option(..., "--parent-id", help="Parent page/folder ID"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Generate HTML without creating pages"),
):
    """Publish upgrade round to Confluence.

    Creates a root page with Details table and child detail pages per module.

    Examples:

        ellucian-support upgrades publish spring2026.json --space-id 3096510467 --parent-id 3606609928

        ellucian-support upgrades publish spring2026.json --space-id 3096510467 --parent-id 3606609928 --dry-run
    """
    from .confluence import publish_upgrade_round
    from .upgrade import UpgradeRound

    load_env()

    user = os.environ.get("ATLASSIAN_USER", "")
    token = os.environ.get("ATLASSIAN_API_TOKEN", "")
    site = os.environ.get("ATLASSIAN_SITE", "")

    if not all([user, token, site]):
        console.print("[red]Missing ATLASSIAN_USER, ATLASSIAN_API_TOKEN, or ATLASSIAN_SITE in local.env[/red]")
        raise typer.Exit(1)

    try:
        data = input_file.read_text()
        round_ = UpgradeRound.from_json(data)
    except Exception as e:
        console.print(f"[red]Error reading {input_file}:[/red] {e}")
        raise typer.Exit(1)

    console.print(f"[bold]Publishing: {round_.title}[/bold]")
    console.print(f"[dim]Modules: {len(round_.modules)} | Space: {space_id} | Parent: {parent_id}[/dim]")

    if dry_run:
        console.print("[yellow]DRY RUN — no pages will be created[/yellow]")

    try:
        result = publish_upgrade_round(
            round_,
            space_id=space_id,
            parent_id=parent_id,
            user=user,
            token=token,
            site=site,
            dry_run=dry_run,
            progress_callback=lambda msg: console.print(f"[dim]{msg}[/dim]"),
        )
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if dry_run:
        import json as json_mod

        # Write generated HTML to files for inspection
        root = result.get("root_page", {})
        if root.get("html"):
            outfile = input_file.with_suffix(".root.html")
            outfile.write_text(root["html"])
            console.print(f"[green]Root page HTML → {outfile}[/green]")

        for detail in result.get("detail_pages", []):
            safe_name = detail["title"].replace("/", "_").replace(" ", "_")
            outfile = input_file.parent / f"{safe_name}.html"
            outfile.write_text(detail["html"])
            console.print(f"[green]Detail HTML → {outfile}[/green]")
    else:
        root = result.get("root_page", {})
        console.print(f"\n[green]Root page:[/green] {root.get('url', root.get('id', ''))}")
        for detail in result.get("detail_pages", []):
            console.print(f"[green]  {detail['title']}:[/green] {detail.get('url', detail.get('id', ''))}")
        console.print(f"\n[green]Published {round_.title} successfully![/green]")


def _load_client_config(client_key: str, config_path: Path = None) -> dict:
    """Load client configuration from clients.json.

    Searches for clients.json in the current directory and up to 3 parent
    directories, or uses the explicit path if provided.

    Args:
        client_key: Client key (e.g., "FHDA", "IVC").
        config_path: Optional explicit path to clients.json.

    Returns:
        Client config dict with space_id, parent_id, etc.

    Raises:
        typer.Exit: If config file not found or client key missing.
    """
    import json as json_mod

    if config_path is None:
        for parent in [Path.cwd()] + list(Path.cwd().parents)[:3]:
            candidate = parent / "clients.json"
            if candidate.exists():
                config_path = candidate
                break

    if config_path is None or not config_path.exists():
        console.print("[red]clients.json not found. Create one or use --config to specify path.[/red]")
        raise typer.Exit(1)

    try:
        all_clients = json_mod.loads(config_path.read_text())
    except Exception as e:
        console.print(f"[red]Error reading {config_path}:[/red] {e}")
        raise typer.Exit(1)

    # Case-insensitive lookup
    for key, cfg in all_clients.items():
        if key.upper() == client_key.upper():
            console.print(f"[dim]Loaded client config for {key} from {config_path}[/dim]")
            return cfg

    available = ", ".join(all_clients.keys())
    console.print(f"[red]Client '{client_key}' not found in {config_path}. Available: {available}[/red]")
    raise typer.Exit(1)


@upgrades_app.command("client-publish")
def upgrades_client_publish(
    input_file: Path = typer.Argument(..., help="JSON file from 'upgrades gather' (enriched)"),
    client: str = typer.Option(..., "--client", help="Client key (e.g., 'FHDA', 'IVC')"),
    esm_versions: Path = typer.Option(..., "--esm-versions", help="JSON file with ESM installed versions"),
    config: Path = typer.Option(None, "--config", help="Path to clients.json (default: auto-detect)"),
    space_id: str = typer.Option("", "--space-id", help="Override client Confluence space ID"),
    parent_id: str = typer.Option("", "--parent-id", help="Override parent page/folder ID"),
    baseline_page_id: str = typer.Option("", "--baseline-page-id", help="Override baseline root page ID"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Generate HTML without creating pages"),
):
    """Publish a client-specific upgrade page to Confluence.

    Creates a flat page with 6 columns (Module, Current Version, Latest Version,
    Release Date, Defect/Enhancement/Regulatory, Dependencies). Only includes
    modules the client has installed (from ESM versions file).

    Client configuration (space_id, parent_id, baseline_page_id) is loaded
    from clients.json. Override any value with explicit flags.

    The ESM versions file should be a JSON object mapping ESM product names
    to version strings, e.g.: {"Financial Aid": "9.3.56", "General DB": "9.40"}

    Examples:

        ellucian-support upgrades client-publish /tmp/spring2026_enriched.json \\
          --client FHDA --esm-versions /tmp/esm_prod_versions.json

        ellucian-support upgrades client-publish /tmp/spring2026_enriched.json \\
          --client IVC --esm-versions /tmp/ivc_versions.json --dry-run
    """
    import json as json_mod

    from .confluence import create_page as conf_create_page
    from .confluence import render_client_page
    from .upgrade import UpgradeRound, match_installed_versions

    load_env()

    # Load client config from clients.json
    client_cfg = _load_client_config(client, config)
    client_name = client_cfg.get("client_name", client)

    # Use config values, allow CLI flags to override
    space_id = space_id or client_cfg.get("space_id", "")
    parent_id = parent_id or client_cfg.get("parent_id", "")
    baseline_page_id = baseline_page_id or client_cfg.get("baseline_page_id", "")

    if not space_id or not parent_id:
        console.print("[red]Missing space_id or parent_id — set in clients.json or pass --space-id/--parent-id[/red]")
        raise typer.Exit(1)

    user = os.environ.get("ATLASSIAN_USER", "")
    token = os.environ.get("ATLASSIAN_API_TOKEN", "")
    site = os.environ.get("ATLASSIAN_SITE", "")

    if not dry_run and not all([user, token, site]):
        console.print("[red]Missing ATLASSIAN_USER, ATLASSIAN_API_TOKEN, or ATLASSIAN_SITE in local.env[/red]")
        raise typer.Exit(1)

    # Load enriched upgrade round
    try:
        data = input_file.read_text()
        round_ = UpgradeRound.from_json(data)
    except Exception as e:
        console.print(f"[red]Error reading {input_file}:[/red] {e}")
        raise typer.Exit(1)

    # Load ESM versions
    try:
        esm_data = json_mod.loads(esm_versions.read_text())
    except Exception as e:
        console.print(f"[red]Error reading ESM versions {esm_versions}:[/red] {e}")
        raise typer.Exit(1)

    # Match ESM products to modules
    installed = match_installed_versions(esm_data, round_)
    console.print(f"[dim]Matched {len(installed)} of {len(esm_data)} ESM products to upgrade modules[/dim]")

    if not installed:
        console.print("[yellow]No ESM products matched any modules in the upgrade round[/yellow]")
        raise typer.Exit(0)

    # Fetch baseline detail links if baseline page ID provided
    detail_links: dict[str, str] = {}
    if baseline_page_id and not dry_run and all([user, token, site]):
        console.print(f"[dim]Fetching baseline detail page links from {baseline_page_id}...[/dim]")
        try:
            detail_links = _fetch_baseline_detail_links(
                baseline_page_id, user, token, site,
            )
            console.print(f"[dim]Found {len(detail_links)} detail page links[/dim]")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not fetch baseline links: {e}[/yellow]")

    # Render the client page
    title = f"{client_name} {round_.title}"
    body = render_client_page(round_, installed, detail_links, client_name=client_name)

    console.print(f"\n[bold]Publishing: {title}[/bold]")
    console.print(f"[dim]Modules: {len(installed)} | Space: {space_id} | Parent: {parent_id}[/dim]")

    if dry_run:
        console.print("[yellow]DRY RUN — no pages will be created[/yellow]")
        outfile = input_file.with_suffix(f".{client_name.lower()}.html")
        outfile.write_text(body)
        console.print(f"[green]Client page HTML → {outfile}[/green]")

        # Also show which modules matched
        console.print(f"\n[bold]Installed modules ({len(installed)}):[/bold]")
        for mod_name, ver in sorted(installed.items()):
            console.print(f"  {mod_name}: {ver}")
        return

    # Create the page
    try:
        result = conf_create_page(
            title, space_id, parent_id, body,
            user, token, site,
        )
        page_url = result.get("_links", {}).get("tinyui", "")
        if page_url and not page_url.startswith("http"):
            page_url = f"https://{site}/wiki{page_url}"
        console.print(f"\n[green]Created: {title}[/green]")
        console.print(f"[green]URL: {page_url}[/green]")
        console.print(f"[green]ID: {result.get('id', '')}[/green]")
    except Exception as e:
        console.print(f"[red]Error creating page:[/red] {e}")
        raise typer.Exit(1)


def _fetch_baseline_detail_links(
    baseline_page_id: str,
    user: str,
    token: str,
    site: str,
) -> dict[str, str]:
    """Fetch detail page links from the baseline root page's children.

    Paginates through children and fetches each page individually to get
    tinyui links (the children list endpoint doesn't include _links).

    Returns a dict of module_name -> page URL for linking from client pages.
    """
    import base64

    from .upgrade import parse_module_name

    credentials = base64.b64encode(f"{user}:{token}".encode()).decode()
    headers = {
        "Authorization": f"Basic {credentials}",
        "Accept": "application/json",
    }

    # Step 1: Collect all child page IDs and titles (with pagination)
    children = []
    url = f"https://{site}/wiki/api/v2/pages/{baseline_page_id}/children"
    params = {"limit": 100}

    with httpx.Client(timeout=60.0) as client:
        while url:
            resp = client.get(url, headers=headers, params=params)
            if resp.status_code != 200:
                break
            data = resp.json()
            children.extend(data.get("results", []))
            # Follow pagination cursor
            next_link = data.get("_links", {}).get("next", "")
            if next_link:
                url = f"https://{site}/wiki{next_link}" if not next_link.startswith("http") else next_link
                params = {}  # cursor is embedded in the next URL
            else:
                url = None

        # Step 2: Fetch tinyui for each child page
        detail_links = {}
        for child in children:
            page_id = child.get("id", "")
            title = child.get("title", "")
            # Detail page titles may have slash-separated versions (e.g.
            # "BA FIN AID 8.55 - REPOST/9.3.56.1/8.56"). Split on first
            # slash before parsing so the module name extracts cleanly.
            base_title = title.split("/")[0] if "/" in title else title
            module_name = parse_module_name(base_title)
            if not module_name or not page_id:
                continue

            page_url = f"https://{site}/wiki/api/v2/pages/{page_id}"
            resp = client.get(page_url, headers=headers)
            if resp.status_code == 200:
                page_data = resp.json()
                tinyui = page_data.get("_links", {}).get("tinyui", "")
                if tinyui and not tinyui.startswith("http"):
                    base = page_data.get("_links", {}).get("base", f"https://{site}/wiki")
                    tinyui = f"{base}{tinyui}"
                if tinyui:
                    detail_links[module_name] = tinyui

    return detail_links


def main():
    """Entry point."""
    app()


if __name__ == "__main__":
    main()
