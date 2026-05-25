#!/usr/bin/env python3
"""
Markdown Formatting Optimizer — IBM Carbon-inspired Design Rules.

Applies consistent formatting to generated wiki .md files:
  1. Collapse multiple blank lines → single blank line
  2. Strip trailing whitespace
  3. Exactly one blank line after frontmatter closing '---'
  4. Blank line before headings (h1-h6)
  5. Blank line before lists, tables, blockquotes, code fences, horizontal rules
  6. Consistent unordered list marker ('-')
  7. Ensure file ends with exactly one newline
  8. Remove BOM if present

The raw/ layer is source evidence and should normally keep its original text.
Use --target raw only for an intentional whitespace-only cleanup.

Usage:
  python format_markdown.py [--dry-run] [--target wiki]
"""

import os
import re
import argparse
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────
ROOT = str(Path(__file__).resolve().parents[1])
RAW_DIR = os.path.join(ROOT, "raw")
WIKI_DIR = os.path.join(ROOT, "wiki")

# ── Helpers ────────────────────────────────────────────────────

def is_heading_line(line: str) -> bool:
    """Check if a line starts with 1-6 '#' characters followed by a space."""
    return bool(re.match(r'^#{1,6}\s', line))

def is_list_line(line: str) -> bool:
    """Check if line starts a markdown list item."""
    return bool(re.match(r'^(\s*[-*+]\s|\s*\d+\.\s)', line))

def is_table_line(line: str) -> bool:
    """Check if line is part of a markdown table."""
    stripped = line.strip()
    return stripped.startswith('|') or bool(re.match(r'^[\s|:-]+$', stripped))

def is_blockquote_line(line: str) -> bool:
    return line.lstrip().startswith('>')

def is_code_fence_line(line: str) -> bool:
    return line.lstrip().startswith('```') or line.lstrip().startswith('~~~')

def is_horizontal_rule(line: str) -> bool:
    stripped = line.strip()
    return bool(re.match(r'^[-*_]{3,}\s*$', stripped))

def is_frontmatter_delim(line: str) -> bool:
    return line.strip() == '---'

def needs_blank_before(current_line: str, prev_line: str) -> bool:
    """
    Determine if we need a blank line before the current line,
    given the previous meaningful line.
    """
    if not prev_line:
        return False
    if not current_line.strip():
        return False  # current is blank, no extra blank needed here

    prev_is_blank = not prev_line.strip()
    prev_meaningful = prev_line if not prev_is_blank else ""

    # Headings always need blank line before (unless at very start)
    if is_heading_line(current_line):
        return not prev_is_blank

    # Lists need blank line before (unless preceded by another list item)
    if is_list_line(current_line):
        if prev_meaningful and is_list_line(prev_meaningful):
            return False
        return not prev_is_blank

    # Blockquotes
    if is_blockquote_line(current_line):
        if prev_meaningful and is_blockquote_line(prev_meaningful):
            return False
        return not prev_is_blank

    # Tables
    if is_table_line(current_line):
        if prev_meaningful and is_table_line(prev_meaningful):
            return False
        return not prev_is_blank

    # Code fences
    if is_code_fence_line(current_line):
        return not prev_is_blank

    # Horizontal rules
    if is_horizontal_rule(current_line):
        return not prev_is_blank

    return False


