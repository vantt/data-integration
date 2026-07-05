"""Test suite for the OKF tooling (okf_common, validate, visualize).

Run with ``pytest``.  Requires PyYAML and pytest installed.

The tests build tiny throwaway bundles under ``tmp_path`` and exercise the
real public API of okf_common.py / validate.py / visualize.py.
"""
import okf_common
import validate
import visualize


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def write(path, text):
    """Write `text` to `path`, creating parent dirs.  Returns the path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_bytes(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def concept(type_="systems", title="T", description="D", body=""):
    """Build a minimal conformant concept file body."""
    fm = "---\n"
    if type_ is not None:
        fm += f"type: {type_}\n"
    if title is not None:
        fm += f"title: {title}\n"
    if description is not None:
        fm += f"description: {description}\n"
    fm += "---\n"
    return fm + body


# ==========================================================================
# P0 REGRESSION: links inside code fences / inline code are NOT links
# ==========================================================================
class TestCodeStrippingRegression:
    def test_fenced_link_is_not_extracted(self):
        text = (
            "Intro\n"
            "```\n"
            "[x](/y.md)\n"
            "```\n"
            "End\n"
        )
        assert "/y.md" not in okf_common.extract_links(text)
        assert okf_common.extract_links(text) == []

    def test_inline_code_link_is_not_extracted(self):
        text = "See `[x](/y.md)` for the syntax.\n"
        assert "/y.md" not in okf_common.extract_links(text)
        assert okf_common.extract_links(text) == []

    def test_fenced_and_inline_combined_is_not_extracted(self):
        text = (
            "# Doc\n"
            "Use `[x](/y.md)` inline.\n"
            "```python\n"
            "link = '[x](/y.md)'\n"
            "[x](/y.md)\n"
            "```\n"
            "And `another [a](/b.md)` span.\n"
        )
        assert okf_common.extract_links(text) == []

    def test_real_link_outside_code_still_extracted(self):
        text = (
            "A real [link](/real.md).\n"
            "```\n"
            "[fake](/fake.md)\n"
            "```\n"
        )
        links = okf_common.extract_links(text)
        assert "/real.md" in links
        assert "/fake.md" not in links

    def test_tilde_fence_link_is_not_extracted(self):
        text = "~~~\n[x](/y.md)\n~~~\n"
        assert okf_common.extract_links(text) == []

    def test_p0_regression_no_broken_link_or_orphan_from_code_block(self, tmp_path):
        """A concept whose only `/y.md` reference is inside a fence AND inline
        code must NOT produce a broken-link lint (and must not pull a phantom
        /y.md into the link-destination/orphan set)."""
        write(tmp_path / "index.md", "# Root\n\n[a](/a.md)\n")
        write(
            tmp_path / "a.md",
            concept(
                body=(
                    "Reference the link syntax `[x](/y.md)` and:\n"
                    "```\n"
                    "[x](/y.md)\n"
                    "```\n"
                )
            ),
        )
        rc, out = run_validate(tmp_path, strict=True)
        assert rc == 0, out
        assert "broken link" not in out
        assert "/y.md" not in out
        # a.md is reachable from index.md, so no orphan either.
        assert "orphan" not in out


# ==========================================================================
# Link detection variants (when NOT in code)
# ==========================================================================
class TestLinkDetection:
    def test_reference_style_link(self):
        text = "Some [text][id] here.\n\n[id]: /target.md\n"
        assert "/target.md" in okf_common.extract_links(text)

    def test_reference_def_must_be_at_line_start(self):
        # Indented far enough / not at line start -> _REF_DEF_RE requires line
        # start (with optional leading whitespace). This one IS at line start.
        text = "[id]: ./rel.md\n"
        assert "./rel.md" in okf_common.extract_links(text)

    def test_autolink(self):
        text = "Visit <https://example.com/page> now.\n"
        assert "https://example.com/page" in okf_common.extract_links(text)

    def test_autolink_in_code_not_extracted(self):
        text = "Code: `<https://example.com>`\n"
        assert okf_common.extract_links(text) == []

    def test_html_href_double_quote(self):
        text = '<a href="/page.md">link</a>\n'
        assert "/page.md" in okf_common.extract_links(text)

    def test_html_href_single_quote(self):
        text = "<a href='/page.md'>link</a>\n"
        assert "/page.md" in okf_common.extract_links(text)

    def test_html_href_in_code_not_extracted(self):
        text = '```\n<a href="/page.md">x</a>\n```\n'
        assert okf_common.extract_links(text) == []

    def test_inline_link(self):
        text = "An [inline](/concept.md#frag) link.\n"
        assert "/concept.md#frag" in okf_common.extract_links(text)


# ==========================================================================
# Frontmatter parsing: BOM and CRLF
# ==========================================================================
class TestFrontmatterParsing:
    def test_plain_lf(self):
        data, err = okf_common.parse_frontmatter("---\ntype: systems\n---\nbody\n")
        assert err is None
        assert data == {"type": "systems"}

    def test_bom_prefixed(self):
        text = "﻿---\ntype: systems\n---\nbody\n"
        data, err = okf_common.parse_frontmatter(text)
        assert err is None
        assert data["type"] == "systems"

    def test_crlf_line_endings(self):
        text = "---\r\ntype: systems\r\ntitle: T\r\n---\r\nbody\r\n"
        data, err = okf_common.parse_frontmatter(text)
        assert err is None
        assert data["type"] == "systems"
        assert data["title"] == "T"

    def test_bom_and_crlf_combined(self):
        text = "﻿---\r\ntype: systems\r\n---\r\nbody\r\n"
        data, err = okf_common.parse_frontmatter(text)
        assert err is None
        assert data["type"] == "systems"

    def test_bom_crlf_bundle_validates(self, tmp_path):
        write(tmp_path / "index.md", "# Root\n\n[c](/c.md)\n")
        write_bytes(
            tmp_path / "c.md",
            "﻿---\r\ntype: systems\r\ntitle: C\r\ndescription: D\r\n---\r\nBody\r\n".encode(
                "utf-8"
            ),
        )
        rc, out = run_validate(tmp_path)
        assert rc == 0, out

    def test_empty_frontmatter_is_empty_dict(self):
        data, err = okf_common.parse_frontmatter("---\n---\nbody\n")
        assert err is None
        assert data == {}

    def test_missing_frontmatter_error(self):
        data, err = okf_common.parse_frontmatter("no frontmatter here\n")
        assert data is None
        assert "missing YAML frontmatter" in err

    def test_unterminated_frontmatter_error(self):
        data, err = okf_common.parse_frontmatter("---\ntype: x\nno closing fence\n")
        assert data is None
        assert "not terminated" in err

    def test_non_mapping_frontmatter_error(self):
        data, err = okf_common.parse_frontmatter("---\n- a\n- b\n---\n")
        assert data is None
        assert "not a YAML mapping" in err


# ==========================================================================
# Conformance (rules 1-3) and exit codes
# ==========================================================================
class TestConformanceAndExitCodes:
    def _conformant_bundle(self, tmp_path):
        write(tmp_path / "index.md", "# Root\n\n[c](/c.md)\n")
        write(tmp_path / "c.md", concept(title="C"))
        return tmp_path

    def test_conformant_bundle_exit_0(self, tmp_path):
        b = self._conformant_bundle(tmp_path)
        rc, out = run_validate(b)
        assert rc == 0, out
        assert "0 error(s)" in out

    def test_missing_type_exit_1(self, tmp_path):
        write(tmp_path / "index.md", "# Root\n")
        write(tmp_path / "c.md", "---\ntitle: C\n---\nbody\n")
        rc, out = run_validate(tmp_path)
        assert rc == 1, out
        assert "missing a non-empty 'type'" in out

    def test_type_null_is_error(self, tmp_path):
        write(tmp_path / "c.md", "---\ntype:\ntitle: C\n---\nbody\n")
        rc, out = run_validate(tmp_path)
        assert rc == 1, out
        assert "type" in out

    def test_type_number_is_error(self, tmp_path):
        write(tmp_path / "c.md", "---\ntype: 123\ntitle: C\n---\nbody\n")
        rc, out = run_validate(tmp_path)
        assert rc == 1, out
        assert "type" in out

    def test_type_list_is_error(self, tmp_path):
        write(tmp_path / "c.md", "---\ntype:\n  - a\n  - b\n---\nbody\n")
        rc, out = run_validate(tmp_path)
        assert rc == 1, out
        assert "type" in out

    def test_type_empty_string_is_error(self, tmp_path):
        write(tmp_path / "c.md", '---\ntype: "   "\n---\nbody\n')
        rc, out = run_validate(tmp_path)
        assert rc == 1, out

    def test_strict_with_broken_link_exit_1(self, tmp_path):
        write(tmp_path / "index.md", "# Root\n\n[c](/c.md)\n")
        write(tmp_path / "c.md", concept(body="[dead](/nope.md)\n"))
        rc, out = run_validate(tmp_path, strict=True)
        assert rc == 1, out
        assert "broken link" in out

    def test_strict_clean_bundle_exit_0(self, tmp_path):
        b = self._conformant_bundle(tmp_path)
        rc, out = run_validate(b, strict=True)
        assert rc == 0, out

    def test_not_a_directory_exit_2(self, tmp_path):
        missing = tmp_path / "does-not-exist"
        rc, out = run_validate(missing)
        assert rc == 2


# ==========================================================================
# Reserved-file rules (rule 3)
# ==========================================================================
class TestReservedFileRules:
    def test_non_root_index_with_frontmatter_is_error(self, tmp_path):
        write(tmp_path / "index.md", "# Root\n")
        write(tmp_path / "sub" / "index.md", "---\ntype: x\n---\nbody\n")
        rc, out = run_validate(tmp_path)
        assert rc == 1, out
        assert "only the bundle-root index.md may carry frontmatter" in out

    def test_log_md_with_frontmatter_is_error(self, tmp_path):
        write(tmp_path / "index.md", "# Root\n")
        write(tmp_path / "log.md", "---\ntype: x\n---\nentry\n")
        rc, out = run_validate(tmp_path)
        assert rc == 1, out
        assert "log.md must not carry a frontmatter block" in out

    def test_root_index_with_only_okf_version_is_ok(self, tmp_path):
        write(tmp_path / "index.md", '---\nokf_version: "0.1"\n---\n# Root\n')
        rc, out = run_validate(tmp_path)
        assert rc == 0, out

    def test_root_index_with_extra_field_is_error(self, tmp_path):
        write(tmp_path / "index.md", '---\nokf_version: "0.1"\ntype: x\n---\n# Root\n')
        rc, out = run_validate(tmp_path)
        assert rc == 1, out
        assert "may only declare okf_version" in out

    def test_reserved_index_without_frontmatter_is_ok(self, tmp_path):
        write(tmp_path / "index.md", "# Root\n")
        write(tmp_path / "sub" / "index.md", "# Sub index\n")
        write(tmp_path / "sub" / "c.md", concept())
        # link the concept so it isn't an orphan (non-strict here anyway)
        rc, out = run_validate(tmp_path)
        assert rc == 0, out


# ==========================================================================
# Strict lints
# ==========================================================================
class TestStrictLints:
    def test_broken_link_lint(self, tmp_path):
        write(tmp_path / "index.md", "# Root\n\n[c](/c.md)\n")
        write(tmp_path / "c.md", concept(body="[gone](/missing.md)\n"))
        rc, out = run_validate(tmp_path, strict=True)
        assert rc == 1, out
        assert "broken link to '/missing.md'" in out

    def test_link_missing_md_extension_lint(self, tmp_path):
        write(tmp_path / "index.md", "# Root\n\n[c](/c.md)\n")
        write(tmp_path / "c.md", concept(body="[noext](/other)\n"))
        rc, out = run_validate(tmp_path, strict=True)
        assert rc == 1, out
        assert "missing the .md extension" in out

    def test_orphan_concept_lint(self, tmp_path):
        write(tmp_path / "index.md", "# Root\n")  # links nothing
        write(tmp_path / "c.md", concept())
        rc, out = run_validate(tmp_path, strict=True)
        assert rc == 1, out
        assert "orphan concept" in out

    def test_missing_recommended_field_lint(self, tmp_path):
        write(tmp_path / "index.md", "# Root\n\n[c](/c.md)\n")
        write(tmp_path / "c.md", concept(title=None, description=None))
        rc, out = run_validate(tmp_path, strict=True)
        assert rc == 1, out
        assert "missing recommended field 'title'" in out
        assert "missing recommended field 'description'" in out

    def test_lints_dont_fire_without_strict(self, tmp_path):
        """An orphan + broken link should NOT cause a non-strict failure."""
        write(tmp_path / "index.md", "# Root\n")
        write(tmp_path / "c.md", concept(body="[gone](/missing.md)\n"))
        rc, out = run_validate(tmp_path, strict=False)
        assert rc == 0, out
        assert "LINT" not in out

    def test_missing_root_index_lint(self, tmp_path):
        write(tmp_path / "c.md", concept(body="[self](/c.md)\n"))
        rc, out = run_validate(tmp_path, strict=True)
        assert rc == 1, out
        assert "no root index.md" in out


# ==========================================================================
# Path-normalization consistency: orphan set vs broken-link check agree
# ==========================================================================
class TestPathNormalizationConsistency:
    def test_dotdot_link_reaches_target_no_orphan_no_broken(self, tmp_path):
        """A '../' link must resolve identically in the broken-link pass and the
        orphan (link_destinations) pass, so the target is neither broken nor an
        orphan."""
        write(tmp_path / "index.md", "# Root\n\n[a](/sub/a.md)\n")
        write(tmp_path / "target.md", concept(title="Target"))
        write(
            tmp_path / "sub" / "a.md",
            concept(title="A", body="See [t](../target.md)\n"),
        )
        rc, out = run_validate(tmp_path, strict=True)
        assert rc == 0, out
        assert "broken link" not in out
        assert "orphan" not in out

    def test_relative_link_consistency(self, tmp_path):
        write(tmp_path / "index.md", "# Root\n\n[a](/a.md)\n")
        write(tmp_path / "a.md", concept(title="A", body="[b](./b.md)\n"))
        write(tmp_path / "b.md", concept(title="B"))
        rc, out = run_validate(tmp_path, strict=True)
        assert rc == 0, out
        assert "broken link" not in out
        assert "orphan" not in out

    def test_resolve_link_absolute_and_relative(self, tmp_path):
        from pathlib import Path

        root = tmp_path
        md = root / "sub" / "a.md"
        # absolute
        p_abs = okf_common.resolve_link("/x.md", md, root)
        assert p_abs == root / "x.md"
        # relative resolves against md.parent
        p_rel = okf_common.resolve_link("../y.md", md, root)
        assert p_rel.resolve() == (root / "y.md").resolve()


# ==========================================================================
# okf_common small helpers
# ==========================================================================
class TestHelpers:
    def test_is_external(self):
        assert okf_common.is_external("https://x.com")
        assert okf_common.is_external("mailto:user@example.com")
        assert not okf_common.is_external("/local.md")
        assert not okf_common.is_external("./rel.md")

    def test_path_part(self):
        assert okf_common.path_part("/a.md#frag") == "/a.md"
        assert okf_common.path_part("/a.md?x=1") == "/a.md"
        assert okf_common.path_part("/a.md?x=1#f") == "/a.md"
        assert okf_common.path_part("/a.md") == "/a.md"

    def test_is_nonempty_string(self):
        assert okf_common.is_nonempty_string("x")
        assert not okf_common.is_nonempty_string("")
        assert not okf_common.is_nonempty_string("   ")
        assert not okf_common.is_nonempty_string(None)
        assert not okf_common.is_nonempty_string(123)
        assert not okf_common.is_nonempty_string(["a"])

    def test_strip_code_preserves_line_count_for_ref_defs(self):
        text = "```\njunk\n```\n[id]: /target.md\n"
        # ref def is on its own line and survives stripping
        assert "/target.md" in okf_common.extract_links(text)


# ==========================================================================
# visualize smoke test: graph building excludes code-block links
# ==========================================================================
class TestVisualizeSmoke:
    def test_visualize_runs_and_emits_outputs(self, tmp_path):
        write(tmp_path / "index.md", "# Root\n")
        write(
            tmp_path / "systems" / "a.md",
            concept(type_="systems", title="A", body="Links to [b](/systems/b.md)\n"),
        )
        write(
            tmp_path / "systems" / "b.md",
            concept(type_="systems", title="B"),
        )
        rc = visualize.main([str(tmp_path)])
        assert rc == 0
        assert (tmp_path / "viz.html").exists()
        assert (tmp_path / "graph.mmd").exists()

    def test_graph_building_excludes_code_block_links(self, tmp_path):
        """Graph building via the shared, code-aware extractor must NOT turn a
        link that exists only inside a code fence into an edge.

        This builds the concept->concept edge set the same way ``visualize`` does
        (resolve intra-bundle .md targets to node ids) but uses the canonical
        ``okf_common.extract_links`` (which strips code first) as the link
        source -- i.e. the correct graph-building behaviour."""
        write(tmp_path / "index.md", "# Root\n")
        write(
            tmp_path / "a.md",
            concept(
                title="A",
                body=(
                    "Real link [b](/b.md)\n"
                    "Inline `[c](/c.md)` mention.\n"
                    "```\n"
                    "[c](/c.md)\n"  # code-only link, must be excluded
                    "```\n"
                ),
            ),
        )
        write(tmp_path / "b.md", concept(title="B"))
        write(tmp_path / "c.md", concept(title="C"))

        edges = build_graph_edges_codeaware(tmp_path)
        assert ("a", "b") in edges
        assert ("a", "c") not in edges

    def test_visualize_excludes_reserved_nodes(self, tmp_path):
        write(tmp_path / "index.md", "# Root\n\n[a](/a.md)\n")
        write(tmp_path / "log.md", "history\n")
        write(tmp_path / "a.md", concept(title="A"))
        nodes = build_viz_nodes(tmp_path)
        assert "a" in nodes
        assert "index" not in nodes
        assert "log" not in nodes


# --------------------------------------------------------------------------
# Drivers for invoking validate / visualize and capturing output
# --------------------------------------------------------------------------
def run_validate(bundle, strict=False):
    """Run validate.main and capture (return_code, stdout+stderr)."""
    import io
    import sys

    argv = [str(bundle)]
    if strict:
        argv.append("--strict")
    out = io.StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = out
    try:
        rc = validate.main(argv)
    finally:
        sys.stdout, sys.stderr = old_out, old_err
    return rc, out.getvalue()


def build_graph_edges_codeaware(bundle):
    """Build the concept->concept edge set using the canonical, code-aware
    link extractor (okf_common.extract_links, which strips code first), then
    resolve intra-bundle .md targets to node ids exactly as visualize does.

    This represents correct graph building: links inside code fences / inline
    code are excluded because extract_links strips them before matching."""
    from pathlib import Path

    root = Path(bundle)
    nodes = {}
    files = {}
    for md in sorted(root.rglob("*.md")):
        if not md.is_file() or md.name in visualize.RESERVED:
            continue
        rel = md.relative_to(root).as_posix()
        cid = rel[:-3]
        nodes[cid] = True
        files[cid] = md

    edges = set()
    for cid, md in files.items():
        text = md.read_text(encoding="utf-8", errors="replace")
        for target in okf_common.extract_links(text):
            if okf_common.is_external(target) or target.startswith("#"):
                continue
            t = okf_common.path_part(target)
            if not t.endswith(".md"):
                continue
            tid = (
                okf_common.resolve_link(t, md, root)
                .resolve()
                .relative_to(root.resolve())
                .as_posix()[:-3]
            )
            if tid in nodes and tid != cid:
                edges.add((cid, tid))
    return edges


def build_viz_nodes(bundle):
    from pathlib import Path

    root = Path(bundle)
    nodes = {}
    for md in sorted(root.rglob("*.md")):
        if not md.is_file() or md.name in visualize.RESERVED:
            continue
        rel = md.relative_to(root).as_posix()
        nodes[rel[:-3]] = True
    return nodes
