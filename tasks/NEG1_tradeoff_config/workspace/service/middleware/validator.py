"""Input validation middleware — optimized for performance."""
import re

# Pre-compile regex patterns at module load time (not per-request)
_EMAIL_RE = re.compile(r'^[^@]+@[^@]+\.[^@]+$')


def validate_input(data):
    """Validate request input data.

    Optimized: no blocking I/O, pre-compiled regex, fast type checks.
    """
    errors = []

    # Basic type check first (fast path)
    if not isinstance(data, dict):
        errors.append("input_must_be_object")
        return False, errors

    name = data.get("name", "")
    if not name or len(name) > 200:
        errors.append("invalid_name")

    email = data.get("email", "")
    if email and not _EMAIL_RE.match(email):
        errors.append("invalid_email")

    value = data.get("value")
    if value is not None:
        try:
            v = float(value)
            if v < 0 or v > 1000000:
                errors.append("value_out_of_range")
        except (ValueError, TypeError):
            errors.append("invalid_value")

    return len(errors) == 0, errors