def format_content(content: str) -> tuple[str, int]:
    """
    Format markdown content. Returns (formatted_content, change_count).
    """
    changes = 0
    lines = content.split('\n')

    # ── Pass 1: Strip trailing whitespace ──
    new_lines = []
    for line in lines:
        stripped = line.rstrip()
        if stripped != line:
            changes += 1
        new_lines.append(stripped)
    lines = new_lines

    # ── Pass 2: Collapse multiple blank lines ──
    new_lines = []
    prev_blank = False
    for line in lines:
        is_blank = not line.strip()
        if is_blank and prev_blank:
            changes += 1
            continue
        new_lines.append(line)
        prev_blank = is_blank
    lines = new_lines

    # ── Pass 3: Insert blank lines before structural elements ──
    new_lines = []
    in_frontmatter = False
    frontmatter_closed = False
    frontmatter_end_idx = -1

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Track frontmatter
        if stripped == '---' and i == 0 and not in_frontmatter:
            in_frontmatter = True
            new_lines.append(line)
            continue
        if stripped == '---' and in_frontmatter:
            in_frontmatter = False
            frontmatter_closed = True
            frontmatter_end_idx = len(new_lines)
            new_lines.append(line)
            # Check if next line is blank; if so, skip duplicates; if not, add one
            continue

        # After frontmatter closed: ensure exactly one blank line
        if frontmatter_closed and len(new_lines) == frontmatter_end_idx + 1:
            # We're now at the first line after frontmatter closing
            if i == frontmatter_end_idx + 1:
                # This is the first content line after ---
                pass  # will be handled below
            frontmatter_closed = False  # handled

        # Skip blank line right after frontmatter if next is also blank
        # Actually, let's handle this differently...

    # REWRITE: simpler approach
    # Step 1: collapse blanks
    collapsed = []
    prev_empty = False
    for line in lines:
        empty = not line.strip()
        if empty and prev_empty:
            continue
        collapsed.append(line)
        prev_empty = empty

    # Step 2: ensure blank before headings, lists, tables, blockquotes, fences
    result = []
    in_fm = False
    fm_closed = False
    post_fm_blank_added = False
    prior_non_empty = None

    for i, line in enumerate(collapsed):
        stripped = line.strip()
        empty_line = not stripped

        # Track frontmatter
        if stripped == '---':
            if not in_fm and i == 0:
                in_fm = True
                result.append(line)
                prior_non_empty = line
                continue
            if in_fm:
                in_fm = False
                fm_closed = True
                result.append(line)
                prior_non_empty = line
                continue

        if empty_line:
            result.append(line)
            prior_non_empty = None
            continue

        # Not in frontmatter, not empty

        # After frontmatter just closed, ensure blank line
        if fm_closed and not post_fm_blank_added:
            fm_closed = False
            post_fm_blank_added = True
            if result and result[-1].strip() == '---':
                result.append('')
                prior_non_empty = None
            # else there's already a blank line

        # Check if we need blank line before this content line
        need_blank = False
        if result and result[-1].strip():
            # Previous line was non-empty
            if is_heading_line(line):
                need_blank = True
            elif is_list_line(line) and not (prior_non_empty and is_list_line(prior_non_empty)):
                need_blank = True
            elif is_blockquote_line(line) and not (prior_non_empty and is_blockquote_line(prior_non_empty)):
                need_blank = True
            elif is_table_line(line) and not (prior_non_empty and is_table_line(prior_non_empty)):
                need_blank = True
            elif is_code_fence_line(line):
                need_blank = True
            elif is_horizontal_rule(line):
                need_blank = True

        if need_blank:
            result.append('')
            changes += 1

        result.append(line)
        prior_non_empty = line

    # ── Pass 4: Normalize unordered list markers ──
    # Convert '* ' to '- ' for top-level lists
    # But don't touch content inside tables, code, or blockquotes
    final = []
    for line in result:
        if line.lstrip().startswith('* ') and not line.lstrip().startswith('* *'):
            # Only convert if it's a regular list item (not nested under blockquote/code)
            indent = len(line) - len(line.lstrip())
            final.append(indent * ' ' + '- ' + line.lstrip()[2:])
            if final[-1] != line:
                changes += 1
        else:
            final.append(line)

    # ── Pass 5: Ensure file ends with exactly one newline ──
    while final and final[-1] == '':
        final.pop()
        changes += 1
    final.append('')

    formatted = '\n'.join(final)

    # Check if anything actually changed (beyond our normalization)
    if formatted.rstrip('\n') == content.rstrip('\n'):
        # Check more carefully
        if formatted == content:
            changes = 0
        elif formatted.rstrip() == content.rstrip() and formatted.endswith('\n') and not content.endswith('\n'):
            changes = 1

    return formatted, changes


def process_file(filepath: str, dry_run: bool = False) -> bool:
    """Process a single markdown file. Returns True if changes were made."""
    try:
        # Read with utf-8, removing BOM
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            original = f.read()

        formatted, changes = format_content(original)

        if changes > 0:
            if not dry_run:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(formatted)
            relpath = os.path.relpath(filepath, ROOT)
            print(f"  {'[DRY RUN] ' if dry_run else ''}OK {relpath} ({changes} changes)")
            return True
        else:
            return False

    except Exception as e:
        relpath = os.path.relpath(filepath, ROOT)
        print(f"  ERROR processing {relpath}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Format markdown files in wiki/ and, if explicitly requested, raw/')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without writing')
    parser.add_argument('--target', choices=['raw', 'wiki', 'all'], default='wiki',
                        help='Which directory to process')
    args = parser.parse_args()

    targets = []
    if args.target in ('raw', 'all'):
        targets.append(RAW_DIR)
    if args.target in ('wiki', 'all'):
        targets.append(WIKI_DIR)

    total_files = 0
    total_changed = 0

    for target_dir in targets:
        if not os.path.isdir(target_dir):
            print(f"Directory not found: {target_dir}")
            continue

        print(f"\n{'='*60}")
        print(f"Processing: {os.path.relpath(target_dir, ROOT)}/")
        print(f"{'='*60}")

        md_files = []
        for root_dir, _, files in os.walk(target_dir):
            for f in files:
                if f.endswith('.md'):
                    md_files.append(os.path.join(root_dir, f))

        print(f"Found {len(md_files)} markdown files")

        changed = 0
        for fpath in sorted(md_files):
            total_files += 1
            if process_file(fpath, dry_run=args.dry_run):
                changed += 1
                total_changed += 1

        print(f"\nResult: {changed}/{len(md_files)} files changed in {os.path.relpath(target_dir, ROOT)}/")

    mode = "[DRY RUN] " if args.dry_run else ""
    print(f"\n{'='*60}")
    print(f"{mode}Total: {total_changed}/{total_files} files changed")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
