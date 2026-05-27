from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT / "wiki"
RAW = ROOT / "raw"


ARTICLE_RE = re.compile(r"(?m)^\s*(第[一二三四五六七八九十百千万零〇0-9]+条)(?!第[一二三四五六七八九十百千万零〇0-9]+款)\s*")
ENUM_RE = re.compile(r"[（(][一二三四五六七八九十百千万零〇0-9]+[）)]")
LIST_INTRO_WORDS = [
    "下列",
    "以下",
    "如下",
    "包括",
    "载明",
    "材料",
    "条件",
    "情形",
    "内容",
    "事项",
    "职权",
    "标准",
    "方式",
    "人员",
    "资料",
    "文件",
    "报告",
    "行为",
    "信息",
]


def split_wikilink(raw_target: str) -> tuple[str, str | None]:
    for idx, char in enumerate(raw_target):
        if char == "|":
            page = raw_target[:idx]
            if page.endswith("\\"):
                page = page[:-1]
            return page.strip(), raw_target[idx + 1 :].strip()
    return raw_target.strip(), None


def resolve_link(target: str) -> Path | None:
    target, _ = split_wikilink(target)
    target = target.split("#", 1)[0].strip()
    if not target or target.startswith(("http://", "https://", "mailto:")):
        return None
    if not target.endswith(".md"):
        target = f"{target}.md"
    return ROOT / Path(target.replace("/", "\\"))


def files_to_check() -> list[Path]:
    files = list(WIKI.rglob("*.md"))
    for name in ("index.md", "log.md"):
        file = ROOT / name
        if file.exists():
            files.append(file)
    return files


def resolve_link_with_anchor(raw_target: str) -> tuple[Path | None, str | None]:
    target, _ = split_wikilink(raw_target)
    if not target or target.startswith(("http://", "https://", "mailto:")):
        return None, None
    page, sep, anchor = target.partition("#")
    if not page:
        return None, anchor or None
    if not page.endswith(".md"):
        page = f"{page}.md"
    return ROOT / Path(page.replace("/", "\\")), anchor if sep else None


def heading_anchors(text: str) -> set[str]:
    anchors: set[str] = set()
    for match in re.finditer(r"(?m)^#{1,6}\s+(.+?)\s*$", text):
        anchors.add(match.group(1).strip())
    return anchors


