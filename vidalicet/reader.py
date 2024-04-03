from typing import Generator, List, Literal, Set, TextIO
import logging
from dataclasses import dataclass
from datetime import time
import sqlite3

from . import _bus, _db, _log_parsing, constants


logger = logging.getLogger(__name__)

type Phase = Literal["init"] | Literal["ecu_identification"] | Literal["parameters"]
type Parser = Generator[
    Phase,
    TextIO,
    None,
]


@dataclass
class IngestionStats:
    ecu_count: int = 0
    param_count: int = 0


class Reader:
    _parser: Parser
    _ecu_identifiers: Set[str]
    _param_messages_raw: List[_log_parsing.params.RawParamRxMsg]
    _con: sqlite3.Connection
    _message_matcher: _bus.matching.MessageMatcher | None
    _block_extractor: _bus.child_blocks.BlockExtractor | None

    last_ingestion_stats: IngestionStats | None
    log_files_ingested: int
    last_timestamp: time | None

    def __init__(self, db_path: str = constants.DEFAULT_DB_PATH) -> None:
        self._parser = self._create_parser()
        self._ecu_identifiers = set()
        self._param_messages_raw = []
        self._con = _db.connection.connect(db_path)
        self._message_matcher = None
        self._block_extractor = None

        self.last_ingestion_stats = None
        self.log_files_ingested = 0
        self.last_timestamp = None

        next(self._parser)

    def _assert_after_last_timestamp(self, timestamp: time, context: object) -> None:
        new, prev = timestamp, self.last_timestamp

        if prev is None:
            return

        if new < prev:
            raise ValueError(
                f"Log entry is older than last parsed entry. Did you ingest your log files in the correct order? Timestamps: {new} < {prev}. Context: '{context}'."
            )

    def _add_ecu_identifier(self, ecu_identifier: str, timestamp: time) -> None:
        self._assert_after_last_timestamp(timestamp, ecu_identifier)

        if ecu_identifier in self._ecu_identifiers:
            logger.warning(f"Duplicate ECU identifier found: '{ecu_identifier}'")
            return

        self._ecu_identifiers.add(ecu_identifier)
        assert self.last_ingestion_stats is not None
        self.last_ingestion_stats.ecu_count += 1
        self.last_timestamp = timestamp

    def _add_param_message(self, message: _log_parsing.params.RawParamRxMsg) -> None:
        self._assert_after_last_timestamp(message.time, message)

        self._param_messages_raw.append(message)
        assert self.last_ingestion_stats is not None
        self.last_ingestion_stats.param_count += 1
        self.last_timestamp = message.time

    def _create_parser(self) -> Parser:
        f = yield "init"

        ## ECU identification phase

        logger.debug("Entering ECU identification phase")

        ecu_parser = _log_parsing.ecu_id.parser()
        next(ecu_parser)
        ecu_parser.send(f)

        for response in ecu_parser:
            if response is None:
                f = yield "ecu_identification"
                ecu_parser.send(f)
                continue

            ecu_identifier, timestamp = response
            self._add_ecu_identifier(ecu_identifier, timestamp)

        logger.debug(
            f"ECU identification phase complete. Detected {len(self._ecu_identifiers)} unique ECUs: {self._ecu_identifiers}"
        )

        ## Parameter read phase

        logger.info("Reading parameter match data from db")
        match_data = _db.matching.get_parent_match_data(
            self._con, self._ecu_identifiers
        )
        logger.info("Preprocessing parameter match data")
        self._message_matcher = _bus.matching.MessageMatcher(match_data)
        self._block_extractor = _bus.child_blocks.BlockExtractor(self._con)

        logger.debug("Entering parameter read phase")
        param_parser = _log_parsing.params.parser()
        next(param_parser)
        param_parser.send(f)

        for message in param_parser:
            if message is None:
                f = yield "parameters"
                param_parser.send(f)
                continue
            self._add_param_message(message)

    def ingest_logfile(self, path: str) -> Phase:
        file_i = self.log_files_ingested

        logger.info(f"Ingesting log file #{file_i}: '{path}'")
        self.last_ingestion_stats = IngestionStats()
        with open(path, "r") as f:
            try:
                status = self._parser.send(f)
            except StopIteration:
                raise RuntimeError("Parser coroutine ended unexpectedly")

        self.log_files_ingested += 1

        ## Log ingestion outcome

        stats = self.last_ingestion_stats
        logger.info(
            f"Ingested {stats.ecu_count} ECU identifiers and {stats.param_count} parameter reads"
        )
        match status:
            case "init":
                raise RuntimeError("Ingested log file, but status is still '{status}'")
            case "ecu_identification":
                pass
            case "parameters":
                pass
        logger.info(f"Ingestion of log file #{file_i} completed: '{path}'")

        return status

    def get_new_params(self) -> list[_bus.common.ChildReading]:
        if not self._message_matcher or not self._block_extractor:
            return []

        logger.info(f"Iterating {len(self._param_messages_raw)} params.")

        readings = self._message_matcher.match(self._param_messages_raw)
        converted_readings = self._block_extractor.extract_children(readings)
        self._param_messages_raw.clear()
        return converted_readings
