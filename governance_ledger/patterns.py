"""Regex patterns for deterministic governance constraint extraction."""

ROLE_PATTERNS = [
    r"\bonly\s+(?P<role>[a-z][a-z_-]*)\s+may\b",
    r"\brequires?\s+(?!(?:reasonable|appropriate|relevant|responsible)\s+)(?P<role>[a-z][a-z_-]*?)\s+approval\b",
]

SEPARATION_PATTERNS = [
    r"\bmust\s+be\s+separate\b",
    r"\bseparation\s+of\s+duties\b",
]

THRESHOLD_PATTERNS = [
    r"\btransfers?\s+(?P<source>above\s+\$?(?P<amount>\d[\d,]*(?:\.\d+)?)\s*(?P<suffix>m|million)?)\b\s+requires?\s+(?:[a-z][a-z_-]*\s+)?approval\b",
]

AMBIGUOUS_AUTHORITY_PATTERNS = [
    r"\bappropriate\s+manager\b",
    r"\brelevant\s+manager\b",
    r"\bresponsible\s+manager\b",
]

UNSUPPORTED_CONSTRAINT_PATTERNS = [
    r"\breasonable\s+approval\s+timing\b",
    r"\breasonable\s+time(?:frame)?\b",
    r"\bas\s+soon\s+as\s+practicable\b",
]

GOVERNANCE_SIGNAL_PATTERN = (
    r"\b(approval|approve|authority|must|only|require|requires|required|shall)\b"
)
