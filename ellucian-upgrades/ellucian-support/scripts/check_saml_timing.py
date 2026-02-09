#!/usr/bin/env python3
"""Check SAML assertion timing constraints."""

import base64
import json
import re
from datetime import datetime
from pathlib import Path


def main():
    har_path = Path(__file__).parent.parent / "tmp" / "ellucian_support_login_and_search.har"
    har = json.loads(har_path.read_text())
    entries = har["log"]["entries"]

    print("=== SAML Timing Analysis ===\n")

    # Get the SAML response
    entry = entries[95]  # nav_to.do POST
    req = entry["request"]

    # Get request timestamp
    started = entry.get("startedDateTime", "unknown")
    print(f"Request timestamp: {started}")

    if "postData" in req and "params" in req["postData"]:
        for p in req["postData"]["params"]:
            if p["name"] == "SAMLResponse":
                saml_b64 = p["value"]
                saml_xml = base64.b64decode(saml_b64).decode("utf-8")

                # Extract timing fields
                issue_instant = re.search(r'IssueInstant="([^"]+)"', saml_xml)
                not_before = re.search(r'NotBefore="([^"]+)"', saml_xml)
                not_after = re.search(r'NotOnOrAfter="([^"]+)"', saml_xml)
                authn_instant = re.search(r'AuthnInstant="([^"]+)"', saml_xml)

                print("\nSAML Assertion Timing:")
                print(f"  IssueInstant: {issue_instant.group(1) if issue_instant else 'NOT FOUND'}")
                print(f"  NotBefore: {not_before.group(1) if not_before else 'NOT FOUND'}")
                print(f"  NotOnOrAfter: {not_after.group(1) if not_after else 'NOT FOUND'}")
                print(f"  AuthnInstant: {authn_instant.group(1) if authn_instant else 'NOT FOUND'}")

                # Parse and calculate validity window
                if not_before and not_after:
                    try:
                        nb = datetime.fromisoformat(not_before.group(1).replace("Z", "+00:00"))
                        na = datetime.fromisoformat(not_after.group(1).replace("Z", "+00:00"))
                        window = (na - nb).total_seconds()
                        print(f"\n  Validity window: {window} seconds ({window / 60:.1f} minutes)")
                    except Exception as e:
                        print(f"\n  Error parsing dates: {e}")

    # Check time between token/redirect and nav_to.do
    token_entry = entries[89]  # token/redirect
    nav_entry = entries[95]  # nav_to.do

    token_time = token_entry.get("startedDateTime", "")
    nav_time = nav_entry.get("startedDateTime", "")

    if token_time and nav_time:
        try:
            t1 = datetime.fromisoformat(token_time.replace("Z", "+00:00"))
            t2 = datetime.fromisoformat(nav_time.replace("Z", "+00:00"))
            delta = (t2 - t1).total_seconds()
            print(f"\nTime between token/redirect and nav_to.do: {delta:.2f} seconds")
        except Exception as e:
            print(f"\nError calculating time delta: {e}")


if __name__ == "__main__":
    main()
