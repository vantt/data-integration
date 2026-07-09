"""test_card_macros.py — unit tests for templates/macros/*.html.

Covers: card(), facts(), card_header(), count_pill() — the shared macro layer built
during the card/badge consolidation (plans/260709-1034-card-badge-macro-consolidation).
None of these macros call custom Jinja filters internally, so a bare Environment
(FileSystemLoader only, no filter registry) is sufficient — unlike
test_web_templating.py's full production-filter setup, which these don't need.

Regression guards specifically encoded here:
  - card()'s `attrs` renders unescaped (|safe) — a caller-escaping contract, not a bug,
    but worth pinning so a future edit doesn't accidentally auto-escape it and break
    tasks_board.html's id/draggable pass-through.
  - card()'s `variant` + `extra_class` can compose (the recipient+lead case in
    order_operations_tab.html) — both land in the class attribute together.
  - facts() renders plain-text values through normal autoescaping (embedded HTML in a
    fact value must NOT come out unescaped — that's the whole reason mixed-markup fact
    blocks were deliberately left hand-written instead of forced through this macro).
  - count_pill() has NO fallback for an unknown variant — it silently renders whatever
    class name it's given; this test pins that behavior so it's a documented contract,
    not a surprise (see macros/count_pill.html's docstring for the same warning).
"""
from __future__ import annotations

import pathlib
import sys

import jinja2

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_TEMPLATES_DIR = str(
    pathlib.Path(__file__).parents[1] / "adapters" / "inbound" / "web" / "templates"
)


def _env() -> jinja2.Environment:
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(_TEMPLATES_DIR), autoescape=True
    )


def _render(src: str, **ctx) -> str:
    return _env().from_string(src).render(**ctx)


class TestCard:
    def test_bare_card_is_plain_scard(self):
        out = _render(
            '{% from "macros/card.html" import card %}'
            "{% call card() %}body{% endcall %}"
        )
        assert '<div class="scard">' in out
        assert "body" in out

    def test_eyebrow_and_accent(self):
        out = _render(
            '{% from "macros/card.html" import card %}'
            '{% call card(eyebrow="Headline", eyebrow_accent=true) %}x{% endcall %}'
        )
        assert 'class="caption caption--accent scard__eyebrow">Headline' in out

    def test_eyebrow_without_accent_omits_class(self):
        out = _render(
            '{% from "macros/card.html" import card %}'
            '{% call card(eyebrow="Plain") %}x{% endcall %}'
        )
        assert 'class="caption scard__eyebrow">Plain' in out
        assert "caption--accent" not in out

    def test_tag_and_tag_variant(self):
        out = _render(
            '{% from "macros/card.html" import card %}'
            '{% call card(tag="GIỮ LẠI", tag_variant="accent") %}x{% endcall %}'
        )
        assert 'class="scard__tag bdg bdg--accent">GIỮ LẠI' in out

    def test_tag_without_variant(self):
        out = _render(
            '{% from "macros/card.html" import card %}'
            '{% call card(tag="GỘP VÀO") %}x{% endcall %}'
        )
        assert 'class="scard__tag bdg">GỘP VÀO' in out

    def test_variant_alone(self):
        out = _render(
            '{% from "macros/card.html" import card %}'
            '{% call card(variant="survive") %}x{% endcall %}'
        )
        assert '<div class="scard scard--survive">' in out

    def test_variant_and_extra_class_compose(self):
        # The order_operations_tab.html Recipient card case: two simultaneous
        # modifier classes (scard--recipient scard--lead) reproduced via
        # variant + extra_class.
        out = _render(
            '{% from "macros/card.html" import card %}'
            '{% call card(variant="recipient", extra_class="scard--lead") %}x{% endcall %}'
        )
        assert '<div class="scard scard--recipient scard--lead">' in out

    def test_attrs_render_unescaped(self):
        out = _render(
            '{% from "macros/card.html" import card %}'
            '{% call card(attrs=\'id="task-card-1" draggable="true"\') %}x{% endcall %}'
        )
        assert '<div class="scard" id="task-card-1" draggable="true">' in out

    def test_no_attrs_no_trailing_space(self):
        out = _render(
            '{% from "macros/card.html" import card %}'
            "{% call card() %}x{% endcall %}"
        )
        assert '<div class="scard">' in out  # no stray space before '>'

    def test_no_type_or_kind_param_exists(self):
        # Design invariant: card() must never grow a type/kind dispatch param — every
        # caller supplies its own content via {% call %}. This test just documents
        # that calling with an unexpected kwarg fails loudly (macro has no **kwargs).
        import jinja2.exceptions

        try:
            _render(
                '{% from "macros/card.html" import card %}'
                '{% call card(kind="whatever") %}x{% endcall %}'
            )
            raised = False
        except jinja2.exceptions.TemplateSyntaxError:
            raised = True
        except Exception:
            raised = True
        assert raised


