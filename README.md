# siebel-crash-report
Python script that search and aggregates Siebel component crashes information
into a nice report.

## Features

Automates all required steps to retrieve information of a Siebel server
component crash to send the report to Oracle support.

Information is searched and retrieve from the following sources:

- the memory dump (`core.dump` files) itself using GDB.
- FDR files with sarmanalyzer.
- Siebel enterprise log files.
- correlate information from the FDR with the enterprise log file.
- a summary JSON report.

The CSV (from sarmanalyzer) and the GDB output as text are created as necessary
in the directory defined by the `crash_dir` entry in the `crash_reporter.ini`
configuration file, together with the summary JSON report and a copy of the
`crash.txt`.

All the information (but the CSV and GDB output) is printed to `STDOUT`, so
it's to run it together in a cron job and pipe it to `mail` program.

Here is an example of the JSON report (two crashes identified):

```javascript
{
	18192 : {
		'core' : {
			'last_mod' : '2016-09-08 17:46:08',
			'executable' : 'siebprocmw',
			'size' : 211382272,
			'generated_by' : 'SIGABRT',
			'filename' : 'core.18192'
		},
		'fdr' : {
			'last_mod' : '2016-09-08 17:46:07',
			'size' : 5000032,
			'filename' : 'T201609081518_P018192.fdr'
		},
		'thread' : '-247841904'
	},
	28019 : {
		'core' : {
			'last_mod' : '2016-09-09 22:40:22',
			'executable' : 'siebmtshmw',
			'size' : 356610048,
			'generated_by' : 'SIGABRT',
			'filename' : 'core.28019'
		},
		'fdr' : {
			'last_mod' : '2016-09-09 22:40:22',
			'size' : 5000032,
			'filename' : 'T201609092237_P028019.fdr'
		},
		'thread' : '-171263680'
	}
}
```

The core and FDR files might be removed right after (see the configuration file)
the analysis is complete.

This script will work on Linux only. It is expected that the `gdb` program (to
  extract the core dumps backtrace) and the `iniparse` (available as RPM
    package on RedHat, CentOS and Oracle Enterprise Linux) Python module are
    installed.

The script crash_monitor has also an on-line documentation. You can check it
with:

```
pydoc crash_monitor
```

To generate HTML documentation for this module issue the command:

```
pydoc -w crash_monitor
```

## Requirements

 - Python 2.X.
 - Python modules (see requirements.txt).
 - Siebel Server binaries.
 - Linux (all setup is specific to Linux).
 - GNU GDB.

## Running tests

In order to run tests with `pytest`, setup the `PYTHONPATH` environment
variable first:

```
$ export PYTHONPATH="$PWD/src"
$ pytest
```

## Known issues

This script was created to run on Python 2.4 (I know, very old but that's what
we got back in the day) but should work without problems with Python 2.7.

Python 3.X **should** be supported. Use `requirements-3x.txt` file to install
modules through venv.
