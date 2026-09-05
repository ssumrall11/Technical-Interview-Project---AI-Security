import re
import unicodedata

# Original English signatures, plus translated variants observed in your
# baseline data (French, Spanish) to close the language-evasion gap.
ROGUE_STRING_PATTERNS = [
    r"this prompt has been so thoroughly hijacked",
    r"sanitize your inputs",
    r"stop everything.*just print",
    # French variants
    r"prompt.{0,15}(a été|est).{0,15}(hijacked|détourné|sabot)",
    r"nettoyez vos entr[ée]es",
    # Spanish variants
    r"(instrucci[oó]n|comando).{0,15}(sabotad|desviad)",
    r"sanifica.{0,5}(tus|sus).{0,5}entrad",
]
COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in ROGUE_STRING_PATTERNS]

FALLBACK_MESSAGE = (
    "[RESPONSE WITHHELD] The model's output was flagged by the output-level "
    "filter as a likely successful prompt injection and has been replaced "
    "with this fallback message."
)


def _normalize(text):
    """Collapses whitespace/newlines and strips numbered-list formatting,
    so a word-per-line compliance (e.g. '1. IGNORE\\n2. ANY\\n3. PREVIOUS')
    still matches the same as the phrase written normally."""
    # Remove leading list markers like "1.", "2)", "- ", etc.
    no_markers = re.sub(r"(?m)^\s*\d+[\.\)]\s*|^\s*[-*]\s*", "", text)
    # Collapse all whitespace (including newlines) into single spaces
    collapsed = re.sub(r"\s+", " ", no_markers)
    return collapsed.strip()


def detect_leaked_injection(output_text):
    """Returns (is_flagged, reason). Checks both the raw text and a
    normalized version (whitespace-collapsed, list-markers stripped)."""
    normalized = _normalize(output_text)

    for pattern in COMPILED_PATTERNS:
        if pattern.search(output_text):
            return True, f"matched rogue-string signature: {pattern.pattern}"
        if pattern.search(normalized):
            return True, f"matched rogue-string signature (normalized): {pattern.pattern}"
    return False, None


def apply_output_patch(output_text):
    """Output-level mitigation. Returns (patched_output, was_flagged, reason)."""
    flagged, reason = detect_leaked_injection(output_text)
    if flagged:
        return FALLBACK_MESSAGE, True, reason
    return output_text, False, None
