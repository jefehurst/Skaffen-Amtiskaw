"""Base parsing utilities for ESM HTML responses."""

from typing import Any

from bs4 import BeautifulSoup, Tag

from ..selectors import get_selectors


def parse_table(
    soup: BeautifulSoup | Tag, selector: str | None = None, version: str | None = None
) -> list[dict[str, Any]]:
    """Parse an HTML table into a list of dicts.

    Args:
        soup: BeautifulSoup object or Tag containing the table
        selector: CSS selector for table. If None, uses default data_table selector.
        version: ESM version for selector overrides

    Returns:
        List of dicts, one per row, with header keys
    """
    selectors = get_selectors(version)
    table_selector = selector or selectors["data_table"]

    table = soup.select_one(table_selector)
    if not table:
        return []

    rows = table.find_all("tr")
    if not rows:
        return []

    # Extract headers from first row
    first_row = rows[0]
    headers = [th.get_text(strip=True) for th in first_row.find_all("th")]

    if headers:
        data_rows = rows[1:]
    else:
        # First row might be data if no th elements
        headers = [td.get_text(strip=True) for td in first_row.find_all("td")]
        data_rows = rows[1:]

    if not headers:
        return []

    # Parse data rows
    result = []
    for row in data_rows:
        cells = row.find_all("td")
        row_data: dict[str, Any] = {}

        for i, cell in enumerate(cells):
            if i < len(headers):
                key = headers[i]
                row_data[key] = cell.get_text(strip=True)

                # Capture target-url attribute if present
                url = cell.get("target-url")
                if url:
                    row_data[f"{key}_url"] = url

                # Capture any data attributes
                for attr, value in cell.attrs.items():
                    if attr.startswith("data-"):
                        row_data[f"{key}_{attr}"] = value

        if row_data:
            result.append(row_data)

    return result


def extract_field(soup: BeautifulSoup | Tag, selector: str) -> str:
    """Extract text from a single element.

    Args:
        soup: BeautifulSoup object or Tag
        selector: CSS selector

    Returns:
        Extracted text or empty string
    """
    element = soup.select_one(selector)
    if element:
        return element.get_text(strip=True)
    return ""


def extract_form_fields(soup: BeautifulSoup | Tag, form_selector: str = "form") -> dict[str, Any]:
    """Extract all form fields and their values.

    Args:
        soup: BeautifulSoup object or Tag
        form_selector: CSS selector for the form

    Returns:
        Dict mapping field names to values/metadata
    """
    form = soup.select_one(form_selector)
    if not form:
        return {}

    fields: dict[str, Any] = {}

    # Text and hidden inputs
    for inp in form.select("input[type='text'], input[type='hidden'], input[type='password']"):
        name = inp.get("name")
        if name:
            fields[name] = {
                "type": inp.get("type", "text"),
                "value": inp.get("value", ""),
                "id": inp.get("id", ""),
            }

    # Checkboxes
    for inp in form.select("input[type='checkbox']"):
        name = inp.get("name")
        if name:
            fields[name] = {
                "type": "checkbox",
                "checked": inp.has_attr("checked"),
                "value": inp.get("value", "on"),
                "id": inp.get("id", ""),
            }

    # Radio buttons
    for inp in form.select("input[type='radio']"):
        name = inp.get("name")
        if name:
            if name not in fields:
                fields[name] = {"type": "radio", "options": [], "selected": None}
            option = {"value": inp.get("value", ""), "id": inp.get("id", "")}
            fields[name]["options"].append(option)
            if inp.has_attr("checked"):
                fields[name]["selected"] = inp.get("value")

    # Selects
    for select in form.select("select"):
        name = select.get("name")
        if name:
            options = []
            selected = None
            for opt in select.select("option"):
                opt_value = opt.get("value", opt.get_text(strip=True))
                options.append({"value": opt_value, "label": opt.get_text(strip=True)})
                if opt.has_attr("selected"):
                    selected = opt_value
            fields[name] = {"type": "select", "options": options, "selected": selected}

    # Textareas
    for textarea in form.select("textarea"):
        name = textarea.get("name")
        if name:
            fields[name] = {
                "type": "textarea",
                "value": textarea.get_text(),
                "id": textarea.get("id", ""),
            }

    return fields
