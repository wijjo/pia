"""Utility functions, etc.."""

import sys
import os
import subprocess
import math
import urllib
import time
import json
import zipfile
import inspect
from contextlib import contextmanager

IS_UNIX_LIKE_PLATFORM = sys.platform in ['linux', 'darwin']
UNIX_ROOT_BIN_DIRECTORIES = ['/sbin', '/usr/sbin', '/usr/local/sbin', '/opt/sbin']
FORWARDING_REQUEST_USER_AGENT_STRING = ' '.join([
    'Mozilla/5.0',
    '(Macintosh; Intel Mac OS X 10_10_1)',
    'AppleWebKit/537.36 (KHTML, like Gecko)',
    'Chrome/39.0.2171.95 Safari/537.36',
])
DRYRUN = False
VERBOSE = False


def get_terminal_attribute_symbols():
    '''Provide symbols for terminal colors and visual attributes.'''
    terminal_attribute_symbols = {}
    if IS_UNIX_LIKE_PLATFORM:
        # Use tput on Unix-like systems to query display strings.
        def _get_tput_string(*tput_args):
            proc = subprocess.run(
                ['tput'] + [str(arg) for arg in tput_args],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding='utf-8',
            )
            return proc.stdout.strip() if proc.returncode == 0 else ''
        def _add_tput_attribute(name, *tput_args):
            terminal_attribute_symbols[name] = _get_tput_string(*tput_args)
        _add_tput_attribute('bold', 'bold')
        _add_tput_attribute('reset', 'sgr0')
        if _get_tput_string('colors') == '256':
            def _add_tput_color_256(name, color):
                _add_tput_attribute(name, 'setaf', color)
            _add_tput_color_256('blue', 4)
            _add_tput_color_256('cyan', 6)
            _add_tput_color_256('green', 2)
            _add_tput_color_256('grey', 0)
            _add_tput_color_256('magenta', 5)
            _add_tput_color_256('red', 1)
            _add_tput_color_256('yellow', 3)
        else:
            def _add_tput_color_16(name, color):
                _add_tput_attribute(name, 'setf', color)
            _add_tput_color_16('blue', 1)
            _add_tput_color_16('cyan', 3)
            _add_tput_color_16('green', 2)
            _add_tput_color_16('grey', 7)
            _add_tput_color_16('magenta', 5)
            _add_tput_color_16('red', 4)
            _add_tput_color_16('yellow', 3)
    else:
        # No support for terminal colors on non-Unix-like systems for now.
        for key in (
            'bold',
            'reset',
            'blue',
            'cyan',
            'green',
            'grey',
            'magenta',
            'red',
            'yellow',
        ):
            terminal_attribute_symbols[key] = ''
    return terminal_attribute_symbols


def iterate_items(obj):
    """Iterate list, tuple or single object."""
    if obj:
        if isinstance(obj, (list, tuple)):
            for obj_item in obj:
                yield obj_item
        else:
            yield obj


class DisplayItem:
    """Holds thing(s) to display with optional display attributes."""

    def __init__(self, *children, attributes=None):
        self.children = children
        self.attributes = attributes

    def to_string(self, attribute_map=None):
        """Generate output lines with or without display attributes."""
        parts = []
        if attribute_map and self.attributes:
            for attribute in iterate_items(self.attributes):
                if attribute in attribute_map:
                    parts.append(attribute_map[attribute])
                else:
                    parts.append('<{}?>'.format(attribute))
        if self.children:
            for child_item in self.children:
                if isinstance(child_item, DisplayItem):
                    parts.append(child_item.to_string(attribute_map=attribute_map))
                elif isinstance(child_item, Exception):
                    parts.append('Exception[{}]: '.format(child_item.__class__.__name__))
                    parts.append(''.join(str(child_item)))
                else:
                    parts.append(str(child_item))
        if attribute_map and self.attributes and 'reset' in attribute_map:
            parts.append(attribute_map['reset'])
        return ''.join(parts)

    def text_length(self):
        """Return the total text length."""
        length = 0
        if self.children:
            for child_item in self.children:
                if isinstance(child_item, DisplayItem):
                    length += child_item.text_length()
                else:
                    length += len(str(child_item))
        return length


