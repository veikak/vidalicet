import os.path
import logging
import vidalicet.reader

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s][%(levelname)s][%(name)s] %(message)s",
)

logger = logging.getLogger(__name__)

log_dir = "data/vida_logs"
log_filenames = [
    "S60 (11-)_2011_xxxxxx.log0.pre-eid",
    "S60 (11-)_2011_xxxxxx.log0.pre-eid-rest",
    "S60 (11-)_2011_xxxxxx.log",
]
log_paths = [os.path.join(log_dir, filename) for filename in log_filenames]

reader = vidalicet.reader.Reader("vidalicet.sqlite3")

for path in log_paths:
    reader.ingest_logfile(path)
    logger.info(f"Last timestamp: {reader.last_timestamp}")
    logger.info(f"Params: {len(reader._param_messages_raw)}")  # type: ignore

params = reader.get_new_params()
logger.info(f"Converted {len(params)} readings.")
logger.info(params[:5])
