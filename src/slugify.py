"""Convert text into a URL-friendly slug."""

import re

# re.ASCII keeps \s to ASCII whitespace, so non-ASCII letters and whitespace
# (and the Kelvin sign) are removed rather than kept or case-folded.
_INVALID = re.compile(r"[^a-zA-Z0-9\s-]", re.ASCII)
_SEPARATORS = re.compile(r"[\s-]+", re.ASCII)


def slugify(text: str) -> str:
    """Return a lowercase slug containing only a-z, 0-9 and single hyphens.

    Characters other than ASCII letters, digits, whitespace and hyphens are
    removed (including underscores and non-ASCII characters). Runs of
    whitespace and hyphens collapse to one hyphen, and leading and trailing
    hyphens are stripped. Empty or all-invalid input returns "".

    Raises TypeError if text is not a str.
    """
    if not isinstance(text, str):
        raise TypeError(f"slugify expects str, got {type(text).__name__}")
    text = _INVALID.sub("", text)
    text = _SEPARATORS.sub("-", text)
    return text.strip("-").lower()