class ConsoleStreamMaker:
    """Make streams for console output."""

    def __init__(self, attribute_map):
        self.attribute_map = attribute_map

    def create_stream(self, for_errors=False, prepend=None, append=None, attributes=None):
        """Create message output stream."""
        class Stream:
            def __init__(self, attribute_map):
                self.attribute_map = attribute_map
                self.attributes = list(iterate_items(attributes))
                self.output_stream = sys.stderr if for_errors else sys.stdout
            def stream_output(self, *line_objs, indent=0):
                for line_obj in line_objs:
                    if isinstance(line_obj, (list, tuple)):
                        self.stream_output(*line_obj, indent=(indent + 1))
                    else:
                        items = []
                        if prepend:
                            items.extend(iterate_items(prepend))
                        if indent > 0:
                            items.append('  ' * indent)
                        items.append(line_obj)
                        if append:
                            items.extend(iterate_items(append))
                        outer_item = DisplayItem(*items, attributes=self.attributes)
                        self.output_stream.write(outer_item.to_string(attribute_map=self.attribute_map))
                        self.output_stream.write(os.linesep)
            def __call__(self, *line_objs, indent=0):
                self.stream_output(*line_objs)
        return Stream(self.attribute_map)


def find_file_in_path(file_name, search_path, executable=False):
    """
    Search for a file in the specified path.

    Return the full path to the file if found or None otherwise.
    """
    check_function = path_is_executable if executable else os.path.isfile
    for directory in search_path.split(os.path.pathsep):
        full_path = os.path.join(directory, file_name)
        if check_function(full_path):
            return full_path


def find_executable(exe_name, as_superuser=False):
    """Search for an executable in the system PATH."""
    # For a dry run add some additional root-accessible paths to be able to
    # guess whether or not the command would be found as root.
    path = os.environ['PATH']
    if IS_UNIX_LIKE_PLATFORM and as_superuser and os.getuid() != 0:
        path = os.path.pathsep.join([path] + UNIX_ROOT_BIN_DIRECTORIES)
    return find_file_in_path(exe_name, path, executable=True)


def path_is_executable(path):
    """Return True if the path resolves to an executable."""
    return os.path.isfile(path) and os.access(path, os.X_OK)


def format_strings(*items, args=None, kwargs=None):
    """Yield iterable formatted strings."""
    args = args or []
    kwargs = kwargs or {}
    base_indent = '  '
    def _generator(item, indent, args, kwargs):
        if isinstance(item, (list, tuple)):
            sub_indent = '' if indent is None else indent + base_indent
            for sub_item in item:
                for line in _generator(sub_item, sub_indent, args, kwargs):
                    yield line
        else:
            indent_string = indent or ''
            item_strings = []
            if isinstance(item, BaseException):
                item_strings = item.messages
            elif isinstance(item, Exception):
                item_strings.append('Exception[{}]: '.format(item.__class__.__name__))
                item_strings.append(''.join([base_indent, str(item)]))
            elif not isinstance(item, str):
                item_strings.append(str(item))
            else:
                item_strings.append(item.format(*args, **kwargs))
            for item_string in item_strings:
                yield ''.join([indent_string, item_string])
    return _generator(items, None, args, kwargs)


class BaseException(Exception):
    """Enhanced base exception class."""

    def __init__(self, *messages, args=None, kwargs=None):
        """Use args and kwargs for string formatting, plus set kwargs items as attributes."""
        for name, value in kwargs.items():
            setattr(self, name, value)
        self.messages = list(format_strings(*messages, args=args, kwargs=kwargs))
        super().__init__(os.linesep.join(self.messages))


def shorten_path(path):
    """Shorten a path for display."""
    # For now just convert $HOME to '~'.
    if path.startswith(os.environ['HOME']):
        return os.path.join('~', path[len(os.environ['HOME']) + 1:])
    return path


