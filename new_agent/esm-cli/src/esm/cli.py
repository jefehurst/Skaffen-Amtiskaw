"""CLI for Ellucian Solution Manager."""

import json
import os
import sys
from pathlib import Path

try:
    import typer
    from rich.console import Console
    from rich.table import Table
except ImportError:
    print("CLI dependencies not installed. Run: pip install typer rich")
    sys.exit(1)

from .client import ESMClient
from .config import ESMConfig
from .exceptions import AuthenticationError, ESMError

app = typer.Typer(help="Ellucian Solution Manager CLI")
console = Console()


def load_env():
    """Load environment from local.env if present."""
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


def get_client() -> ESMClient:
    """Create and authenticate ESM client."""
    load_env()
    config = ESMConfig.from_env()
    missing = config.validate()
    if missing:
        console.print(f"[red]Missing configuration:[/red] {', '.join(missing)}")
        console.print("[dim]Set ESM_URL, ESM_USER, ESM_PASSWORD in environment or local.env[/dim]")
        raise typer.Exit(1)

    client = ESMClient(config)
    try:
        client.login()
    except AuthenticationError as e:
        console.print(f"[red]Authentication failed:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Connection failed:[/red] {e}")
        raise typer.Exit(1)

    return client


@app.command()
def login():
    """Test ESM authentication."""
    load_env()
    config = ESMConfig.from_env()

    console.print(f"ESM URL: [cyan]{config.base_url}[/cyan]")
    console.print(f"User: [cyan]{config.username}[/cyan]")

    client = get_client()
    console.print("[green]Login successful![/green]")


@app.command()
def envs(
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """List all environments."""
    client = get_client()

    try:
        environments = client.get_environments()
    except ESMError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if json_output:
        console.print(json.dumps(environments, indent=2))
    else:
        console.print(f"\n[bold]Environments ({len(environments)})[/bold]\n")

        table = Table(show_header=True, header_style="bold")
        table.add_column("Name", width=25)
        table.add_column("Status", width=12)
        table.add_column("DB SID", width=15)
        table.add_column("Domain", width=30)

        for env in environments:
            status = env.get("status", "")
            style = "green" if status == "Running" else "yellow" if status == "Stopped" else ""
            table.add_row(
                env.get("name", ""),
                f"[{style}]{status}[/{style}]" if style else status,
                env.get("db_sid", ""),
                env.get("domain", ""),
            )

        console.print(table)


@app.command()
def products(
    env_name: str = typer.Argument(..., help="Environment name"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """List installed products for an environment."""
    client = get_client()

    try:
        product_list = client.get_products(env_name)
    except ESMError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if json_output:
        console.print(json.dumps(product_list, indent=2))
    else:
        console.print(f"\n[bold]Products in {env_name} ({len(product_list)})[/bold]\n")

        table = Table(show_header=True, header_style="bold")
        table.add_column("Product", width=30)
        table.add_column("Application", width=20)
        table.add_column("Installed", width=12)
        table.add_column("Available", width=12)

        for p in product_list:
            installed = p.get("installed_version", "")
            available = p.get("available_version", "")
            # Highlight if upgrade available
            if available and available != installed:
                available = f"[yellow]{available}[/yellow]"

            table.add_row(
                p.get("name", ""),
                p.get("application", ""),
                installed,
                available,
            )

        console.print(table)


@app.command()
def versions(
    env_name: str = typer.Argument(..., help="Environment name"),
    output: Path = typer.Option(None, "--output", "-o", help="Output file"),
):
    """Export installed versions as JSON (for comparison with releases)."""
    client = get_client()

    try:
        product_list = client.get_products(env_name)
    except ESMError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    # Build version map: product_name -> installed_version
    version_map = {}
    for p in product_list:
        name = p.get("name", "")
        version = p.get("installed_version", "")
        if name and version:
            version_map[name] = {
                "installed_version": version,
                "available_version": p.get("available_version", ""),
                "application": p.get("application", ""),
            }

    data = {
        "environment": env_name,
        "products": version_map,
    }

    json_str = json.dumps(data, indent=2)

    if output:
        output.write_text(json_str)
        console.print(f"[green]Exported {len(version_map)} product versions to {output}[/green]")
    else:
        console.print(json_str)


@app.command()
def compare(
    env_name: str = typer.Argument(..., help="Environment name"),
    releases_file: Path = typer.Argument(..., help="Releases JSON file from ellucian-support"),
    output: Path = typer.Option(None, "--output", "-o", help="Output filtered releases"),
):
    """Compare environment versions against releases to find applicable upgrades.

    Takes a releases JSON file (from 'ellucian-support releases export') and
    filters to only releases that apply to this environment's installed versions.

    Examples:

        esm compare PROD releases.json

        esm compare PROD releases.json -o applicable-releases.json
    """
    client = get_client()

    # Get installed products
    try:
        product_list = client.get_products(env_name)
    except ESMError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    # Build version lookup
    installed = {}
    for p in product_list:
        name = p.get("name", "").lower()
        app = p.get("application", "").lower()
        version = p.get("installed_version", "")
        if name:
            installed[name] = version
        if app:
            installed[app] = version

    # Load releases
    try:
        releases_data = json.loads(releases_file.read_text())
    except Exception as e:
        console.print(f"[red]Failed to read releases file:[/red] {e}")
        raise typer.Exit(1)

    releases = releases_data.get("releases", [])

    # Filter releases that might apply
    applicable = []
    for r in releases:
        product_line = r.get("product_line", "").lower()
        product_name = r.get("product_name", "").lower()
        version = r.get("version", "")

        # Check if this product is installed
        installed_version = None
        for key in [product_name, product_line]:
            if key in installed:
                installed_version = installed[key]
                break

        # Include if product is installed (regardless of version match for now)
        if installed_version:
            r["_installed_version"] = installed_version
            r["_applicable"] = True
            applicable.append(r)

    result = {
        "environment": env_name,
        "releases_checked": len(releases),
        "applicable_count": len(applicable),
        "releases": applicable,
    }

    json_str = json.dumps(result, indent=2)

    if output:
        output.write_text(json_str)
        console.print(f"[green]Found {len(applicable)} applicable releases (of {len(releases)} total)[/green]")
        console.print(f"[green]Written to {output}[/green]")
    else:
        console.print(f"\n[bold]Applicable Releases for {env_name}[/bold]")
        console.print(f"[dim]Checked {len(releases)} releases, {len(applicable)} apply[/dim]\n")

        if applicable:
            table = Table(show_header=True, header_style="bold")
            table.add_column("Release", width=14)
            table.add_column("Product", width=25)
            table.add_column("Version", width=12)
            table.add_column("Installed", width=12)
            table.add_column("Date", width=12)

            for r in applicable:
                table.add_row(
                    r.get("number", ""),
                    r.get("short_description", "")[:25],
                    r.get("version", ""),
                    r.get("_installed_version", ""),
                    r.get("date_released", "")[:10],
                )

            console.print(table)
        else:
            console.print("[dim]No applicable releases found[/dim]")


def main():
    """Entry point."""
    app()


if __name__ == "__main__":
    main()
