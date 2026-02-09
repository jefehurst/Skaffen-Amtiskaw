"""CLI for Runner Technologies Support."""

import os
import re
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .auth import AuthSession, AuthenticationError, authenticate
from .client import RunnerSupportClient


def strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    return re.sub(r"<[^>]+>", "", text)


app = typer.Typer(help="Runner Technologies Support CLI")
console = Console()


def load_env() -> None:
    """Load environment variables from local.env."""
    env_file = Path(__file__).parent.parent.parent.parent.parent / "local.env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    value = value.strip().strip('"').strip("'")
                    os.environ.setdefault(key.strip(), value)


@app.command()
def login() -> None:
    """Login to Runner Technologies Support."""
    load_env()

    username = os.environ.get("RUNNER_SUPPORT_USER")
    password = os.environ.get("RUNNER_SUPPORT_PW")

    if not username or not password:
        console.print("[red]Error:[/red] Set RUNNER_SUPPORT_USER and RUNNER_SUPPORT_PW")
        raise typer.Exit(1)

    console.print(f"Logging in as: {username}")

    try:
        session = authenticate(username, password)
        session.save()
        console.print("[green]Login successful![/green]")
        console.print(f"  Session saved for: {session.user_email}")
    except AuthenticationError as e:
        console.print(f"[red]Login failed:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def status() -> None:
    """Check current login status."""
    session = AuthSession.load()

    if session and session.is_authenticated:
        console.print("[green]Logged in[/green]")
        if session.user_email:
            console.print(f"  User: {session.user_email}")
    else:
        console.print("[yellow]Not logged in[/yellow]")


@app.command()
def logout() -> None:
    """Clear saved session."""
    AuthSession.clear()
    console.print("Session cleared")


@app.command()
def search(
    term: str = typer.Argument(..., help="Search term"),
    max_results: int = typer.Option(10, "--max", "-m", help="Maximum results"),
) -> None:
    """Search support articles."""
    load_env()

    try:
        with RunnerSupportClient() as client:
            results = client.search(term, max_matches=max_results)

            if not results:
                console.print("[yellow]No results found[/yellow]")
                return

            table = Table(title=f"Search: {term}")
            table.add_column("Type", style="dim")
            table.add_column("Title", style="white")
            table.add_column("URL", style="cyan")

            for result in results:
                table.add_row(
                    result.get("type", ""),
                    strip_html(result.get("title", "")),
                    result.get("url", ""),
                )

            console.print(table)

    except AuthenticationError as e:
        console.print(f"[red]Authentication error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def fetch(
    article_id: str = typer.Argument(..., help="Article ID or URL path"),
) -> None:
    """Fetch and display a support article."""
    load_env()

    # Extract article ID from URL if full URL provided
    if "/" in article_id:
        # Handle URLs like /support/solutions/articles/13000068571-...
        match = re.search(r"articles/(\d+)", article_id)
        if match:
            article_id = match.group(1)

    try:
        with RunnerSupportClient() as client:
            article = client.get_article(article_id)

            title = strip_html(article.get("title", ""))
            body = strip_html(article.get("body", ""))

            console.print(f"[bold]{title}[/bold]")
            console.print(f"Article ID: {article_id}\n")
            console.print(body)

    except AuthenticationError as e:
        console.print(f"[red]Authentication error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def main() -> None:
    """Entry point."""
    app()


if __name__ == "__main__":
    main()
