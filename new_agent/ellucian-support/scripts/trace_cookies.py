#!/usr/bin/env python3
"""Trace where the JSESSIONID cookie comes from in the auth flow."""

import json
from pathlib import Path

HAR_FILE = Path(__file__).parent.parent / "tmp" / "ellucian_support_login_and_search.har"


def main():
    with open(HAR_FILE) as f:
        har = json.load(f)

    print("=== All requests between Okta page load and introspect ===\n")

    in_okta_section = False
    for i, entry in enumerate(har["log"]["entries"]):
        url = entry["request"]["url"]

        # Start tracking after the SAML page
        if "sso.ellucian.com/app/" in url and "saml" in url.lower():
            in_okta_section = True

        if not in_okta_section:
            continue

        req = entry["request"]
        resp = entry["response"]

        # Cookies sent
        req_cookies = {c["name"]: c["value"][:30] for c in req.get("cookies", [])}

        # Cookies set
        resp_cookies = {}
        for c in resp.get("cookies", []):
            resp_cookies[c["name"]] = c["value"][:30] if c["value"] else "(empty)"

        # Also check Set-Cookie headers
        for h in resp.get("headers", []):
            if h["name"].lower() == "set-cookie":
                val = h["value"]
                name = val.split("=")[0]
                value = val.split("=")[1].split(";")[0][:30] if "=" in val else ""
                resp_cookies[name] = value

        # Simplify URL for display
        short_url = url.split("?")[0]
        if len(short_url) > 60:
            short_url = short_url[:60] + "..."

        print(f"[{i}] {req['method']} {short_url}")
        print(f"    Status: {resp['status']}")
        if "JSESSIONID" in req_cookies:
            print(f"    JSESSIONID sent: {req_cookies['JSESSIONID']}")
        if "JSESSIONID" in resp_cookies:
            print(f"    JSESSIONID set:  {resp_cookies['JSESSIONID']}")
        print()

        # Stop after introspect
        if "introspect" in url:
            break


if __name__ == "__main__":
    main()