def error(*line_objs, fatal_error=False, return_code=1):
    """Error stream wrapper with support for fatal errors."""
    ERROR_STREAM(*line_objs)
    if fatal_error:
        ERROR_STREAM('(quitting)')
        sys.exit(return_code)


def warning(*line_objs):
    """Warning stream wrapper."""
    WARNING_STREAM(*line_objs)


def info(*line_objs):
    """Info stream wrapper."""
    INFO_STREAM(*line_objs)


def info2(*line_objs):
    """info2 stream wrapper handles VERBOSE-only enabling."""
    if VERBOSE:
        INFO2_STREAM(*line_objs)


def heading(*line_objs):
    """Heading stream wrapper."""
    HEADING_STREAM(*line_objs)


def run_command(*args, **kwargs):
    """Simplified interface to subprocess.run() for non-shell command."""
    fatal_error = kwargs.pop('fatal_error', False)
    always_run = kwargs.pop('always_run', False)
    dry_run = DRYRUN and not always_run
    # String-ize the positional arguments
    subprocess_args = [str(arg) for arg in args]
    # May be called before TOOLS is set up.
    if dry_run:
        info('>> {}'.format(subprocess.list2cmdline(subprocess_args)))
        proc = subprocess.CompletedProcess(subprocess_args, 0)
        if kwargs.get('stdout') == subprocess.PIPE:
            proc.stdout = ''
        return proc
    if VERBOSE:
        info2('Command: {}'.format(subprocess.list2cmdline(subprocess_args)))
    proc = subprocess.run(subprocess_args, **kwargs)
    if fatal_error and proc.returncode != 0:
        error('Command failed with return code {}:'.format(proc.returncode),
              [str(args)], fatal_error=True)
    return proc

def capture_command(*args, **kwargs):
    """Simplified interface to subprocess.run() with captured output."""
    kwargs['stdout'] = subprocess.PIPE
    kwargs['stderr'] = subprocess.STDOUT
    kwargs['encoding'] = 'utf-8'
    return run_command(*args, **kwargs)


def shell_command(*args, **kwargs):
    """Simplified interface to subprocess.run() for shell command."""
    kwargs['shell'] = True
    return run_command(*args, **kwargs)


class Package:
    """Installable package."""
    def __init__(self, package, executable=None):
        self.package = package
        self.executable = executable


def install_packages(packages):
    """Install component(s) using the system installer."""
    num_installed = 0
    if packages:
        to_install = []
        for pkg in packages:
            if pkg.executable and not find_executable(pkg.executable, as_superuser=True):
                to_install.append(pkg.package)
        if to_install:
            if not INSTALL_COMMAND:
                error('Please install these packages before trying again:',
                      packages, fatal_error=True)
            info('Installing packages:', to_install)
            if not DRYRUN:
                if subprocess.run(INSTALL_COMMAND + to_install).returncode != 0:
                    error('Package installation failed.', fatal_error=True)
            num_installed += len(to_install)
    return num_installed


def delete_file(*paths, fatal_error=False, always_run=False):
    """Delete one or more files."""
    dry_run = DRYRUN and not always_run
    for path in paths:
        if os.path.exists(path):
            info2('Delete file:', [path])
            try:
                if not dry_run:
                    os.remove(path)
            except (IOError, OSError) as exc:
                error('Unable to delete file.', [path, exc], fatal_error=fatal_error)


def display_list(heading, data, marker='-'):
    """Display numbered list if marker is an integer or a bulleted list otherwise."""
    info('')
    if heading:
        heading(heading)
    info('')
    if data:
        if type(marker) is int:
            # Numbered list
            marker_format = '%%%dd)' % int(math.log10(len(data)) + 1)
            for item in data:
                info(' '.join([marker_format % marker, str(item)]))
                marker += 1
        else:
            # Normal list
            for item in data:
                info(' '.join([marker, str(item)]))


