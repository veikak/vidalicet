from typing import Generator, TextIO, Tuple
import re
from datetime import time

from . import common

m_ecu_id_phase_start_line = re.compile(r".*> PerformEcuIdentification <.*")
m_ecu_id_phase_end_line = re.compile(r".*> PerformCarConfigReadout <.*")
m_get_ecu_id = re.compile(r"^.*?SP: general_GetEcuId, EcuId: (.+?), Result: .*$")


def _lines_until_start(f: TextIO):
    for line in f:
        result = m_ecu_id_phase_start_line.match(line)
        if result is not None:
            yield line
            return
        yield line
    else:
        yield None


def _lines_until_end(f: TextIO):
    for line in f:
        result = m_ecu_id_phase_end_line.match(line)
        if result is not None:
            yield line
            return
        yield line
    else:
        yield None


def _parse_ecu_identifier(line: str) -> str | None:
    match = m_get_ecu_id.match(line)
    return match and match.group(1)


def parser() -> Generator[Tuple[str, time] | None, TextIO, None]:
    """
    Parse ECU identifiers from one or more log files until end of ECU id phase has been reached.

    Yields `(ecu_identifier, timestamp)`, or `None` if EOF was reached. When iteration stops, parsing has concluded.

    ### Usage

    1. Start with `.send(None)`.
    2. Send file with `.send(f)` (will yield `None`).
    3. Iterate until exhaustion:
        1. If `None` was yielded: EOF was reached before end of ECU identification phase.
        Send another file and continue.
        2. Else process yielded value.

    Will misbehave if the above conventions are not followed.
    """
    start_reached = False

    while True:
        f = yield
        yield

        if not start_reached:
            for line in _lines_until_start(f):
                if line is None:
                    # EOF reached
                    break
            else:
                start_reached = True

        if not start_reached:
            continue

        for line in _lines_until_end(f):
            if line is None:
                break

            entry = common.parse_log_entry(line)
            if not entry:
                continue

            ecu_identifier = _parse_ecu_identifier(entry.message)
            if ecu_identifier is not None:
                yield ecu_identifier, entry.time
        else:
            return
