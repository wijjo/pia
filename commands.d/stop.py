"""Stop command."""

from lib import tools
from lib import provider

name = 'stop'
help = 'stop the PIA/OpenVPN connection'
arguments = []

def execute(options):
    provider_tool = provider.Tool()
    pid = tools.get_running_pid(pid_path=provider_tool.pid_path)
    if not pid:
        tools.error('OpenVPN server does not appear to be running.', fatal_error=True)
    tools.info('Killing OpenVPN server PID: {}'.format(pid))
    tools.run_command('sudo', 'kill', pid)
    tools.delete_file(provider_tool.pid_path, provider_tool.port_path)
