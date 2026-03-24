"""Structured audit logging for security-relevant events."""
import hashlib
import json
import logging
import sys
import time

import streamlit as st

audit_logger = logging.getLogger("audit")

# Configure handler once at import time — idempotent if already set up
if not audit_logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter("%(message)s"))
    audit_logger.addHandler(_handler)
    audit_logger.setLevel(logging.INFO)
    audit_logger.propagate = False


def _session_id() -> str:
    """Stable, anonymous per-session identifier (not reversible to user identity)."""
    raw = str(id(st.session_state))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def log_event(event_type: str, **kwargs) -> None:
    """Emit a structured JSON audit event.

    Args:
        event_type: Short identifier for the event (e.g. "file_accepted").
        **kwargs:   Additional fields to include in the log entry.
    """
    entry = {
        "event": event_type,
        "ts": time.time(),
        "session": _session_id(),
        **kwargs,
    }
    audit_logger.info(json.dumps(entry))
