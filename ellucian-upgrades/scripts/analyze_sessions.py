#!/usr/bin/env python3
"""
Analyze Claude Code session logs for correction patterns and instructional moments.

This script mines session history to identify:
1. User corrections - moments where the user redirected behavior
2. Explicit instructions - standing orders for future behavior
3. Behavioral guidance - requests to update procedures/profiles

Output: Structured report of learnings for promptcraft improvement.
"""

import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator

# Patterns that indicate user corrections
CORRECTION_PATTERNS = [
    r"\bno[,.]?\s+(don'?t|that'?s|you)",
    r"\bwrong\b",
    r"\bactually[,]?\s",
    r"\binstead[,]?\s",
    r"\bstop\s+(doing|asking|trying)",
    r"\bdon'?t\s+(do|ask|try|assume|guess)",
    r"\bnot\s+what\s+I",
    r"\bthat'?s\s+not",
    r"\bI\s+said\b",
    r"\bI\s+meant\b",
    r"\bI\s+wanted\b",
]

# Patterns that indicate standing instructions
INSTRUCTION_PATTERNS = [
    r"\balways\s+\w+",
    r"\bnever\s+\w+",
    r"\bfrom\s+now\s+on\b",
    r"\bremember\s+(to|that)\b",
    r"\bupdate\s+(your|the)\s+(procedures?|profile|CLAUDE)",
    r"\badd\s+(this\s+)?to\s+(CLAUDE|profile)",
    r"\bthis\s+is\s+(how|the\s+way)\b",
    r"\bprefer\s+\w+",
    r"\buse\s+\w+\s+instead",
    r"\bwhen\s+you\s+see\b",
    r"\bif\s+you\s+encounter\b",
]

# Patterns indicating frustration/repeated issues
FRUSTRATION_PATTERNS = [
    r"\bagain\b",
    r"\balready\s+told\s+you",
    r"\bI\s+keep\s+saying",
    r"\bhow\s+many\s+times",
    r"\bwe\s+discussed\s+this",
    r"\bI\s+explained\b",
]


@dataclass
class Finding:
    """A finding from session analysis."""

    session_id: str
    timestamp: str
    category: str  # correction, instruction, frustration
    pattern_matched: str
    user_message: str
    context_before: str  # assistant message before
    context_after: str  # assistant response after

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "category": self.category,
            "pattern": self.pattern_matched,
            "user_message": self.user_message[:500] if self.user_message else "",
            "context_before": self.context_before[:300] if self.context_before else "",
            "context_after": self.context_after[:300] if self.context_after else "",
        }


def load_session(path: Path) -> list[dict]:
    """Load a session JSONL file."""
    messages = []
    with open(path) as f:
        for line in f:
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return messages


def extract_text_content(message: dict) -> str:
    """Extract text from a message content block."""
    content = message.get("message", {}).get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    texts.append(block.get("text", ""))
                elif block.get("type") == "tool_result":
                    texts.append(str(block.get("content", ""))[:100])
        return " ".join(texts)
    return ""


def find_patterns(text: str, patterns: list[str]) -> list[str]:
    """Find all matching patterns in text."""
    matches = []
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            matches.append(pattern)
    return matches


def analyze_session(path: Path) -> Iterator[Finding]:
    """Analyze a single session for findings."""
    messages = load_session(path)
    session_id = path.stem

    # Build message chain (kept for future context linking)
    _ = {m.get("uuid"): m for m in messages if "uuid" in m}

    prev_assistant = ""

    for msg in messages:
        msg_type = msg.get("type")
        role = msg.get("message", {}).get("role")

        if msg_type == "user" and role == "user":
            text = extract_text_content(msg)
            timestamp = msg.get("timestamp", "")

            # Check for corrections
            correction_matches = find_patterns(text, CORRECTION_PATTERNS)
            for pattern in correction_matches:
                yield Finding(
                    session_id=session_id,
                    timestamp=timestamp,
                    category="correction",
                    pattern_matched=pattern,
                    user_message=text,
                    context_before=prev_assistant,
                    context_after="",
                )

            # Check for instructions
            instruction_matches = find_patterns(text, INSTRUCTION_PATTERNS)
            for pattern in instruction_matches:
                yield Finding(
                    session_id=session_id,
                    timestamp=timestamp,
                    category="instruction",
                    pattern_matched=pattern,
                    user_message=text,
                    context_before=prev_assistant,
                    context_after="",
                )

            # Check for frustration
            frustration_matches = find_patterns(text, FRUSTRATION_PATTERNS)
            for pattern in frustration_matches:
                yield Finding(
                    session_id=session_id,
                    timestamp=timestamp,
                    category="frustration",
                    pattern_matched=pattern,
                    user_message=text,
                    context_before=prev_assistant,
                    context_after="",
                )

        elif role == "assistant":
            prev_assistant = extract_text_content(msg)


def analyze_all_sessions(sessions_dir: Path) -> list[Finding]:
    """Analyze all sessions in a directory."""
    findings = []
    for path in sessions_dir.glob("*.jsonl"):
        try:
            for finding in analyze_session(path):
                findings.append(finding)
        except Exception as e:
            print(f"Error processing {path}: {e}", file=sys.stderr)
    return findings


def categorize_findings(findings: list[Finding]) -> dict[str, list[Finding]]:
    """Group findings by category and pattern."""
    by_category = defaultdict(list)
    for f in findings:
        by_category[f.category].append(f)
    return dict(by_category)


def generate_report(findings: list[Finding]) -> str:
    """Generate a markdown report of findings."""
    categorized = categorize_findings(findings)

    lines = [
        "# Session Analysis Report",
        "",
        f"**Generated**: {datetime.now().isoformat()}",
        f"**Total Findings**: {len(findings)}",
        "",
    ]

    for category in ["correction", "instruction", "frustration"]:
        items = categorized.get(category, [])
        lines.append(f"## {category.title()}s ({len(items)})")
        lines.append("")

        if not items:
            lines.append("*No findings*")
            lines.append("")
            continue

        # Group by pattern
        by_pattern = defaultdict(list)
        for item in items:
            by_pattern[item.pattern_matched].append(item)

        for pattern, pattern_items in sorted(by_pattern.items(), key=lambda x: -len(x[1])):
            lines.append(f"### Pattern: `{pattern}` ({len(pattern_items)} occurrences)")
            lines.append("")

            # Show up to 3 examples
            for item in pattern_items[:3]:
                lines.append(f"**Session**: `{item.session_id[:8]}...`")
                lines.append(f"**Time**: {item.timestamp}")
                lines.append("")
                lines.append("```")
                # Truncate for readability
                msg = item.user_message[:400]
                if len(item.user_message) > 400:
                    msg += "..."
                lines.append(msg)
                lines.append("```")
                lines.append("")

            if len(pattern_items) > 3:
                lines.append(f"*... and {len(pattern_items) - 3} more*")
                lines.append("")

    return "\n".join(lines)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Analyze Claude Code session logs")
    parser.add_argument(
        "--sessions-dir",
        type=Path,
        default=Path.home() / ".claude/projects/<project-path>",
        help="Directory containing session JSONL files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file (default: stdout)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON instead of markdown",
    )

    args = parser.parse_args()

    findings = analyze_all_sessions(args.sessions_dir)

    if args.json:
        output = json.dumps([f.to_dict() for f in findings], indent=2)
    else:
        output = generate_report(findings)

    if args.output:
        args.output.write_text(output)
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
