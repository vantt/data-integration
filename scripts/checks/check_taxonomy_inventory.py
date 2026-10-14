"""Taxonomy inventory check (stdlib + PyYAML). Warns, never fails the build.

  python3 scripts/checks/check_taxonomy_inventory.py            # compare code with the inventory
  python3 scripts/checks/check_taxonomy_inventory.py --list     # print every CASE block that assigns a taxonomy column

Every classification rule that still lives in dbt SQL is recorded in
`taxonomy_inventory.yaml` (next to this file) with the sha256 of the block after
comments are removed and whitespace is collapsed. The human-readable spec is
transformation/docs/TAXONOMY.md; it quotes the same hashes.

WARN (exit code stays 0) when:
  changed   an inventoried block is no longer found in its file (its text changed)
  moved     an inventoried block is still present but its line changed (INFO only)
  new       a CASE ... END AS <taxonomy column> block exists that is not inventoried
  missing   an inventoried file does not exist

A block is either `case` (a CASE ... END [AS] alias block, found by hash) or `expr`
(an expression that is not a CASE, found by its normalized `snippet`).
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
INVENTORY = Path(__file__).resolve().parent / "taxonomy_inventory.yaml"
SCAN_DIRS = ("transformation/models", "transformation/macros")

_KEYWORDS = {
    "and", "or", "then", "else", "when", "end", "from", "where", "group", "order", "on",
    "join", "left", "right", "inner", "union", "having", "limit", "over", "is", "not",
    "in", "as", "using", "select", "case", "like", "ilike", "between", "desc", "asc",
}
_WORD = re.compile(r"[A-Za-z_]+")


@dataclass(frozen=True)
class Block:
    file: str
    line: int
    alias: str | None
    sha256: str


def _mask(sql: str) -> str:
    """Replace comments and string literals by spaces (same length) so keyword scans are safe."""
    out = list(sql)
    i, n = 0, len(sql)
    while i < n:
        two = sql[i:i + 2]
        if two == "--":
            j = sql.find("\n", i)
            j = n if j < 0 else j
        elif two == "/*":
            j = sql.find("*/", i + 2)
            j = n if j < 0 else j + 2
        elif sql[i] == "'":
            j = i + 1
            while j < n:
                if sql[j] == "'":
                    if sql[j + 1:j + 2] == "'":  # escaped quote
                        j += 2
                        continue
                    j += 1
                    break
                j += 1
        else:
            i += 1
            continue
        for k in range(i, j):
            if out[k] != "\n":
                out[k] = " "
        i = j
    return "".join(out)


def _strip_comments(sql: str) -> str:
    """Remove comments but keep string literals intact."""
    out, i, n = [], 0, len(sql)
    while i < n:
        two = sql[i:i + 2]
        if two == "--":
            j = sql.find("\n", i)
            i = n if j < 0 else j
        elif two == "/*":
            j = sql.find("*/", i + 2)
            i = n if j < 0 else j + 2
        elif sql[i] == "'":
            j = i + 1
            while j < n:
                if sql[j] == "'":
                    if sql[j + 1:j + 2] == "'":
                        j += 2
                        continue
                    j += 1
                    break
                j += 1
            out.append(sql[i:j])
            i = j
        else:
            out.append(sql[i])
            i += 1
    return "".join(out)


def normalize(sql: str) -> str:
    return " ".join(_strip_comments(sql).split())


def digest(sql: str) -> str:
    return hashlib.sha256(normalize(sql).encode("utf-8")).hexdigest()


def find_case_blocks(sql: str, rel: str) -> list[Block]:
    """Every top-level and nested CASE ... END block, with its alias when `END [AS] alias` follows."""
    masked = _mask(sql)
    tokens = [(m.group(0).lower(), m.start(), m.end()) for m in _WORD.finditer(masked)]
    stack: list[int] = []
    blocks: list[Block] = []
    for word, start, end in tokens:
        if word == "case":
            stack.append(start)
        elif word == "end" and stack:
            begin = stack.pop()
            alias = _alias_after(masked, end)
            blocks.append(Block(rel, sql.count("\n", 0, begin) + 1, alias, digest(sql[begin:end])))
    return blocks


def _alias_after(masked: str, pos: int) -> str | None:
    m = re.match(r"\s+(?:as\s+)?([A-Za-z_][A-Za-z_0-9]*)", masked[pos:pos + 200], re.IGNORECASE)
    if not m:
        return None
    word = m.group(1)
    return None if word.lower() in _KEYWORDS else word


def scan(repo: Path, columns: "Columns") -> list[Block]:
    found: list[Block] = []
    for d in SCAN_DIRS:
        for path in sorted((repo / d).rglob("*")):
            if path.suffix not in (".sql",) or not path.is_file():
                continue
            rel = path.relative_to(repo).as_posix()
            for b in find_case_blocks(path.read_text(encoding="utf-8"), rel):
                if b.alias and columns.covers(b.file, b.alias):
                    found.append(b)
    return found


def load_inventory(path: Path = INVENTORY) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@dataclass(frozen=True)
class Columns:
    """Taxonomy column names. `plain` match in every file; `scoped` is `(file name, column)`."""
    plain: frozenset[str]
    scoped: frozenset[tuple[str, str]]

    def covers(self, rel: str, alias: str) -> bool:
        a = alias.lower()
        return a in self.plain or (Path(rel).name, a) in self.scoped


def taxonomy_columns(inv: dict) -> Columns:
    """`columns` entries are `name` (any file) or `file.sql:name` (only that file name)."""
    plain: set[str] = set()
    scoped: set[tuple[str, str]] = set()
    for d in inv["domains"].values():
        for c in d.get("columns", []):
            if ":" in c:
                f, name = c.split(":", 1)
                scoped.add((f, name.lower()))
            else:
                plain.add(c.lower())
    return Columns(frozenset(plain), frozenset(scoped))


def check(repo: Path, inv: dict) -> tuple[list[str], list[str]]:
    """Return (warnings, infos)."""
    warns: list[str] = []
    infos: list[str] = []
    columns = taxonomy_columns(inv)
    found = scan(repo, columns)
    known_hashes: set[tuple[str, str]] = set()
    changed: set[tuple[str, str | None]] = set()
    cache: dict[str, str] = {}

    def text(rel: str) -> str | None:
        if rel not in cache:
            p = repo / rel
            cache[rel] = normalize(p.read_text(encoding="utf-8")) if p.is_file() else None  # type: ignore[assignment]
        return cache[rel]

    for dom, spec in inv["domains"].items():
        for blk in spec.get("blocks", []):
            rel, kind = blk["file"], blk.get("kind", "case")
            body = text(rel)
            if body is None:
                warns.append(f"WARN missing  [{dom}] {rel} no longer exists (inventoried block)")
                continue
            if kind == "case":
                known_hashes.add((rel, blk["sha256"]))
                hits = [b for b in found_in_file(repo, rel) if b.sha256 == blk["sha256"]]
                if not hits:
                    changed.add((rel, blk.get("alias")))
                    warns.append(f"WARN changed  [{dom}] {rel} block '{blk.get('alias')}' (was line {blk['line']}) "
                                 f"no longer matches sha256 {blk['sha256'][:12]}")
                elif blk["line"] not in {b.line for b in hits}:
                    infos.append(f"INFO moved    [{dom}] {rel} block '{blk.get('alias')}' now at line "
                                 f"{hits[0].line} (inventory says {blk['line']})")
            else:
                snippet = " ".join(blk["snippet"].split())
                if snippet not in body:
                    warns.append(f"WARN changed  [{dom}] {rel} expression '{blk.get('alias')}' (was line {blk['line']}) "
                                 f"no longer contains the inventoried snippet")
    for b in found:
        # a block whose text changed is already reported as "changed"; do not also call it new
        if (b.file, b.sha256) not in known_hashes and (b.file, b.alias) not in changed:
            warns.append(f"WARN new      {b.file}:{b.line} CASE assigns taxonomy column '{b.alias}' "
                         f"(sha256 {b.sha256[:12]}) and is not in taxonomy_inventory.yaml")
    return warns, infos


def found_in_file(repo: Path, rel: str) -> list[Block]:
    p = repo / rel
    return find_case_blocks(p.read_text(encoding="utf-8"), rel) if p.is_file() else []


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", type=Path, default=REPO, help="repository root (default: this checkout)")
    ap.add_argument("--inventory", type=Path, default=INVENTORY)
    ap.add_argument("--list", action="store_true", help="print CASE blocks that assign a taxonomy column")
    args = ap.parse_args(argv)
    inv = load_inventory(args.inventory)
    if args.list:
        for b in scan(args.repo, taxonomy_columns(inv)):
            print(f"{b.file}:{b.line}\t{b.alias}\t{b.sha256}")
        return 0
    warns, infos = check(args.repo, inv)
    for line in infos + warns:
        print(line)
    n_blocks = sum(len(d.get("blocks", [])) for d in inv["domains"].values())
    print(f"taxonomy inventory: {n_blocks} blocks, {len(inv['domains'])} domains, {len(warns)} warning(s)")
    return 0  # warn only: classification changes are allowed, they just must be deliberate


if __name__ == "__main__":
    sys.exit(main())
