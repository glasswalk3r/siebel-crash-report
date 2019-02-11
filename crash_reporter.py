#!/usr/bin/env python

import os
import datetime
import codecs
import re
import sys
import shutil
import simplejson
import signal
import os.path
from subprocess import call, Popen, PIPE
from stat import S_ISDIR
import traceback
from iniparse import BasicConfig

"""
Script to search for Siebel Server crash files and generate a report to help to
identify the problem.
If any is found, it will execute all the require steps to retrieve information
from the core dumps, FDR, crash file and related log files
to generate a complete information about the crash. A summary with the
information is generated as a JSON to STDOUT.
The core and FDR files might be removed right after (see the configuration
file).
This script will work on Linux only. It is expected that the gdb program is
also available (to extract the core dumps backtrace).
To generate HTML documentation for this module issue the command:
    pydoc -w crash_monitor


COPYRIGHT AND LICENSE

This software is copyright (c) 2012 of Alceu Rodrigues de Freitas Junior,
arfreitas@cpan.org

This file is part of siebel-crash-report.

siebel-crash-report is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

siebel-crash-report is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
You should have received a copy of the GNU General Public License
along with Siebel Monitoring Tools.  If not, see http://www.gnu.org/licenses/.
"""


def is_to_rem(ini):
    """Check if crash related files are expected to be removed or not.
    Expects as parameter an instance of iniparse.BasicConfig.
    Returns true (if "yes"), false (if "no") or raise an exception (for any
    value different of those two).
    """
    if ini.clean_files == 'yes':
        return True
    elif ini.clean_files == 'no':
        return False
    else:
        raise ValueError(
                'Invalid file for clean_files: (%s)' % ini.clean_files)


def dec2bin(s):
    """Back port of bin function to Python 2.4."""
    if s <= 1:
        return str(s)
    else:
        return dec2bin(s >> 1) + str(s & 1)


def fix_thread_id(thread_id):
    """
    Expects a thread id as parameter and will convert it to a proper value if
    necessary.
    See Doc ID 1500676.1 for more information about that.
    Returns the thread_id (converted or not).
    """
    id = int(thread_id)

    if id > (2**31):
        bin_str = dec2bin(id)
        bin_digits = []

        for digit in bin_str:

            if digit == '1':
                bin_digits.append('0')
            else:
                bin_digits.append('1')

        temp = int(''.join(bin_digits[1:]), 2)
        temp += 1
        return ("-" + str(temp))
    else:
        return thread_id


def find_thread_id(filename):
    """Expect a complete path to a FDR file as parameter.
    It will search for the thread id corresponding to the point the crash
    occurred and will return it.
    """
    csv_file = codecs.open(filename, 'r')
    thread_id = None

    for line in csv_file:
        fields = line.split(',')
        # 6859951,1430765202,2509233040,Fdr_FDR,Fdr Internal,FdrSub_FDR_CRASH,
        # ** CRASHING THREAD **,0,0,"",""
        if ((len(fields) >= 6) and (fields[6] == '** CRASHING THREAD **')):
            thread_id = fields[2]
            break
    csv_file.close()
    return thread_id


def manage_comp_alias(crashes, pid, default_log, archive_dir, crash_dir):
    """Handle a component alias locating.

    Handles a component alias in the sense of locating and copying it's related
    crash information whenever is possible.
    First it will try to find the crash PID in the Siebel Enterprise log file.
    If not found, it will also try the archives.

    Expects the following parameters:
    1 - a dictionary containing all the crashes information
    2 - the PID of the crash
    3 - the path to the default Siebel Enterprise log file
    4 - the path to the log archive directory
    5 - the path to the crash directory created by this script

    It will update in place parameter 1 and copy any component log file found
    to 5.
    """
    try:
        if 'comp_alias' not in crashes[pid]:
            comp_alias = find_comp_alias(pid, default_log)

            if comp_alias is None:
                print "\tCouldn't find the pid %s in the enterprise log \
file." % (str(pid))
                last_log = os.path.join(find_last(archive_dir),
                                        enterprise_log_file)
                comp_alias = find_comp_alias(pid, last_log)
                if comp_alias is not None:
                    crashes[pid]['enterprise_log'] = last_log
                    shutil.copy2(last_log, crash_dir)
            else:
                crashes[pid]['enterprise_log'] = default_log
                shutil.copy2(default_log, crash_dir)

            if comp_alias is None:
                print "\tAll attempts to locate the component alias for %s \
failed." % (str(pid))
            else:
                crashes[pid]['comp_alias'] = comp_alias
    except: # NOQA
        print "Unexpected error!"
        all_info = sys.exc_info()
        if not all_info[0] is None:
            print 'exception type is %s' % (all_info[0])
        if not all_info[1] is None:
            print 'exception value is %s' % (all_info[1])
        if not all_info[2] is None:
            print 'traceback: '
            print traceback.print_exception(all_info[0], all_info[1],
                                            all_info[2])
        # to be sure that no circular references will hang around
        all_info = ()


