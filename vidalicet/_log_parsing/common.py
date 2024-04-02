from dataclasses import dataclass
from datetime import time
import re


@dataclass(frozen=True)
class LogEntry:
    time: time
    message: str


m_log_entry = re.compile(r"(\d\d:\d\d:\d\d,\d\d\d) \[.*? *\]\[.*?\]\[.*? *\] +(.+)")


def parse_log_entry(line: str) -> LogEntry | None:
    match = m_log_entry.match(line)
    if not match:
        return None

    (timestamp, message) = match.groups()
    return LogEntry(
        time=time.fromisoformat(timestamp),
        message=message,
    )