class TestFacts:
    def test_simple_list(self):
        out = _render(
            '{% from "macros/facts.html" import facts %}'
            "{{ facts([{'k': 'ID', 'v': 'abc123'}]) }}"
        )
        assert 'class="fact__k">ID' in out
        assert 'class="fact__v">abc123' in out
        assert "mono" not in out

    def test_mono_flag(self):
        out = _render(
            '{% from "macros/facts.html" import facts %}'
            "{{ facts([{'k': 'ID', 'v': 'abc123', 'mono': true}]) }}"
        )
        assert 'class="fact__v mono">abc123' in out

    def test_multiple_items_preserve_order(self):
        out = _render(
            '{% from "macros/facts.html" import facts %}'
            "{{ facts([{'k': 'A', 'v': '1'}, {'k': 'B', 'v': '2'}]) }}"
        )
        assert out.index(">A<") < out.index(">B<")

    def test_embedded_html_in_value_is_escaped(self):
        # This is the exact reason mixed-markup fact blocks stay hand-written:
        # facts() must NOT let a value's markup through unescaped.
        out = _render(
            '{% from "macros/facts.html" import facts %}'
            "{{ facts([{'k': 'X', 'v': '<b>bold</b>'}]) }}"
        )
        assert "<b>bold</b>" not in out
        assert "&lt;b&gt;bold&lt;/b&gt;" in out

    def test_empty_list_renders_empty_wrapper(self):
        out = _render(
            '{% from "macros/facts.html" import facts %}' "{{ facts([]) }}"
        )
        assert '<div class="facts">' in out
        assert "fact__k" not in out


class TestCardHeader:
    def test_with_edit_href(self):
        out = _render(
            '{% from "macros/card_header.html" import card_header %}'
            '{{ card_header("Liên Lạc", edit_href="/modals/m15?party_id=1") }}'
        )
        assert 'class="caption">Liên Lạc' in out
        assert 'hx-get="/modals/m15?party_id=1"' in out
        assert "Sửa" in out

    def test_title_only_omits_button(self):
        out = _render(
            '{% from "macros/card_header.html" import card_header %}'
            '{{ card_header("Dates") }}'
        )
        assert 'class="row-between"' in out
        assert 'class="caption">Dates' in out
        assert "Sửa" not in out
        assert "hx-get" not in out


class TestCountPill:
    def test_known_variant_band(self):
        out = _render(
            '{% from "macros/count_pill.html" import count_pill %}'
            '{{ count_pill(17, "band") }}'
        )
        assert '<span class="cpill cpill--band">17</span>' == out.strip()

    def test_known_variant_ship(self):
        out = _render(
            '{% from "macros/count_pill.html" import count_pill %}'
            '{{ count_pill(7, "ship") }}'
        )
        assert '<span class="cpill cpill--ship">7</span>' == out.strip()

    def test_known_variant_session_with_text_suffix(self):
        out = _render(
            '{% from "macros/count_pill.html" import count_pill %}'
            '{{ count_pill(6 ~ " việc", "session") }}'
        )
        assert '<span class="cpill cpill--session">6 việc</span>' == out.strip()

    def test_unknown_variant_has_no_fallback(self):
        # Documented contract (macros/count_pill.html docstring): an undefined variant
        # silently renders with only the bare .cpill shell - no error, no default
        # styling. This test pins that it does NOT raise and does NOT special-case.
        out = _render(
            '{% from "macros/count_pill.html" import count_pill %}'
            '{{ count_pill(1, "made-up-variant") }}'
        )
        assert '<span class="cpill cpill--made-up-variant">1</span>' == out.strip()
