from __future__ import print_function
import re
import codecs
import os
import sys
from iniparse import INIConfig
import shutil
import traceback
from stat import S_ISDIR


def dec2bin(thread_id):
    """Convert a integer to binary depending on Python version."""
    if sys.version_info.major == 2 and sys.version_info.minor == 4:
        return dec2bin_backport(id)
    else:
        return (bin(thread_id)).replace('0b', '')


def dec2bin_backport(thread_id):
    """Back port of bin function to Python 2.4."""
    if thread_id <= 1:
        return str(thread_id)
    else:
        return dec2bin_backport(thread_id >> 1) + str(thread_id & 1)


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


def manage_comp_alias(crashes, pid, default_log, archive_dir, crash_dir,
                      enterprise_log_file):
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
    6 - the enterprise log file name

    It will update in place parameter 1 and copy any component log file found
    to 5.
    """
    try:
        if 'comp_alias' not in crashes[pid]:
            comp_alias = find_comp_alias(pid, default_log)

            if comp_alias is None:
                print("\tCouldn't find the pid %s in the enterprise log \
file." % (str(pid)))
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
                print("\tAll attempts to locate the component alias for %s \
failed." % (str(pid)))
            else:
                crashes[pid]['comp_alias'] = comp_alias
    except:  # NOQA
        print("Unexpected error!")
        all_info = sys.exc_info()
        if not all_info[0] is None:
            print('exception type is %s' % (all_info[0]))
        if not all_info[1] is None:
            print('exception value is %s' % (all_info[1]))
        if not all_info[2] is None:
            print('traceback: ')
            print(traceback.print_exception(all_info[0], all_info[1],
                                            all_info[2]))
        # to be sure that no circular references will hang around
        all_info = ()


def find_comp_alias(pid, enterprise_log):
    """Try to find a process crash in the Siebel Enterprise Log file.

    Expects as parameter the PID of the process and the complete path to the
    Siebel Enterprise log file.
    """
    print('\tTrying to locate the component alias with PID %s in the Siebel \
Enterprise log file %s... ' % (str(pid), enterprise_log), end='')

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
                    print('found it.')
                    return fields[6]
                else:
                    print('invalid line that matches the regex of process \
failure: "line".')
                    return None

        log.close()
        print('not found')
    else:
        print('file %s does not exists, cannot search for pid.' % (
            enterprise_log))

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
                    print('%s does not have a valid header line: "%s"' % (
                        log_filename, header))
                else:
                    if ((header_fields[13] == pid) and (
                            header_fields[15] == thread_num)):
                        logs_counter += 1
                        shutil.copy2(original, (os.path.join(
                            crash_dir, log_filename)))

            except UnicodeEncodeError as inst:
                print('\n\tAn error occurred when reading "%s": %s' % (
                    original, str(inst)))
            except:  # NOQA
                print('Unexpected error: ', sys.exc_info()[0])

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


def find_last(log_archive_dir):
    """Return the last created directory.

    Returns the last created directory name inside the log archive directory.
    Expects as parameter the complete path to the log archive directory.
    """
    print('Locating newest archive directory under "%s"...' % (
        log_archive_dir))
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
    location = os.path.join(os.environ['HOME'], '.crash.ini')
    fh = open(location, 'r')
    ini = INIConfig(fh)
    fh.close()
    return ini
