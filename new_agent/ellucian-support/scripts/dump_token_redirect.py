#!/usr/bin/env python3
"""Dump the token/redirect page HTML to see the form structure."""

import json
from pathlib import Path


def main():
    har_path = Path(__file__).parent.parent / "tmp" / "ellucian_support_login_and_search.har"
    har = json.loads(har_path.read_text())
    entries = har["log"]["entries"]

    # Entry 89 is token/redirect
    entry = entries[89]
    resp = entry["response"]

    print("=== Token/Redirect Page ===\n")
    print(f"URL: {entry['request']['url'][:80]}...")
    print(f"Status: {resp['status']}")
    print()

    if "content" in resp and "text" in resp["content"]:
        html = resp["content"]["text"]

        # Find the form
        import re

        form_match = re.search(r"<form[^>]*>(.*?)</form>", html, re.DOTALL | re.IGNORECASE)
        if form_match:
            form_html = form_match.group(0)
            print("Form HTML (cleaned):")
            print("-" * 50)

            # Extract key parts
            action = re.search(r'action="([^"]+)"', form_html)
            method = re.search(r'method="([^"]+)"', form_html, re.IGNORECASE)

            print(f"Action: {action.group(1) if action else 'NOT FOUND'}")
            print(f"Method: {method.group(1) if method else 'NOT FOUND'}")

            # Extract inputs
            inputs = re.findall(r"<input[^>]+>", form_html, re.IGNORECASE)
            print(f"\nInputs ({len(inputs)}):")
            for inp in inputs:
                name = re.search(r'name="([^"]+)"', inp)
                type_ = re.search(r'type="([^"]+)"', inp)
                value = re.search(r'value="([^"]{0,50})', inp)
                field_name = name.group(1) if name else "?"
                field_type = type_.group(1) if type_ else "?"
                field_val = value.group(1) + "..." if value else "?"
                print(f"  - {field_name} ({field_type}): {field_val}")
        else:
            print("No form found in page")
            print("\nFirst 2000 chars of page:")
            print(html[:2000])
    else:
        print("No content in response")


if __name__ == "__main__":
    main()
