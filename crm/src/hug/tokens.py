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


def is_valid_token(token: str) -> bool:
    """True if the string is a well-formed token (length + charset)."""
    return len(token) == TOKEN_LEN and all(c in _ALPHABET for c in token)
