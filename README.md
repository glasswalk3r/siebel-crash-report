# siebel-crash-report
Python project that searchs and aggregates Siebel component crashes information
into a nice report.

## Features

Automates all required steps to retrieve information of a Siebel server
component crash to send the report to Oracle support.

Information is searched and retrieve from the following sources:

- the memory dump (`core.dump` files) itself using GDB.
- FDR files with `sarmanalyzer`.
- Siebel enterprise log files.
- correlate information from the FDR with the enterprise log file.
- a summary JSON report.

The CSV (from `sarmanalyzer`) and the GDB output as text are created as
necessary in the directory defined by the `crash_dir` entry in the
`crash_reporter.ini` configuration file, together with the summary JSON report
and a copy of the `crash.txt`.

All the information (but the CSV and `gdb` output) is printed to `STDOUT`, so
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

The core and FDR files might be removed (see the configuration file) right after
the analysis is complete.

This script will work on Linux only. It is expected that the `gdb` program (to
extract the core dumps backtrace) and the `iniparse` (available as RPM package
on RedHat, CentOS and Oracle Enterprise Linux) Python module are installed.

The script `crash_monitor` has also an on-line documentation. You can check it
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

 - Python 3.x: see `setup.py` for up to date information about the support
Python versions.
 - Siebel Server binaries and configuration in place.
 - Linux (all setup is specific to Linux).
 - GNU GDB.

### Install

You should be able to install this program with `pip`:

```
$ pip install siebel-crash-report
```

Then you will need to configure the `crash_reporter` program and finally run it
against your Siebel Enterprise.

### Configuration

You must have a YAML configuration file located at your home directory as
`$HOME/.crash_reporter.yaml`.

You can see a sample configuration file at the website project.

Further information can be checked on the module documentation:

```
pydoc siebel.maintenance.crash.readConfig
```

## Development

If you want to get involved with this project development, first install the
Python development requirements with:

```
pip install -r requirements-dev.txt
```

You will also need to install the GNU Make in order to be able to use this
project `Makefile` for serveral tasks, like running the unit tests for example:

```
siebel-crash-report$ make test
pytest -v
==================================================================================== test session starts =====================================================================================
platform linux -- Python 3.6.13, pytest-6.2.2, py-1.10.0, pluggy-0.13.1 -- /home/alceu/.pyenv/versions/3.6.13/envs/siebel-crash-report/bin/python3.6
cachedir: .pytest_cache
rootdir: siebel-crash-report
collected 3 items

tests/siebel/maintenance/test_thread.py::test_fix_thread_id PASSED                                                                                                                     [ 33%]
tests/siebel/maintenance/test_thread.py::test_dec2bin PASSED                                                                                                                           [ 66%]
tests/siebel/maintenance/test_thread.py::test_dec2bin_backport PASSED                                                                                                                  [100%]

===================================================================================== 3 passed in 0.06s ======================================================================================
```
