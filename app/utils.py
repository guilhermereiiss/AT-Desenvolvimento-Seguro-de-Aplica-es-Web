from datetime import datetime, timezone


def utcnow() -> datetime:
    """UTC naive (banco guarda tudo em UTC sem tzinfo)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
