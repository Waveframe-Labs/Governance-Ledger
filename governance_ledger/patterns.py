"""Regex patterns for deterministic governance constraint extraction."""

ROLE_PATTERNS = [
    r"\bonly\s+(?P<role>[a-z][a-z_-]*)\s+may\b",
    r"\brequires?\s+(?!(?:reasonable|appropriate|relevant|responsible)\s+)(?P<role>[a-z][a-z_-]*?)\s+approval\b",
]

SEPARATION_PATTERNS = [
    r"\bmust\s+be\s+separate\b",
    r"\bseparation\s+of\s+duties\b",
]

EXPLICIT_ROLE_THRESHOLD_PATTERNS = [
    r"\b(?:transfers?|purchases?|payments?|invoices?|requests?)\s+(?P<source>(?P<operator_phrase>above|over|greater\s+than|exceeding|at\s+least|up\s+to|below|under|less\s+than)\s+\$?(?P<amount>\d[\d,]*(?:\.\d+)?)\s*(?P<suffix>k|m|thousand|million)?)\b\s+requires?\s+(?P<requires_role>[a-z][a-z_-]*)\s+approval\b",
]

MISSING_ROLE_THRESHOLD_PATTERNS = [
    r"\b(?:transfers?|purchases?|payments?|invoices?|requests?)\s+(?P<source>(?P<operator_phrase>above|over|greater\s+than|exceeding|at\s+least|up\s+to|below|under|less\s+than)\s+\$?(?P<amount>\d[\d,]*(?:\.\d+)?)\s*(?P<suffix>k|m|thousand|million)?)\b\s+requires?\s+approval\b",
]

THRESHOLD_PATTERNS = [
    *EXPLICIT_ROLE_THRESHOLD_PATTERNS,
    *MISSING_ROLE_THRESHOLD_PATTERNS,
]

AMBIGUOUS_AUTHORITY_PATTERNS = [
    r"\bappropriate\s+manager\b",
    r"\brelevant\s+manager\b",
    r"\bresponsible\s+manager\b",
    r"\bsenior\s+reviewer\b",
    r"\bdesignated\s+owner\b",
]

AMBIGUOUS_THRESHOLD_PATTERNS = [
    r"\blarge\s+transfers?\b",
    r"\bmaterial\s+transfers?\b",
    r"\bsignificant\s+transfers?\b",
]

AMBIGUOUS_TEMPORAL_PATTERNS = [
    r"\breasonable\s+approval\s+timing\b",
    r"\breasonable\s+time(?:frame)?\b",
    r"\bas\s+soon\s+as\s+practicable\b",
    r"\bpromptly\b",
    r"\bin\s+a\s+timely\s+manner\b",
]

AMBIGUOUS_RISK_PATTERNS = [
    r"\bhigh\s+risk\b",
    r"\brisky\b",
    r"\belevated\s+risk\b",
]

AMBIGUOUS_PROCESS_PATTERNS = [
    r"\bappropriate\s+approval\b",
    r"\brelevant\s+approval\b",
    r"\badequate\s+approval\b",
]

UNSUPPORTED_CONSTRAINT_PATTERNS = [
    r"\bmulti-party\s+quorum\b",
    r"\bquorum\b",
    r"\bwithin\s+\d+\s+(?:minutes?|hours?|days?)\b",
    r"\bretain(?:ed)?\s+for\s+\d+\s+(?:days?|months?|years?)\b",
]

GOVERNANCE_SIGNAL_PATTERN = (
    r"\b(approval|approve|authority|must|only|require|requires|required|shall|should|transfer|transfers|risk|reviewer)\b"
)
