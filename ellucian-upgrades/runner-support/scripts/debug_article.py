#!/usr/bin/env python3
"""Debug article page structure."""

from runner_support.client import RunnerSupportClient

with RunnerSupportClient() as client:
    # First get article URL from search
    results = client.search("What is CLEAN_Address", max_matches=5)
    print("Search results:")
    for r in results:
        print(f"  {r['type']}: {r['title']}")
        print(f"    URL: {r['url']}")
    print()

    # Use the first article URL
    if results:
        article_url = "https://support.runnertech.com" + results[0]["url"]
    else:
        article_url = "https://support.runnertech.com/support/solutions/articles/5000549408-what-is-clean_address-"

    print(f"Fetching: {article_url}")
    resp = client._client.get(article_url)
    print(f"Status: {resp.status_code}")
    print(f"Length: {len(resp.text)}")

    # Save full HTML for inspection
    with open("/tmp/article.html", "w") as f:
        f.write(resp.text)
    print("Saved to /tmp/article.html")

    # Look for key patterns
    import re

    patterns = [
        (r"article-body", "article-body class"),
        (r"article-content", "article-content class"),
        (r"<article", "<article> tag"),
        (r'class="fr-view"', "fr-view class"),
        (r"data-article-id", "data-article-id"),
    ]

    print("\nPattern search:")
    for pattern, name in patterns:
        matches = re.findall(pattern, resp.text)
        print(f"  {name}: {len(matches)} matches")

    # Show snippet around article
    idx = resp.text.find("article-body")
    if idx > 0:
        print(f"\nContext around 'article-body' (pos {idx}):")
        print(resp.text[idx - 100 : idx + 500])
