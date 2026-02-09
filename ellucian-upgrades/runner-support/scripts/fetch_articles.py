#!/usr/bin/env python3
"""Fetch CLEAN_Address articles from Runner Support."""

import re
import html
from pathlib import Path

from runner_support.client import RunnerSupportClient

# Single focused search
SEARCH_TERMS = [
    "CLEAN_Address Banner 9",
]


def clean_html(text: str) -> str:
    """Convert HTML to readable markdown."""
    # Decode HTML entities
    text = html.unescape(text)

    # Remove style and script tags entirely
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)

    # Convert common tags to markdown
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<p[^>]*>", "\n\n", text)
    text = re.sub(r"</p>", "", text)
    text = re.sub(r"<li[^>]*>", "\n- ", text)
    text = re.sub(r"</li>", "", text)
    text = re.sub(r"<ul[^>]*>", "\n", text)
    text = re.sub(r"</ul>", "\n", text)
    text = re.sub(r"<ol[^>]*>", "\n", text)
    text = re.sub(r"</ol>", "\n", text)
    text = re.sub(r"<h1[^>]*>", "\n# ", text)
    text = re.sub(r"</h1>", "\n", text)
    text = re.sub(r"<h2[^>]*>", "\n## ", text)
    text = re.sub(r"</h2>", "\n", text)
    text = re.sub(r"<h3[^>]*>", "\n### ", text)
    text = re.sub(r"</h3>", "\n", text)
    text = re.sub(r"<h4[^>]*>", "\n#### ", text)
    text = re.sub(r"</h4>", "\n", text)
    text = re.sub(r"<strong[^>]*>", "**", text)
    text = re.sub(r"</strong>", "**", text)
    text = re.sub(r"<b[^>]*>", "**", text)
    text = re.sub(r"</b>", "**", text)
    text = re.sub(r"<em[^>]*>", "*", text)
    text = re.sub(r"</em>", "*", text)
    text = re.sub(r"<i[^>]*>", "*", text)
    text = re.sub(r"</i>", "*", text)
    text = re.sub(r"<code[^>]*>", "`", text)
    text = re.sub(r"</code>", "`", text)
    text = re.sub(r"<pre[^>]*>", "\n```\n", text)
    text = re.sub(r"</pre>", "\n```\n", text)
    text = re.sub(r"<blockquote[^>]*>", "\n> ", text)
    text = re.sub(r"</blockquote>", "\n", text)
    text = re.sub(r"<hr[^>]*/?>", "\n---\n", text)

    # Handle tables simply
    text = re.sub(r"<table[^>]*>", "\n", text)
    text = re.sub(r"</table>", "\n", text)
    text = re.sub(r"<tr[^>]*>", "", text)
    text = re.sub(r"</tr>", "\n", text)
    text = re.sub(r"<t[dh][^>]*>", "| ", text)
    text = re.sub(r"</t[dh]>", " ", text)

    # Extract links
    text = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', r"[\2](\1)", text)

    # Remove span tags but keep content
    text = re.sub(r"<span[^>]*>", "", text)
    text = re.sub(r"</span>", "", text)

    # Remove div tags but keep content
    text = re.sub(r"<div[^>]*>", "\n", text)
    text = re.sub(r"</div>", "", text)

    # Remove remaining tags
    text = re.sub(r"<[^>]+>", "", text)

    # Clean up whitespace
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n\n\n+", "\n\n", text)
    text = text.strip()

    return text


def fetch_article(
    client: RunnerSupportClient, url: str, output_dir: Path
) -> tuple[str, str, list[str]]:
    """Fetch an article and extract title, body, and attachments."""
    full_url = f"https://support.runnertech.com{url}"
    resp = client._client.get(full_url)

    if resp.status_code != 200:
        return "", f"Error: {resp.status_code}", []

    # Extract title
    title_match = re.search(
        r'<h2[^>]*class="[^"]*heading[^"]*"[^>]*>\s*<[^>]*>\s*([^<]+)', resp.text
    )
    if not title_match:
        title_match = re.search(r"<title>([^<]+)</title>", resp.text)
    title = title_match.group(1).strip() if title_match else "Unknown"
    title = html.unescape(title)

    # Extract article body
    body_match = re.search(
        r'<article[^>]*class="[^"]*article-body[^"]*"[^>]*>(.*?)</article>', resp.text, re.DOTALL
    )
    body = body_match.group(1) if body_match else ""

    # Find attachments - look for attachment links
    attachments = []
    attachment_patterns = [
        r'<a[^>]*href="([^"]*attachments[^"]*)"[^>]*>([^<]+)</a>',
        r'<a[^>]*href="([^"]*\.pdf)"[^>]*>([^<]+)</a>',
        r'<a[^>]*href="([^"]*\.doc[x]?)"[^>]*>([^<]+)</a>',
        r'<a[^>]*href="([^"]*\.xls[x]?)"[^>]*>([^<]+)</a>',
        r'<a[^>]*href="([^"]*\.zip)"[^>]*>([^<]+)</a>',
    ]

    for pattern in attachment_patterns:
        for match in re.finditer(pattern, resp.text, re.IGNORECASE):
            att_url = match.group(1)
            att_name = match.group(2).strip()
            if att_url and att_name:
                attachments.append((att_url, att_name))

    return title, clean_html(body), attachments


