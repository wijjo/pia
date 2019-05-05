"""Credentials command."""

import os

from lib import tools
from lib import provider

name = 'log'
help = 'follow PIA/OpenVPN log output'

def execute(options):
    provider_tool = provider.Tool()
    pid = tools.get_running_pid(pid_path=provider_tool.pid_path)
    if pid:
        os.execvp('sudo', ['sudo', 'tail', '-f', provider_tool.log_path])
    tools.error('OpenVPN does not seem to be running.')