def find_comp_alias(pid, enterprise_log):
    """Try to find a process crash in the Siebel Enterprise Log file.

    Expects as parameter the PID of the process and the complete path to the
    Siebel Enterprise log file.
    """
    print '\tTrying to locate the component alias with PID %s in the Siebel \
Enterprise log file %s... ' % (str(pid), enterprise_log),

    if (os.path.exists(enterprise_log)):
        regex = re.compile(r'.*(Process\s' + str(pid) +
                           r'\sexited\swith\serror).*', re.UNICODE | re.DOTALL)
        log = codecs.open(enterprise_log, 'r')

        for line in log:
            match = regex.match(line)

            if match:
                fields = line.split()
                log.close()

                if (len(fields) >= 6):
                    print 'found it.'
                    return fields[6]
                else:
                    print 'invalid line that matches the regex of process \
failure: "line".'
                    return None

        log.close()
        print 'not found'
    else:
        print 'file %s does not exists, cannot search for pid.' % (
            enterprise_log)

    return None


def find_logs(log_dir, regex, crash_dir, pid, thread_num):
    """Search for the logs of a Siebel component process that crashed.

    Expects as parameters:
    - the complete path to the log directory
    - a regular expression object used to match the file names found in the
    log directory
    - the directory where the crash information will be stored, since the log
    files found will be copied to there
    - the related PID of the process that crashed
    - the thread number of the process that crashed

    Returns an integer with the number of logs found. Each log found will be
    copied to crash_dir.
    """
    logs_counter = 0

    for log_filename in os.listdir(log_dir):
        match = regex.match(log_filename)
        if match:
            original = os.path.join(log_dir, log_filename)

            try:
                comp_log = codecs.open(original, 'r')
                header = comp_log.readline()
                comp_log.close()

                # file header checking
                header_fields = header.split(' ')

                if (not(len(header_fields) >= 19)):
                    print '%s does not have a valid header line: "%s"' % (
                        log_filename, header)
                else:
                    if ((header_fields[13] == pid) and (
                         header_fields[15] == thread_num)):
                        logs_counter += 1
                        shutil.copy2(original, (os.path.join(
                            crash_dir, log_filename)))

            except UnicodeEncodeError, inst:
                print '\n\tAn error occurred when reading "%s": %s' % (
                    original, str(inst))
            except: # NOQA
                print "Unexpected error:", sys.exc_info()[0]

    return logs_counter


