from typing import Any, Generator, Sequence, TextIO, Literal, NoReturn
import re
from datetime import time
from dataclasses import dataclass

from . import common


@dataclass(frozen=True)
class RawParamRxMsg:
    ecu_addr: str
    message: str
    time: time


m_request = re.compile(r".*VehComm request: Ecu '(.+?)'.*")
m_response = re.compile(r".*VehComm response: '(.+?)'.*")


def _parse_ecu_address_from_request(line: str) -> str | None:
    match = m_request.match(line)
    return match.group(1) if match else None


def _parse_ecu_message_from_response(line: str) -> str | None:
    match = m_response.match(line)
    return match.group(1) if match else None


def _message_group_parser(
    ecu_addr: str,
) -> Generator[RawParamRxMsg | None, TextIO, TextIO]:
    """
    Parse a single parameter read spanning one or more log files.

    ### Usage

    1. Wait until a parameter request line is found.
    2. Start with `.send(None)`.
    3. Send file with `.send(f)` (will yield `None`).
    4. Iterate until exhaustion:
        1. If `None` was yielded: EOF was reached. Send another file and continue.
        2. Else process yielded value.

    Will misbehave if the above conventions are not followed.
    """
    while True:
        f = yield
        yield

        for line in f:
            ecu_message = _parse_ecu_message_from_response(line)
            if ecu_message is None:
                continue

            entry = common.parse_log_entry(line)
            if not entry:
                break

            yield RawParamRxMsg(ecu_addr=ecu_addr, message=ecu_message, time=entry.time)
            break
        else:
            # EOF reached
            continue

        return f


def parser() -> Generator[RawParamRxMsg | None, TextIO, NoReturn]:
    """
    Parse parameter reads from one or more log files, forever.

    ### Usage

    1. Start with `.send(None)`.
    2. Send file with `.send(f)` (will yield `None`).
    3. Iterate until exhaustion:
        1. If `None` was yielded: EOF was reached. Send another file and continue (or don't).
        2. Else process yielded value.

    Will misbehave if the above conventions are not followed.
    """
    while True:
        f = yield
        yield

        while True:
            # Using while+readline instead of for-in because the file can change during the loop
            line = f.readline()
            if line == "":
                # EOF reached
                break

            ecu_addr = _parse_ecu_address_from_request(line)
            if ecu_addr is None:
                continue

            # Start line found: descent

            group_parser = _message_group_parser(ecu_addr)
            group_parser.send(None)
            group_parser.send(f)
            group_parser_f = yield from group_parser

            # If the file was changed in group_parser, bring it here.
            # We could parse the groups differently to avoid this, but then we'd have to
            # either discard any parameter reads that span two log files boundaries, or
            # to keep track of parser state explicitly.
            if f != group_parser_f:
                f = group_parser_f
                continue
