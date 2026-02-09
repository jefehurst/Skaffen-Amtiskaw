#!/usr/bin/env python3
"""Fetch a single article by URL."""

import sys
import re
import html
from pathlib import Path

from runner_support.client import RunnerSupportClient


def clean_html(text: str) -> str:
    """Convert HTML to readable markdown."""
    text = html.unescape(text)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<p[^>]*>", "\n\n", text)
    text = re.sub(r"</p>", "", text)
    text = re.sub(r"<li[^>]*>", "\n- ", text)
    text = re.sub(r"</li>", "", text)
    text = re.sub(r"<h1[^>]*>", "\n# ", text)
    text = re.sub(r"</h1>", "\n", text)
    text = re.sub(r"<h2[^>]*>", "\n## ", text)
    text = re.sub(r"</h2>", "\n", text)
    text = re.sub(r"<h3[^>]*>", "\n### ", text)
    text = re.sub(r"</h3>", "\n", text)
    text = re.sub(r"<strong[^>]*>", "**", text)
    text = re.sub(r"</strong>", "**", text)
    text = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', r"[\2](\1)", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n\n\n+", "\n\n", text)
    return text.strip()


url = (
    sys.argv[1]
    if len(sys.argv) > 1
    else "/support/solutions/articles/13000095804-clean-address-installation-guide"
)

with RunnerSupportClient() as client:
    # Ensure authenticated (loads cookies)
    client._ensure_authenticated()

    full_url = f"https://support.runnertech.com{url}"
    print(f"Fetching: {full_url}")
    resp = client._client.get(full_url)
    print(f"Status: {resp.status_code}")
    print(f"Length: {len(resp.text)}")

    # Save raw HTML
    Path("/tmp/article.html").write_text(resp.text)
    print("Saved raw HTML to /tmp/article.html")

    # Extract body
    body_match = re.search(
        r'<article[^>]*class="[^"]*article-body[^"]*"[^>]*>(.*?)</article>', resp.text, re.DOTALL
    )
    if body_match:
        body = clean_html(body_match.group(1))
        print(f"\n=== ARTICLE BODY ({len(body)} chars) ===\n")
        print(body[:5000])
        if len(body) > 5000:
            print(f"\n... (truncated, {len(body)} total chars)")
    else:
        print("No article body found")

    # Check for PDF attachments
    pdf_links = re.findall(r'href="([^"]*\.pdf[^"]*)"', resp.text, re.IGNORECASE)
    if pdf_links:
        print("\n=== PDF ATTACHMENTS ===")
        for link in pdf_links:
            print(f"  {link}")