class RowFormatter:
    """Used by display_table() for row formatting."""

    widths = None
    col_count = None
    row_format = None

    def __init__(self, data, attr=None):
        self.data = data
        self.attr = attr

    def output_item(self):
        num_row_cols = len(self.data)
        if num_row_cols < self.col_count:
            self.data.extend([''] * (self.col_count - num_row_cols))
        data_str = self.row_format % tuple([str(item) for item in self.data])
        return DisplayItem(data_str, attributes=self.attr)

    @classmethod
    def update(cls, widths, column_types):
        cls.widths = widths
        cls.col_count = len(widths)
        format_parts = []
        for col_idx in range(len(widths)):
            format_parts.append('%%%s%ds' % (
                '' if column_types[col_idx] == 'number' else '-',
                widths[col_idx],
            ))
        cls.row_format = '  '.join(format_parts)


def display_table(row_seq,
        title=None,
        header=None,
        title_attr='magenta',
        header_attr='cyan',
    ):
    """Format a columnar table with or without a header."""
    widths = [DisplayItem(field).text_length() for field in header] if header else []
    row_formatters = []
    data_row_count = 0
    column_types = []
    for row in row_seq:
        data_row_count += 1
        row_data = []
        if len(column_types) < len(row):
            column_types.extend([None] * (len(row) - len(column_types)))
        for col_idx in range(len(row)):
            cell_item = row[col_idx]
            if isinstance(cell_item, bool):
                column_types[col_idx] = 'other'
                cell_item = 'YES' if cell_item else ''
            elif isinstance(cell_item, (int, float)):
                # 'number' only sticks for the column if no other types exist.
                if column_types[col_idx] is None:
                    column_types[col_idx] = 'number'
                cell_item = str(cell_item)
            else:
                column_types[col_idx] = 'other'
            col_len = DisplayItem(cell_item).text_length()
            row_data.append(cell_item)
            if len(widths) <= col_idx:
                widths.append(col_len)
            else:
                if col_len > widths[col_idx]:
                    widths[col_idx] = col_len
        row_formatters.append(RowFormatter(row_data))
    if title:
        total_width = sum(widths) + (2 * (len(widths) - 1))
        title_string = str(title)
        pad_width_left = int((total_width - len(title_string)) / 2) - 1
        pad_width_right = total_width - pad_width_left - len(title_string) - 2
        pad_left = '=' * max(pad_width_left, 3)
        pad_right = '=' * max(pad_width_right, 3)
        info(DisplayItem(pad_left, ' ', title_string, ' ', pad_right, attributes='magenta'))
    if header:
        row_formatters.insert(0, RowFormatter([
            header[i].center(widths[i]).rstrip()
            for i in range(len(header))
        ], attr=header_attr))
        header_seps = ['=' * width for width in widths]
        row_formatters.insert(1, RowFormatter(header_seps, attr=header_attr))
    if data_row_count == 0:
        return
    RowFormatter.update(widths, column_types)
    for row_formatter in row_formatters:
        info(row_formatter.output_item())


def get_directory(*path_segments, create_directory=True, fatal_error=True):
    """
    Get a directory, optionally creating it.

    By default it creates a missing directory and makes all errors fatal.

    Check the "exists" status member fatal_error is False.

    Return an object with these members:
        path        absolute directory path or None if unavailable
        created     True if it was created by this call
        exists      True if the directory exists
    """
    class DirectoryStatus:
        def __init__(self):
            self.path = os.path.expanduser(os.path.join(*path_segments))
            self.created = False
            self.exists = (
                os.path.isdir(self.path) or
                (DRYRUN and status.path in DRYRUN_DIRECTORIES_CREATED))
    status = DirectoryStatus()
    if not status.exists:
        # It may not exist as a directory, but it could be something else.
        if os.path.exists(status.path):
            error('Path exists, but is not a directory:', [status.path],
                  fatal_error=fatal_error)
        if create_directory:
            info('Create directory:', [status.path])
            if DRYRUN:
                DRYRUN_DIRECTORIES_CREATED.add(status.path)
            else:
                try:
                    os.makedirs(status.path)
                    status.exists = True
                except OSError as exc:
                    error('Error creating directory:', [status.path, exc],
                          fatal_error=fatal_error)
    return status


