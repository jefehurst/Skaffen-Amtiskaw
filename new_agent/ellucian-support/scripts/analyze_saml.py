#!/usr/bin/env python3
"""Analyze SAML responses from HAR file."""

import base64
import json
import re
from pathlib import Path


def main():
    har_path = Path(__file__).parent.parent / "tmp" / "ellucian_support_login_and_search.har"
    har = json.loads(har_path.read_text())
    entries = har["log"]["entries"]

    # Entry 95 is nav_to.do POST (0-indexed, so entries[95])
    entry = entries[95]
    req = entry["request"]

    print("=== Browser SAML POST Analysis ===\n")

    if "postData" in req and "params" in req["postData"]:
        for p in req["postData"]["params"]:
            if p["name"] == "SAMLResponse":
                saml_b64 = p["value"]
                saml_xml = base64.b64decode(saml_b64).decode("utf-8")

                # Extract key fields
                dest = re.search(r'Destination="([^"]+)"', saml_xml)
                inresp = re.search(r'InResponseTo="([^"]+)"', saml_xml)
                issuer = re.search(r"<saml2:Issuer[^>]*>([^<]+)</saml2:Issuer>", saml_xml)
                nameid = re.search(r"<saml2:NameID[^>]*>([^<]+)</saml2:NameID>", saml_xml)
                audience = re.search(r"<saml2:Audience>([^<]+)</saml2:Audience>", saml_xml)

                print("SAML Response from Browser HAR:")
                print(f"  Destination: {dest.group(1) if dest else 'NOT FOUND'}")
                print(f"  InResponseTo: {inresp.group(1) if inresp else 'NOT FOUND'}")
                print(f"  Issuer: {issuer.group(1) if issuer else 'NOT FOUND'}")
                print(f"  NameID: {nameid.group(1) if nameid else 'NOT FOUND'}")
                print(f"  Audience: {audience.group(1) if audience else 'NOT FOUND'}")
                print(f"  Total length: {len(saml_b64)} chars (base64)")
                print()

            elif p["name"] == "RelayState":
                print(f"RelayState: {p['value']}")
                print()

    # Also show the form action from the token/redirect page
    # Entry 89 is token/redirect (0-indexed)
    token_entry = entries[89]
    token_resp = token_entry["response"]

    # Get response content if available
    if "content" in token_resp and "text" in token_resp["content"]:
        html = token_resp["content"]["text"]
        form_action = re.search(r'<form[^>]*action="([^"]+)"', html)
        if form_action:
            print(f"Form action in token/redirect page: {form_action.group(1)}")


if __name__ == "__main__":
    main()