def signal_map():
    """Map signal names to it's respective number.

    Returns a dict objet that maps the numeric signals from Linux to the
    corresponding signal name.
    Created from kill -l output on OEL:
    $ kill -l
    1) SIGHUP       2) SIGINT       3) SIGQUIT      4) SIGILL
    5) SIGTRAP      6) SIGABRT      7) SIGBUS       8) SIGFPE
    9) SIGKILL     10) SIGUSR1     11) SIGSEGV     12) SIGUSR2
    13) SIGPIPE     14) SIGALRM     15) SIGTERM     16) SIGSTKFLT
    17) SIGCHLD     18) SIGCONT     19) SIGSTOP     20) SIGTSTP
    21) SIGTTIN     22) SIGTTOU     23) SIGURG      24) SIGXCPU
    25) SIGXFSZ     26) SIGVTALRM   27) SIGPROF     28) SIGWINCH
    29) SIGIO       30) SIGPWR      31) SIGSYS      34) SIGRTMIN
    35) SIGRTMIN+1  36) SIGRTMIN+2  37) SIGRTMIN+3  38) SIGRTMIN+4
    39) SIGRTMIN+5  40) SIGRTMIN+6  41) SIGRTMIN+7  42) SIGRTMIN+8
    43) SIGRTMIN+9  44) SIGRTMIN+10 45) SIGRTMIN+11 46) SIGRTMIN+12
    47) SIGRTMIN+13 48) SIGRTMIN+14 49) SIGRTMIN+15 50) SIGRTMAX-14
    51) SIGRTMAX-13 52) SIGRTMAX-12 53) SIGRTMAX-11 54) SIGRTMAX-10
    55) SIGRTMAX-9  56) SIGRTMAX-8  57) SIGRTMAX-7  58) SIGRTMAX-6
    59) SIGRTMAX-5  60) SIGRTMAX-4  61) SIGRTMAX-3  62) SIGRTMAX-2
    63) SIGRTMAX-1  64) SIGRTMAX

    It's an ugly hack, but couldn't find a portable code to produce the
    correct result.
    Not all signals were implemented anyway.
    """
    return dict(zip(list(range(1, 32)), ['SIGHUP', 'SIGINT', 'SIGQUIT',
                                         'SIGILL', 'SIGTRAP', 'SIGABRT',
                                         'SIGBUS', 'SIGFPE', 'SIGKILL',
                                         'SIGUSR1', 'SIGSEGV', 'SIGUSR2',
                                         'SIGPIPE', 'SIGALRM', 'SIGTERM',
                                         'SIGSTKFLT', 'SIGCHLD', 'SIGCONT',
                                         'SIGSTOP', 'SIGTSTP', 'SIGTTIN',
                                         'SIGTTOU', 'SIGURG', 'SIGXPU',
                                         'SIGXFSZ', 'SIGVTALRM', 'SIGPROF',
                                         'SIGWINCH', 'SIGIO', 'SIGPWR',
                                         'SIGSYS']))


def signal_handler(signal, frame):
    """
    SIGINT handler. Just print to STDOUT a message asking to wait operations to
    finish.
    This is an attempt to try to finish the process correctly in case of server
    bounce.
    """
    print 'Received SIGINT signal'
    print 'Resuming operations, please wait'


def find_last(log_archive_dir):
    # returns the last created directory
    print 'Locating newest archive directory under "%s"...' % (log_archive_dir)
    archives = {}

    for archive_dir in os.listdir(log_archive_dir):
        full_path = os.path.join(log_archive_dir, archive_dir)
        statinfo = os.stat(full_path)

        if (S_ISDIR(statinfo.st_mode)):
            archives[statinfo.st_mtime] = full_path

    entries = archives.keys()
    entries.sort(reverse=True)
    return archives[entries[0]]


def readConfig():
    """Read the INI configuration file.

    Configuration file details

    This script uses a INI file to providing information of where to search for
    crash files and execute the expected
    steps once one if found.
    The configuration file is expected to the located at the user's home
    directory with the filename equal to ".crash_reporter.ini".
    Details on INI format can be checked by reading the standard iniparse
    module documentation.

    The expected keys and values are described below. You don't need to use
    namespaces in the INI file, neither it is expected to.

    - crash_archive: expects a full path of a directory that will be used to
    store the crash(es) information. Inside this directory, subdirectories will
    be created with the name corresponding to the string returned by today()
    method from datetime.date Python standard module and respective files will
    be located there.
    - siebel_bin: the complete path to the Siebel Server bin directory. Also,
    where the crash files will be located.
    - ent_log_dir: the complete path to the Siebel Enterprise log directory
    - ent_log_file: the complete path to the current Siebel Enterprise log file
    - log_archive: the complete path to the directory where the log files were
    rotated
    - clean_files: defines if the related files (core, FDR and crash.txt)
    should be removed or not. Accept the values "yes" and "no". Log files will
    not be removed at all.
    """
    ini = BasicConfig()
    location = os.path.join(os.environ['HOME'], '.crash.ini')
    with (open(location, mode='r')) as fp:
        ini.readfp(fp)
    return ini