def download_attachment(
    client: RunnerSupportClient, att_url: str, att_name: str, output_dir: Path
) -> str | None:
    """Download an attachment file."""
    # Make URL absolute if needed
    if att_url.startswith("/"):
        att_url = f"https://support.runnertech.com{att_url}"
    elif not att_url.startswith("http"):
        return None

    try:
        resp = client._client.get(att_url)
        if resp.status_code != 200:
            return None

        # Clean up filename
        safe_name = re.sub(r"[^\w\-_\. ]", "", att_name)
        safe_name = safe_name.replace(" ", "_")
        if not safe_name:
            safe_name = "attachment"

        # Ensure we have an extension
        if "." not in safe_name:
            content_type = resp.headers.get("content-type", "")
            if "pdf" in content_type:
                safe_name += ".pdf"
            elif "word" in content_type or "document" in content_type:
                safe_name += ".docx"
            elif "excel" in content_type or "spreadsheet" in content_type:
                safe_name += ".xlsx"
            else:
                safe_name += ".bin"

        # Save to attachments directory
        att_dir = output_dir / "attachments"
        att_dir.mkdir(exist_ok=True)
        att_file = att_dir / safe_name

        with open(att_file, "wb") as f:
            f.write(resp.content)

        return f"attachments/{safe_name}"
    except Exception:
        return None


def url_to_slug(url: str) -> str:
    """Convert URL to filename slug."""
    # Extract the last part after articles/
    match = re.search(r"/articles/(\d+-[^/]+)", url)
    if match:
        slug = match.group(1)
        # Remove leading numbers and dash
        slug = re.sub(r"^\d+-", "", slug)
        # Clean up
        slug = slug.rstrip("-")
        return slug[:60]  # Limit length
    return "unknown"


def main():
    output_dir = Path(__file__).parent.parent.parent / "docs" / "runner" / "clean-address"
    output_dir.mkdir(parents=True, exist_ok=True)

    seen_urls = set()
    articles = []

    with RunnerSupportClient() as client:
        print("Searching for articles...")

        for term in SEARCH_TERMS:
            print(f"  '{term}'...")
            results = client.search(term, max_matches=20)
            for r in results:
                if r["type"] == "ARTICLE" and r["url"] not in seen_urls:
                    seen_urls.add(r["url"])
                    # Clean up title
                    title = re.sub(r"<[^>]+>", "", r["title"])
                    articles.append((r["url"], title))

        print(f"\nFound {len(articles)} unique articles")

        # Filter to Banner 9 core docs only (skip newsletters, duplicates, other platforms)
        skip_keywords = [
            "newsletter",
            "peoplesoft",
            "colleague",
            "advance",
            "jd edwards",
            "e-business",
            "ebs",
            "monthly",
            "hecvat",
        ]
        require_keywords = ["banner"]
        filtered = []
        seen_titles = set()
        for url, title in articles:
            title_lower = title.lower()
            # Skip unwanted content
            if any(kw in title_lower for kw in skip_keywords):
                continue
            # Must be Banner-related
            if not any(kw in title_lower for kw in require_keywords):
                continue
            # Skip duplicates by title
            if title_lower in seen_titles:
                continue
            seen_titles.add(title_lower)
            filtered.append((url, title))

        print(f"Filtered to {len(filtered)} relevant articles\n")
        print("Fetching articles...")

        all_attachments = []

        for url, search_title in filtered:
            slug = url_to_slug(url)
            print(f"  {slug}...", end=" ", flush=True)
            try:
                title, body, attachments = fetch_article(client, url, output_dir)
                if body and len(body) > 200:
                    output_file = output_dir / f"{slug}.md"
                    with open(output_file, "w") as f:
                        f.write(f"# {title}\n\n")
                        f.write(f"Source: https://support.runnertech.com{url}\n\n")
                        f.write("---\n\n")
                        f.write(body)

                        # Add attachments section if any
                        if attachments:
                            f.write("\n\n---\n\n## Attachments\n\n")
                            for att_url, att_name in attachments:
                                local_path = download_attachment(
                                    client, att_url, att_name, output_dir
                                )
                                if local_path:
                                    f.write(f"- [{att_name}]({local_path})\n")
                                    all_attachments.append((att_name, local_path))
                                else:
                                    f.write(f"- {att_name} (download failed)\n")

                    att_info = f", {len(attachments)} attachments" if attachments else ""
                    print(f"OK ({len(body)} chars{att_info})")
                else:
                    print(f"SKIP (body too short: {len(body)})")
            except Exception as e:
                print(f"ERROR: {e}")

        if all_attachments:
            print(f"\nDownloaded {len(all_attachments)} attachments")

        print("\nCreating index...")
        index_file = output_dir / "INDEX.md"
        with open(index_file, "w") as f:
            f.write("# CLEAN_Address Documentation\n\n")
            f.write("Articles fetched from Runner Technologies Support.\n\n")
            f.write("## Articles\n\n")
            for url, title in sorted(filtered, key=lambda x: x[1]):
                slug = url_to_slug(url)
                if (output_dir / f"{slug}.md").exists():
                    f.write(f"- [{title}]({slug}.md)\n")

        print("Done!")


if __name__ == "__main__":
    main()
