"""Credentials command."""

import os

from lib import tools
from lib import provider
from lib import command

name = 'credentials'
help = 'save PIA/OpenVPN user credentials'

arguments = [
    command.Argument('-f', '--force', dest='FORCE', action='store_true',
                help='force by overwriting existing file as needed'),
]

def execute(options):
    provider_tool = provider.Tool()
    if os.path.exists(provider_tool.cred_path) and not options.FORCE:
        tools.info('Credentials file exists:', [provider_tool.cred_path])
        return
    provider_tool.credentials.create()