@contextmanager
def open_input_file(path, binary=False, delete_on_error=False):
    """Open a file for reading."""
    try:
        mode = 'rb' if binary else 'r'
        with open(path, mode) as input_file:
            class InputFile:
                def read(self):
                    return input_file.read()
                def __iter__(self):
                    for line in input_file:
                        yield line
                def read_lines(self):
                    for line in self:
                        yield line.rstrip()
            yield InputFile()
    except (IOError, OSError) as exc:
        if delete_on_error:
            error('Deleting file after failing to open it for input:', [path])
            delete_file(path, fatal_error=False)
        error('Failed to access input file:', [path, exc], fatal_error=True)


@contextmanager
def open_output_file(path, binary=False, create_directory=False, permissions=None):
    """Open a file for writing."""
    # Errors are fatal -- return status can be ignored.
    get_directory(os.path.dirname(path), create_directory=create_directory)
    if DRYRUN:
        class FakeOutputFile:
            def write(self, data):
                pass
            def write_lines(self, *lines):
                pass
        yield FakeOutputFile()
    else:
        try:
            mode = 'wb' if binary else 'w'
            with open(path, mode) as output_file:
                class OutputFile:
                    def write(self, data):
                        output_file.write(data)
                    def write_lines(self, *lines):
                        for line in lines:
                            output_file.write(line)
                            output_file.write(os.linesep)
                yield OutputFile()
        except (IOError, OSError) as exc:
            error('Error trying to write to file:', [path, exc], fatal_error=True)
        if permissions is not None:
            if run_command('chmod', permissions, path, fatal_error=False).returncode != 0:
                # Remove a file with theoretically bad permissions.
                delete_file(path)
                error('Failed to change file mode to {}:'.format(permissions),
                      [path], fatal_error=True)


def download_url(url, timeout=60, fatal_error=False):
    try:
        request = urllib.request.Request(url)
        request.add_header('User-Agent', FORWARDING_REQUEST_USER_AGENT_STRING)
        if VERBOSE:
            info2('Download URL: "{}"'.format(request.get_full_url()))
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_data = response.read()
            if VERBOSE:
                info2('Download data:', [str(response_data)])
            return response_data
    except urllib.request.URLError as exc:
        error('Download failed due to URL error:', [url, exc], fatal_error=fatal_error)
    except Exception as exc:
        error('Download failed due to other error:', [url, exc], fatal_error=fatal_error)

def download_file(url,
                  path,
                  expiration=None,
                  force=False,
                  create_directory=True,
                  fatal_error=False):
    """Download a file if it hasn't been downloaded recently."""
    # Errors are fatal -- return status can be ignored.
    do_download = True
    if os.path.exists(path):
        if not force and (not expiration or (time.time() - os.path.getctime(path) <= expiration)):
            info2('Use existing file for download URL:', [url, path])
            do_download = False
    if do_download and not DRYRUN:
        info('Download:', ['From: {}'.format(url), '  To: {}'.format(path)])
        download_data = download_url(url, fatal_error=fatal_error)
        if download_data:
            with open_output_file(
                    path, binary=True, create_directory=create_directory) as downloaded_file:
                downloaded_file.write(download_data)
    return do_download


def download_json(url, timeout=60, fatal_error=False):
    response = download_url(url, timeout=timeout, fatal_error=fatal_error)
    if response:
        try:
            if not isinstance(response, bytes):
                # Probably unnecessary.
                return json.loads(str(response))
            return json.loads(response.decode('utf-8'))
        except json.JSONDecodeError:
            error('JSON response decode error:', [str(response)],
                  fatal_error=fatal_error)
        except:
            error('Unable to decode expected JSON response:',
                  [str(response)],
                  fatal_error=fatal_error)


def unzip_to(zip_path, directory):
    """Extract files from a zip file to a target directory."""
    info('Extract zip:', ['From: {}'.format(zip_path), '  To: {}/'.format(directory)])
    if not DRYRUN:
        try:
            with zipfile.ZipFile(zip_path) as zip_file:
                zip_file.extractall(path=directory)
        except Exception as exc:
            error('Zip file extraction failed:', [exc], fatal_error=True)


