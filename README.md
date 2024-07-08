# Vidalicet

The missing parameter export functionality for Volvo VIDA 2014D: A Python library that turns VIDA's raw logs into usable data with proper naming and scaling.

> [!NOTE]
> This is an unfinished hobby project that's been tested with just one car. Some of the more complex parameter types (e.g. categorical values) won't work, and there can be mistakes. Please don't trust the output of this library without cross-referencing with VIDA.

## Installation

Requirements:
- [Poetry](https://python-poetry.org/) 1.2.0 or newer
- VIDA 2014D

To install, run:
```
$ poetry install
```

## Database setup

> [!NOTE]
> You can skip this part if you already have a `vidalicet.sqlite3` file.

This tool needs protocol spesifications, parameter scaling information etc. from a VIDA database. Because this data can't be redistributed legally, you must dump a functional VIDA database yourself. **You only need to do this once.**

> [!WARNING]
> Following the instructions below will produce copies of VIDA's database contents. You should recognize that this content can be protected by copyright and other laws. Copying and/or distributing this content may be illegal.

### Phase 1: Dump VIDA's db

1. Transfer the dump script ([DumpEcuParams.ps1](tools/DumpEcuParams.ps1)) to a VIDA machine.
2. Shut down VIDA (right click the VIDA icon in the system tray and select *Stop*).
3. Open a PowerShell prompt, run the dump script, and let it finish.
   - It might take a while. Check if any of the files in the output directory keep growing in size if you unsure whether the script is stuck.
   - If PowerShell nags that the execution of scripts is disabled, open an **admin** PowerShell prompt and run `$ Set-ExecutionPolicy RemoteSigned` to enable scripts permanently.
   - If PowerShell prompts you to install some packages, do it.
   - If you get an SSL/TLS error, try updating powershellget with `$ Find-Module powershellget | Install-Module`. If that doesn't work, try enabling TLS 1.2 with `$ [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor [System.Net.SecurityProtocolType]::Tls12`.
4. A new directory full of CSV files called `vida_dump` should've been created in the working directory. Transfer it to the machine you intend to use Vidalicet with.

### Phase 2: Create a Vidalicet db

Convert the CSV dump into Vidalicet's internal format:
```
$ poetry run create-db <path-to-dump-dir>
```

The script will create a single SQLite db file called `vidalicet.sqlite3` in the working directory.

That's it! The database is portable, so you don't need to recreate it if you want to use Vidalicet on a different machine.

## Usage

### Logging data

To log data in VIDA:

1. Connect to a vehicle.
2. Run a fault trace (DTC scan).
3. Go to *Diagnostics* → *Vehicle communication* and add the parameters you want to log to the watchlist (*Add to list* button). All parameters displayed in the watchlist will be logged by VIDA.
4. Do whatever you want to capture with the vehicle.
5. When you are done, keep VIDA open because the log files can be deleted if VIDA is restarted. You can disconnect the cable from the vehicle.

VIDA's diagnostic logs should be found in `C:\VIDA\System\Log\Diagnostics`. There should be one or more files that have a name starting with `<model>_<year>_<code>.log` (for example, `S60 (11-)_2011_123456.log`). Longer diagnostic sessions are split into multiple files. Grab all the files that are named after your vehicle (but differ in extension) and copy them to a safer location.

If there are multiple files, the first file will have the extension `.log0`, the second file will have the extension `.log1` etc. The last (or only) file will always have the extension `.log`.

These files contain the raw communication between VIDA and the various modules in the vehicle. This is where Vidalicet comes in.

### Reading the logs

In a nutshell:
1. Create a `Reader` instance (it will look for the Vidalicet db in the working directory by default).
2. Feed the log files into it **in order** (`.ingest_logfile`).
3. Output parameter readings (`.get_new_params`).

Minimal example:

```python
import vidalicet

log_dir = "data/vida_logs"
log_filenames = [
    "S60 (11-)_2011_123456.log0",
    "S60 (11-)_2011_123456.log",
]
log_paths = [os.path.join(log_dir, filename) for filename in log_filenames]

reader = vidalicet.reader.Reader()

for path in log_paths:
    reader.ingest_logfile(path)

params = reader.get_new_params()
```

See [examples/boost_pressure.ipynb](boost_pressure.ipynb) for a more comprehensive example that covers plotting etc.