# to try to finish the process in case of server bounce
signal.signal(signal.SIGINT, signal_handler)
# TODO: add try/catch

cfg = readConfig()
bin_dir = cfg.main.bin_dir
today = datetime.date.today()
crash_dir = cfg.main.crash_dir
enterprise_log_dir = cfg.main.enterprise_log_dir
log_archive = cfg.main.log_archive
enterprise_log_file = cfg.main.enterprise_log_file
enterprise_log = os.path.join(enterprise_log_dir, enterprise_log_file)
crashes = {}
introduction = """Greetings,

This report will search for specific files on this Siebel Server file system
that are corresponding for component crashes.
Please beware that some files might be missing, specially if the crashes
happened during the Siebel Server restarted, occasion when the log files are
rotated.

Once information is extracted, some of those files (core dump and FDR) will be
removed from the server to maintain storage space available.

List of files found:
----
"""

print introduction

from_to = signal_map()

for filename in os.listdir(bin_dir):

    if filename[0:5] == 'core.':
        print 'Found core dump %s' % (filename)

        if (not(os.path.isdir(crash_dir))):
            os.mkdir(crash_dir)

        core_path = os.path.join(bin_dir, filename)
        statinfo = os.stat(core_path)
        last_mod = datetime.datetime.fromtimestamp(statinfo.st_mtime)
        output = (Popen(['file', core_path],
                        stdout=PIPE).communicate()[0]).rstrip()
        """
        /<PATH>/siebsrvr/bin/core.23340: ELF 32-bit LSB core file Intel 80386,
        version 1 (SYSV), SVR4-style, from 'siebmtshmw'
        """
        bin = ((output.split(','))[-1]).replace(" from '", "").replace("'", "")
        # this can raise an exception
        pid = int((filename.split('.'))[1])

        if pid in crashes:
            crashes[pid]['core'] = {'filename': filename,
                                    'size': statinfo.st_size,
                                    'last_mod': str(last_mod),
                                    'executable': bin,
                                    'generated_by': 'unknown'}
        else:
            crashes[pid] = {'core': {'filename': filename,
                                     'size': statinfo.st_size,
                                     'last_mod': str(last_mod),
                                     'executable': bin,
                                     'generated_by': 'unknown'}}

        if sys.platform.startswith('linux'):
            print '\tExtracting information from the core file with gdb... ',
            gdb_cmd_filename = os.path.join(crash_dir, 'gdb.cmd')
            gdb = open(gdb_cmd_filename, 'w')
            gdb.write('bt\n')
            gdb.close()
            gdb_out = open((os.path.join(crash_dir, 'gdb_core.txt')), 'a')
            gdb_out.write('Analyzing core ' + core_path + '\n')
            popen = Popen(['/usr/bin/gdb', bin,
                           os.path.join(bin_dir, bin, core_path),
                           '-batch', '-x', gdb_cmd_filename],
                          bufsize=0, shell=False, stdout=PIPE)
            out, err = popen.communicate()
            signal_regex = re.compile(
                r'^Program\sterminated\swith\ssignal\s(\d+)', re.MULTILINE)
            found = signal_regex.findall(out)

            if len(found) >= 1:
                crashes[pid]['core']['generated_by'] = from_to[int(found[0])]

            gdb_out.write(out)
            gdb_out.close()

            if err is not None:
                print 'GDB returned an error: %s.' % (err)
            else:
                print 'done.'

            if is_to_rem(cfg):
                os.remove(core_path)

            os.remove(gdb_cmd_filename)

        manage_comp_alias(crashes=crashes, pid=pid, default_log=enterprise_log,
                          archive_dir=log_archive, crash_dir=crash_dir)
        continue

    if filename[-4:] == '.fdr':
        print 'Found FDR file %s' % (filename)

        if (not(os.path.isdir(crash_dir))):
            os.mkdir(crash_dir)

        fdr_path = os.path.join(bin_dir, filename)
        statinfo = os.stat(fdr_path)
        last_mod = datetime.datetime.fromtimestamp(statinfo.st_mtime)

        # this can raise an exception
        # T201504072041_P028126.fdr
        pid = int((((filename.split('_'))[1].split('.'))[0])[1:])

        if pid in crashes:
            crashes[pid]['fdr'] = {'filename': filename,
                                   'size': statinfo.st_size,
                                   'last_mod': str(last_mod)}
        else:
            crashes[pid] = {'fdr': {'filename': filename,
                                    'size': statinfo.st_size,
                                    'last_mod': str(last_mod)}}

        csv_file = os.path.join(crash_dir, (filename + '.csv'))

        ret = call(['sarmanalyzer', '-o', csv_file, '-x', '-f', fdr_path])

        if ret != 0:
            print ' '.join(('\tsarmanalizer execution failed with code',
                            str(ret)))

        if is_to_rem(cfg):
            os.remove(fdr_path)

        thread_id = find_thread_id(csv_file)

        if thread_id is not None:
            crashes[pid]['thread'] = fix_thread_id(thread_id)
        else:
            print " ".join(("\tCouldn't find the thread id of the crashing \
thread of process", str(pid), 'by reading the export FDR information'))

        manage_comp_alias(crashes=crashes, pid=pid, default_log=enterprise_log,
                          archive_dir=log_archive, crash_dir=crash_dir)

        continue

    if filename == 'crash.txt':
        print 'Found file crash.txt, copying it... ',

        if (not(os.path.isdir(crash_dir))):
            os.mkdir(crash_dir)

        if is_to_rem(cfg):
            os.rename((os.path.join(bin_dir, filename)),
                      (os.path.join(crash_dir, filename)))
        else:
            shutil.copy2((os.path.join(bin_dir, filename)), crash_dir)

        os.rename((os.path.join(bin_dir, filename)), (os.path.join(
            crash_dir, filename)))
        print 'done.'