def get_running_pid(pid=None, pid_path=None):
    """Return PID if process identified by PID or pid file path is running."""
    if not pid and pid_path:
        if os.path.exists(pid_path):
            with open_input_file(pid_path, delete_on_error=True) as pid_path:
                pid = int(pid_path.read())
    if pid:
        proc = capture_command('sudo', 'kill', '-0', pid,
                               fatal_error=False,
                               always_run=True)
        if proc.returncode != 0:
            pid = None
    return pid


def test_server_latency(address, fatal_error=False):
    """
    Return server latency in milliseconds.

    Return None if fatal_error is False and the server if unavailable.
    """
    proc = capture_command('ping', '-c', 3, address, fatal_error=False)
    if proc.returncode != 0:
        if fatal_error:
            error('Unable to ping address:', [address], fatal_error=True)
        return 99999999
    lines = proc.stdout.split(os.linesep)
    for line in lines:
        if line.startswith('rtt '):
            try:
                return float(line.split(' = ', maxsplit=1)[1].split('/')[0])
            except (IndexError, ValueError):
                break
    if fatal_error:
        error('Failed to parse ping output.', lines, fatal_error=True)
    return 99999999


class PersistentJSONData:
    """Persistent JSON data accessed as member attributes of "data"."""

    def __init__(self, path, description):
        self.path = path
        self.description = description
        self._dirty = False
        if os.path.exists(self.path):
            with open_input_file(self.path, delete_on_error=True) as input_file:
                try:
                    self.data = json.loads(input_file.read())
                except json.JSONDecodeError as exc:
                    error('Deleting bad {} file: {}'.format(
                                    self.description, self.path),
                                [exc])
                    delete_file(self.path)
        parent_for_data = self
        class Data(dict):
            def __getattr__(self, name):
                return self.get(name, None)
            def __setattr__(self, name, value):
                self[name] = value
                parent_for_data._dirty = True
        self.data = Data()

    def save(self):
        """Flush the state to disk."""
        if self._dirty:
            info('Saving state:', [self.path])
            create_directory(os.path.dirname(self.path))
            if not DRYRUN:
                with open_output_file(self.path) as output_file:
                    output_file.write(json.dumps(self.data, indent=2))
                    output_file.write(os.linesep)
        self._dirty = False


class Dumpable:
    """Dumpable overrides __str__ and __repr__ for useful stringized output."""
    def __str__(self):
        attr_pairs = []
        for name, member in inspect.getmembers(self):
            if not name.startswith('_'):
                value_string = "'{}'".format(member) if isinstance(member, str) else str(member)
                attr_pairs.append((name, value_string))
        attrs_string = ', '.join(['{}={}'.format(key, value) for key, value in attr_pairs])
        return '{}({})'.format(self.__class__.__name__, attrs_string)
    def __repr__(self):
        return str(self)


### Globals

CONSOLE_STREAM_MAKER = ConsoleStreamMaker(get_terminal_attribute_symbols())
INFO_STREAM = CONSOLE_STREAM_MAKER.create_stream()
HEADING_STREAM = CONSOLE_STREAM_MAKER.create_stream(attributes='blue')
WARNING_STREAM = CONSOLE_STREAM_MAKER.create_stream(prepend='WARNING: ',
                                                    for_errors=True,
                                                    attributes='yellow')
ERROR_STREAM = CONSOLE_STREAM_MAKER.create_stream(prepend='ERROR: ',
                                                  for_errors=True,
                                                  attributes='red')
INFO2_STREAM = CONSOLE_STREAM_MAKER.create_stream(prepend='INFO2: ')

if find_executable('pacman', as_superuser=True):
    INSTALL_COMMAND = ['sudo', 'pacman', '--noconfirm', '-S']
elif find_executable('apt-get', as_superuser=True):
    INSTALL_COMMAND = ['sudo', 'apt-get', 'install', '-y']
elif find_executable('yum', as_superuser=True):
    INSTALL_COMMAND = ['sudo', 'yum', 'install', '-y']
else:
    INSTALL_COMMAND = None

DRYRUN_DIRECTORIES_CREATED = set()
