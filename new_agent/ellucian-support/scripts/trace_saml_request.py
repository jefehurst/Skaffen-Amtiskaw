#!/usr/bin/env python3
"""Trace SAMLRequest ID through the flow."""

import base64
import json
import re
import zlib
from pathlib import Path
from urllib.parse import parse_qs, urlparse


def main():
    har_path = Path(__file__).parent.parent / "tmp" / "ellucian_support_login_and_search.har"
    har = json.loads(har_path.read_text())
    entries = har["log"]["entries"]

    print("=== Tracing SAMLRequest ID ===\n")

    # Entry 38 is auth_redirect.do which contains the SAML URL
    # The SAML URL has the SAMLRequest parameter
    entry = entries[38]
    resp = entry["response"]

    # Get the page content to find the Okta URL
    if "content" in resp and "text" in resp["content"]:
        html = resp["content"]["text"]

        # Find the Okta SAML URL
        match = re.search(r"(https://sso\.ellucian\.com/app/[^\"'<>\s;]+)", html)
        if match:
            saml_url = match.group(1).replace("&amp;", "&")
            print("SAML URL found in auth_redirect.do page")

            parsed = urlparse(saml_url)
            params = parse_qs(parsed.query)

            if "SAMLRequest" in params:
                saml_req_b64 = params["SAMLRequest"][0]
                try:
                    # SAMLRequest is deflated then base64 encoded
                    saml_req_xml = zlib.decompress(base64.b64decode(saml_req_b64), -15).decode("utf-8")

                    # Extract the ID
                    req_id_match = re.search(r'ID="([^"]+)"', saml_req_xml)
                    issuer_match = re.search(r"<saml:Issuer>([^<]+)</saml:Issuer>", saml_req_xml)
                    acs_match = re.search(r'AssertionConsumerServiceURL="([^"]+)"', saml_req_xml)

                    print("\nSAMLRequest Analysis:")
                    print(f"  Request ID: {req_id_match.group(1) if req_id_match else 'NOT FOUND'}")
                    print(f"  Issuer: {issuer_match.group(1) if issuer_match else 'NOT FOUND'}")
                    print(f"  ACS URL: {acs_match.group(1) if acs_match else 'NOT FOUND'}")

                except Exception as e:
                    print(f"  Error decoding SAMLRequest: {e}")

            if "RelayState" in params:
                print(f"\nRelayState in URL: {params['RelayState'][0]}")
        else:
            print("Could not find SAML URL in auth_redirect page")
    else:
        print("No content in auth_redirect response")

    # Now check the SAMLResponse
    print("\n" + "=" * 50)
    print("\n=== SAMLResponse Analysis ===\n")

    entry = entries[95]  # nav_to.do POST
    req = entry["request"]

    if "postData" in req and "params" in req["postData"]:
        for p in req["postData"]["params"]:
            if p["name"] == "SAMLResponse":
                saml_b64 = p["value"]
                saml_xml = base64.b64decode(saml_b64).decode("utf-8")

                inresp = re.search(r'InResponseTo="([^"]+)"', saml_xml)
                print(f"InResponseTo: {inresp.group(1) if inresp else 'NOT FOUND'}")

    print("\n=== ID Match Check ===")
    print("The InResponseTo in SAMLResponse must match the ID in SAMLRequest")


if __name__ == "__main__":
    main()
