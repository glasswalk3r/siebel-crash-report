# siebel-crash-report
Python project that searchs and aggregates Siebel component crashes information into a nice report.

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
$ pydoc siebel.maintenance.crash
```

To generate HTML documentation for this module issue the command:

```
$ pydoc -w siebel.maintenance.crash
```

## How to use

### Requirements

 - Python 2.X or 3.x.
 - Siebel Server binaries and configuration in place.
 - Linux (all setup is specific to Linux).
 - GNU GDB.

### Install

You should be able to install this program with `pip`:

```
$ pip install siebel-crash-report
```

Then you will need to configure the crash_reporter program and finally run it
against your Siebel Enterprise.

### Configuration

You must have a INI configuration file located at your home directory as
`$HOME/.crash.ini`.

Here is a sample INI configuration file:

```Ini
[main]
;location of Siebel binaries
bin_dir = /server/81/siebsrvr/bin
; location of where the crashes information will be stored. A subdirectory will be created there with filename "crash_dir" appended with datetime.date.today string
crash_dir = /server/crash_dir
; location of the Siebel Enterprise log files
enterprise_log_dir = /server/foobar/siebel/81/siebsrvr/enterprises/foobar/myserver/log
; location of Siebel Enterprise log archives
log_archive = /server/foobar/siebel/81/siebsrvr/enterprises/foobar/myserver/logarchive
; the file name of the Siebel Enterprise log file (only the file name, not the complete path)
enterprise_log_file = foobar.myserver.log
clean_files = yes
```

Further information can be checked on the module documentation:

```
$ pydoc siebel.maintenance.crash.readConfig
```

## Development

If you want to get involved with this project develoment, here are some very
basic details to start.

### Requirements

 - Python 2.X and 3.x.
 - Python modules (see `requirements.txt` and `requirements-3x.txt`).
 - Siebel Server binaries and configuration in place.
 - Linux (all setup is specific to Linux).
 - GNU GDB.

### Running tests

In order to run tests with `pytest`, setup the `PYTHONPATH` environment
variable first:

```
$ export PYTHONPATH="$PWD/src"
$ pytest
```

### Known issues

This script was created to run on Python 2.4 (I know, very old but that's what
we got back in the day) but should work without problems with Python 2.7.

Python 3.X **should** be supported. Use `requirements-3x.txt` file to install
modules through venv.
