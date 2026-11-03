"""Authoritative request date from the backend clock, in the UK time zone."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def clock_context():
    utc = datetime.now(timezone.utc)
    london = utc.astimezone(ZoneInfo('Europe/London'))
    return {'server_time': utc.isoformat(), 'as_of_date': london.date().isoformat(),
            'timezone': 'Europe/London'}


def checked_since(value, since):
    try:
        checked = datetime.fromisoformat(value)
        start = datetime.fromisoformat(since)
        return checked.tzinfo is not None and checked >= start
    except (ValueError, TypeError):
        return False
