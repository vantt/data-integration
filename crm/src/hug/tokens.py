"""Token generation — random 12-char readable base32 (Crockford-style).

Per the locked spec the alphabet is "uppercase letters + digits, EXCLUDE
I, L, O, 0, 1" (visually ambiguous). Excluding those from {0-9, A-Z} leaves
exactly 31 symbols (digits 2-9 plus A-Z minus I, L, O). A 12-char token over
this set gives 31^12 ~= 7.8e17 — astronomically sparse, so guessing a live
token is impractical even before the edge rate-limit.

Tokens are opaque: meaning lives in the hug_token row, never in the string.
Uniqueness is enforced by a UNIQUE index in hug.db; the caller regenerates on
the rare collision.
"""
from __future__ import annotations

import re
import secrets

# 31 readable symbols: digits 2-9 and A-Z minus I, L, O.
_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"

TOKEN_LEN = 12


def generate_token() -> str:
    """Return a fresh random 12-char token from the readable base32 alphabet."""
    return "".join(secrets.choice(_ALPHABET) for _ in range(TOKEN_LEN))


def human_code(token: str) -> str:
    """Format a 12-char token as the printed fallback ``HUG-XXXX-XXXX-XXXX``."""
    if len(token) != TOKEN_LEN:
        chunks = [token[i : i + 4] for i in range(0, len(token), 4)]
        return "HUG-" + "-".join(chunks)
    return f"HUG-{token[0:4]}-{token[4:8]}-{token[8:12]}"


def grouped_code(token: str) -> str:
    """Format a token in dash-separated groups of 4, with NO prefix.

    e.g. ``7K2NQ9XRWAB4`` -> ``7K2N-Q9XR-WAB4``. This is the printed token line
    under the QR; the claim form strips the dashes on input, so the grouping is
    purely for human readability. Unlike ``human_code`` it carries no ``HUG-``.
    """
    if len(token) != TOKEN_LEN:
        return "-".join(token[i : i + 4] for i in range(0, len(token), 4))
    return f"{token[0:4]}-{token[4:8]}-{token[8:12]}"


def is_valid_token(token: str) -> bool:
    """True if the string is a well-formed token (length + charset)."""
    return len(token) == TOKEN_LEN and all(c in _ALPHABET for c in token)


def normalize_input(raw: str) -> str:
    """Convert any human or scanner input form into a bare 12-char token string.

    Accepted input forms:
      - Bare token:              ``7K2NQ9XRWAB4``
      - Printed human code:      ``HUG-7K2N-Q9XR-WAB4``  (also mixed-case / extra spaces)
      - Full scan URL:           ``https://hug.fjp.vn/h/7K2NQ9XRWAB4``
      - Any URL whose path ends with the token (last path segment)
      - Underscore or dot separators: ``7K2N_Q9XR_WAB4``, ``7K2N.Q9XR.WAB4``

    This function does NOT validate — the caller is expected to pass the result
    to ``is_valid_token``.

    Disambiguation for the ``HUG`` prefix edge case
    -----------------------------------------------
    The alphabet includes H, U, G, so a legitimate bare 12-char token can start
    with "HUG" (e.g. ``HUG234567892``).  Stripping "HUG" from such a token would
    corrupt it.

    We only strip a leading "HUG" when the de-dashed, de-spaced string is exactly
    15 characters long AND starts with "HUG".  15 = len("HUG") + TOKEN_LEN (12),
    which is the exact shape of the printed ``HUG-XXXX-XXXX-XXXX`` form after
    dashes are removed.  A genuine bare 12-char token is already 12 chars at that
    point and is returned as-is, regardless of whether it starts with "HUG".
    """
    s = raw.strip().upper()

    # If the input looks like a URL (contains "://"), extract the path's last
    # segment (everything after the last "/"), dropping query strings/fragments.
    if "://" in s:
        # e.g. "HTTPS://HUG.FJP.VN/H/7K2NQ9XRWAB4?foo=1#bar" → "7K2NQ9XRWAB4"
        path_part = s.split("?")[0].split("#")[0]  # strip query + fragment
        s = path_part.rstrip("/").rsplit("/", 1)[-1]

    # Remove all separator characters: dashes, underscores, dots, and whitespace.
    # Covers printed sticker (HUG-XXXX-XXXX-XXXX), manually typed codes using
    # _, . or spaces, and any mix a typist might reach for.
    s = re.sub(r"[-_.\s]", "", s)

    # Strip the "HUG" prefix only when the result is unmistakably the human_code
    # form (15 chars = "HUG" prefix + 12 token chars).  Never strip when the
    # string is already 12 chars — that would corrupt a token like HUG234567892.
    if len(s) == TOKEN_LEN + 3 and s.startswith("HUG"):
        s = s[3:]

    return s