def is_table_separator(line: str) -> bool:
    return bool(re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", line))


def split_table_cells(line: str, *, respect_wikilinks: bool) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return []
    inner = stripped[1:-1] if stripped.endswith("|") else stripped[1:]
    cells: list[str] = []
    current: list[str] = []
    in_wikilink = 0
    escaped = False
    i = 0
    while i < len(inner):
        char = inner[i]
        next_char = inner[i + 1] if i + 1 < len(inner) else ""
        if escaped:
            current.append(char)
            escaped = False
            i += 1
            continue
        if char == "\\":
            escaped = True
            i += 1
            continue
        if respect_wikilinks and char == "[" and next_char == "[":
            in_wikilink += 1
            current.extend((char, next_char))
            i += 2
            continue
        if respect_wikilinks and char == "]" and next_char == "]" and in_wikilink:
            in_wikilink -= 1
            current.extend((char, next_char))
            i += 2
            continue
        if char == "|" and not in_wikilink:
            cells.append("".join(current).strip())
            current = []
            i += 1
            continue
        current.append(char)
        i += 1
    cells.append("".join(current).strip())
    return cells


def find_table_issues(files: list[Path]) -> list[str]:
    placeholders = {"待填", "待检查"}
    issues: list[str] = []
    for file in files:
        text = file.read_text(encoding="utf-8")
        lines = text.splitlines()
        idx = 0
        while idx < len(lines) - 1:
            if not lines[idx].strip().startswith("|") or not is_table_separator(lines[idx + 1]):
                idx += 1
                continue

            rel = file.relative_to(ROOT)
            header = split_table_cells(lines[idx], respect_wikilinks=False)
            logical_header = split_table_cells(lines[idx], respect_wikilinks=True)
            width = len(header)

            if any(not cell for cell in header):
                issues.append(f"{rel}:{idx + 1} table_blank_header")
            if len(header) != len(logical_header):
                issues.append(f"{rel}:{idx + 1} table_unescaped_wikilink_pipe")

            row_idx = idx + 2
            while row_idx < len(lines) and lines[row_idx].strip().startswith("|"):
                raw_cells = split_table_cells(lines[row_idx], respect_wikilinks=False)
                logical_cells = split_table_cells(lines[row_idx], respect_wikilinks=True)
                if len(raw_cells) != len(logical_cells):
                    issues.append(f"{rel}:{row_idx + 1} table_unescaped_wikilink_pipe")
                if len(raw_cells) != width:
                    issues.append(f"{rel}:{row_idx + 1} table_width_mismatch")
                for cell in logical_cells:
                    if cell in placeholders:
                        issues.append(f"{rel}:{row_idx + 1} table_placeholder_cell={cell}")
                    if cell == "":
                        issues.append(f"{rel}:{row_idx + 1} table_blank_cell")
                row_idx += 1

            idx = row_idx
    return issues


def find_missing_anchors(files: list[Path]) -> list[tuple[Path, str]]:
    headings = {
        file: heading_anchors(file.read_text(encoding="utf-8", errors="ignore"))
        for file in files
    }
    missing: list[tuple[Path, str]] = []
    for file in files:
        text = file.read_text(encoding="utf-8", errors="ignore")
        for raw_target in re.findall(r"\[\[([^\]]+)\]\]", text):
            target, anchor = resolve_link_with_anchor(raw_target)
            if not target or not anchor or not target.exists():
                continue
            if anchor not in headings.get(target, set()):
                missing.append((file.relative_to(ROOT), raw_target))
    return missing


def find_topic_generic_warnings() -> list[tuple[Path, int]]:
    warnings: list[tuple[Path, int]] = []
    generic = re.compile(r"(?:涉及.{0,80}?等事项时|围绕.{0,80}?等事项)")
    for file in (WIKI / "专题").glob("*.md"):
        text = file.read_text(encoding="utf-8", errors="ignore")
        count = len(generic.findall(text))
        if count:
            warnings.append((file.relative_to(ROOT), count))
    return warnings


def split_articles(text: str) -> list[tuple[str, str]]:
    parts = ARTICLE_RE.split(text)
    articles: list[tuple[str, str]] = []
    if len(parts) < 3:
        return articles
    for i in range(1, len(parts), 2):
        clause = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""
        articles.append((clause, body))
    return articles


def sections_by_clause(page_text: str) -> dict[str, list[str]]:
    heading = re.compile(r"^###\s+(?:E\d+[:：])?(第[一二三四五六七八九十百千万零〇0-9]+条|段落\d+)\s*$", re.M)
    matches = list(heading.finditer(page_text))
    sections: dict[str, list[str]] = {}
    for idx, match in enumerate(matches):
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(page_text)
        sections.setdefault(match.group(1), []).append(page_text[match.start() : end])
    return sections


def enum_count(text: str) -> int:
    markers = {m.group(0) for m in ENUM_RE.finditer(text)}
    markers.discard("(0)")
    markers.discard("（0）")
    return len(markers)


def looks_like_numbered_list(text: str, first_marker_start: int) -> bool:
    prefix = text[max(0, first_marker_start - 120) : first_marker_start]
    if re.search(r"第\s*$", prefix):
        return False
    return any(word in prefix for word in LIST_INTRO_WORDS)


def list_item_count(text: str) -> int:
    normalized = re.sub(r"\s+", " ", text).strip()
    matches = list(ENUM_RE.finditer(normalized))
    if len(matches) < 2:
        return 0
    if not looks_like_numbered_list(normalized, matches[0].start()):
        return 0
    return enum_count(normalized)


def find_enumeration_losses() -> list[str]:
    losses: list[str] = []
    for raw_file in RAW.rglob("*.md"):
        source_page = WIKI / "来源" / raw_file.parent.name / raw_file.name
        if not source_page.exists():
            continue
        raw_text = raw_file.read_text(encoding="utf-8", errors="ignore").replace("javascript:void(0);", "")
        raw_articles = split_articles(raw_text)
        page_text = source_page.read_text(encoding="utf-8")
        page_sections = sections_by_clause(page_text)
        raw_counts_by_clause: dict[str, list[int]] = {}
        for clause, body in raw_articles:
            raw_count = list_item_count(body)
            if raw_count < 3:
                continue
            raw_counts_by_clause.setdefault(clause, []).append(raw_count)

        for clause, raw_counts in raw_counts_by_clause.items():
            sections = page_sections.get(clause, [])
            if not sections:
                continue
            page_counts = sorted((enum_count(section) for section in sections), reverse=True)
            for idx, raw_enum_count in enumerate(sorted(raw_counts, reverse=True)):
                page_enum_count = page_counts[idx] if idx < len(page_counts) else 0
                if page_enum_count >= raw_enum_count:
                    continue
                rel = raw_file.relative_to(ROOT).as_posix()
                losses.append(f"{rel} {clause}: raw={raw_enum_count}, wiki={page_enum_count}")
    return losses


def main() -> int:
    broken: list[tuple[Path, str]] = []
    line_refs: list[Path] = []
    links = 0
    checked_files = files_to_check()
    for file in checked_files:
        text = file.read_text(encoding="utf-8")
        if re.search(r"\bline\s+\d+\b", text, re.I):
            line_refs.append(file.relative_to(ROOT))
        for raw_target in re.findall(r"\[\[([^\]]+)\]\]", text):
            links += 1
            target = resolve_link(raw_target)
            if target is not None and not target.exists():
                broken.append((file.relative_to(ROOT), raw_target))

    raw_count = sum(1 for _ in RAW.rglob("*.md"))
    source_count = sum(1 for _ in (WIKI / "来源").rglob("*.md"))
    wiki_count = sum(1 for _ in WIKI.rglob("*.md"))

    chairman = WIKI / "专题" / "董事长职责监管规定汇总.md"
    chairman_text = chairman.read_text(encoding="utf-8")
    weak_needles = ["保险公估", "本办法自公布之日起施行", "签署的申请书", "首席代表授权书"]
    weak_hits = [needle for needle in weak_needles if needle in chairman_text]
    enumeration_losses = find_enumeration_losses()
    missing_anchors = find_missing_anchors(checked_files)
    generic_topic_warnings = find_topic_generic_warnings()
    table_issues = find_table_issues(checked_files)

    print(f"raw_count={raw_count}")
    print(f"source_page_count={source_count}")
    print(f"wiki_file_count={wiki_count}")
    print(f"wikilink_count={links}")
    print(f"broken_link_count={len(broken)}")
    print(f"missing_anchor_count={len(missing_anchors)}")
    print(f"line_reference_count={len(line_refs)}")
    print(f"table_issue_count={len(table_issues)}")
    print(f"chairman_weak_hit_count={len(weak_hits)}")
    print(f"enumeration_loss_count={len(enumeration_losses)}")
    print(f"topic_generic_warning_page_count={len(generic_topic_warnings)}")
    if weak_hits:
        print("chairman_weak_hits=" + ", ".join(weak_hits))
    if raw_count != source_count:
        print("source coverage mismatch")
        return 1
    if broken:
        for file, target in broken[:20]:
            print(f"broken: {file} -> {target}")
        return 1
    if missing_anchors:
        for file, target in missing_anchors[:20]:
            print(f"missing_anchor: {file} -> {target}")
        return 1
    if line_refs:
        for file in line_refs[:20]:
            print(f"line_reference: {file}")
        return 1
    if table_issues:
        for issue in table_issues[:20]:
            print(f"table_issue: {issue}")
        return 1
    if weak_hits:
        return 1
    if enumeration_losses:
        for loss in enumeration_losses[:20]:
            print(f"enumeration_loss: {loss}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