if len(crashes):
    for pid in crashes.keys():

        if 'comp_alias' in crashes[pid]:
            log_counter = 0

            if 'thread' in crashes[pid]:
                print 'Searching for log files of component %s, pid %s, thread \
id %s...' % (crashes[pid]['comp_alias'], str(pid), crashes[pid]['thread']),
                ent_regex = re.compile(crashes[pid]['comp_alias'] + r'.*\.log')
                log_counter = find_logs(log_dir=enterprise_log_dir,
                                        regex=ent_regex, crash_dir=crash_dir,
                                        pid=str(pid),
                                        thread_num=crashes[pid]['thread'])

                if (log_counter > 0):
                    print 'found %s log files.' % (str(log_counter))
                else:
                    print 'no log files found in %s.' % (enterprise_log_dir)
                    print 'Trying to find in the logarchive... ',
                    # sane setting
                    log_counter = 0
                    last_one = find_last(log_archive)
                    log_counter = find_logs(log_dir=last_one, regex=ent_regex,
                                            crash_dir=crash_dir, pid=str(pid),
                                            thread_num=crashes[pid]['thread'])

                    if (log_counter > 0):
                        print 'found %s log files.' % (str(log_counter))
                    else:
                        print 'no log files found in %s' % (last_one)
            else:
                print 'PID %s is missing thread id, cannot search for \
logs.' % (str(pid))

        else:
            print 'PID %s is missing component alias, cannot search for \
logs.' % (str(pid))

    print '\n----\nDumping technical details of component crashes found:\n \
%s\n----' % (str(crashes))
    print 'Also dumping all technical details found in JSON format to crashes_\
info.json file'
    crashes_info = os.path.join(crash_dir, 'crashes_info.json')
    fp = codecs.open(crashes_info, 'w', encoding='utf8')
    simplejson.dump(crashes, fp)
    fp.close()
    print '\n'

print 'End of report. If files were found, they will be located in the home \
directory of the server, under %s directory.' % (crash_dir)
