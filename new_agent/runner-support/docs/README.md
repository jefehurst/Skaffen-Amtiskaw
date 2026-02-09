# Runner Support Documentation

This directory contains reverse-engineering notes and documentation for the Runner Technologies Support site
authentication and API.

## Files

- [auth-flow.md](auth-flow.md) - Authentication flow documentation (Rails session + CSRF)

## Overview

Runner Technologies is the vendor of CLEAN_Address, address validation software used with Ellucian Banner. Their support
site (support.runnertech.com) runs on Freshdesk and uses standard Rails session authentication - much simpler than the
Okta SAML flow used by Ellucian Support.

## Quick Reference

| Aspect         | Value                               |
| -------------- | ----------------------------------- |
| Base URL       | https://support.runnertech.com      |
| Platform       | Freshdesk (Rails-based)             |
| Auth Type      | Username/password with CSRF         |
| Session Cookie | `_helpkit_session`                  |
| Auth Cookie    | `user_credentials` (~90 day expiry) |
| CSRF Header    | `X-CSRF-Token` (from meta tag)      |
