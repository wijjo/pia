"""Credentials handling."""

import sys
import os
from getpass import getpass

from . import tools

class Credentials:
    """User credentials access."""

    def __init__(self, path):
        self.path = path

    def create(self):
        """Prompt for and save credentials."""
        if not tools.DRYRUN:
            try:
                while True:
                    username = input('Username: ')
                    if username:
                        break
                    tools.error('Username must not be empty.')
                while True:
                    password = getpass(prompt='Password: ')
                    if password:
                        break
                    tools.error('Password must not be empty.')
            except (EOFError, KeyboardInterrupt):
                tools.info('', 'Credentials were not saved.')
                sys.exit(1)
            with tools.open_output_file(self.path,
                                        permissions='600',
                                        mkdir=True) as credentials_file:
                credentials_file.write_lines(username, password)
        tools.info('Credentials were saved:', [self.path])

    def get(self):
        """Return data from the credentials file."""
        if not os.path.exists(self.path):
            self.create()
        with tools.open_input_file(self.path) as credentials_file:
            lines = [line for line in credentials_file.read_lines()]
            if len(lines) < 2:
                tools.error('The credentials file is bad.',
                            'Please save a new one.',
                            fatal_error=True)
            return lines[:2]
