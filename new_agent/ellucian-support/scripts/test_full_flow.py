#!/usr/bin/env python3
"""Test the full authentication flow with MFA."""

import os
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Load env
env_file = Path(__file__).parent.parent.parent / "local.env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key.strip(), value)

from ellucian_support.auth import AuthenticationError, OktaAuthenticator


def main():
    username = os.environ.get("ELLUCIAN_SUPPORT_USER")
    password = os.environ.get("ELLUCIAN_SUPPORT_PW")

    if not username or not password:
        print("ERROR: Set ELLUCIAN_SUPPORT_USER and ELLUCIAN_SUPPORT_PW")
        sys.exit(1)

    # MFA code from command line or prompt
    mfa_code = sys.argv[1] if len(sys.argv) > 1 else None

    def mfa_callback():
        if mfa_code:
            return mfa_code
        return input("Enter MFA code: ")

    print(f"Authenticating as: {username}")

    try:
        with OktaAuthenticator(username, password, mfa_callback) as auth:
            session = auth.authenticate()

            print("\n=== SUCCESS ===")
            print(f"User email: {session.user_email}")
            if session.glide_session_store:
                print(f"Glide session: {session.glide_session_store[:30]}...")
            else:
                print("No glide session")
            print(f"Cookies: {list(session.cookies.keys())}")

    except AuthenticationError as e:
        print(f"\nERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
