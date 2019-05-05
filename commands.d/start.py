"""Start command."""

import sys
import os

from lib import tools
from lib import command

name = 'start'
help = 'start the PIA/OpenVPN connection'

arguments = [
    command.Argument(
        '-w', '--wait', dest='WAIT',
        help='do not exit and wait for key to disconnect'
    ),
    command.Argument(
        '-N', '--new-port', dest='NEW_PORT',
        help='assign new forwarded port using new client ID'
    ),
    command.Argument(
        '-s', '--server-config', dest='SERVER_CONFIG', action='store',
        help='server configuration name to use instead of default'
    ),
]

def execute(options):
    # Make sure credentials are available
    self.credentials.get()
    server_config = self.config.get_server(name=self.options.SERVER_CONFIG)
    pid = tools.get_running_pid(pid_path=self.pid_path)
    if pid:
        tools.error('OpenVPN server is already running.', fatal_error=True)
    if self.options.VERBOSE:
        tools.info2(server_config)
    servers = self.select_servers(server_config)
    if not servers:
        tools.error('No matching servers found.', fatal_error=True)
    if self.options.VERBOSE:
        tools.info2(servers)
    tools.delete_file(self.pid_path, self.port_path)
    for server in servers:
        tools.info('Connecting to: {}'.format(server.name))
        cmd_args = ['sudo', 'openvpn']
        if not self.options.WAIT:
            cmd_args.extend(['--daemon', '--log', self.log_path])
        cmd_args.extend(['--config', server.config_path])
        # --auth-user-pass option must follow --config in order to override.
        cmd_args.extend(['--auth-user-pass', self.cred_path])
        if not self.options.WAIT:
            cmd_args.extend(['--writepid', self.pid_path])
        if self.saved_state.data.recent_servers:
            self.saved_state.data.recent_servers.append(server.name)
        else:
            self.saved_state.data.recent_servers = [server.name]
        proc = tools.run_command(*cmd_args)
        if proc.returncode == 0:
            if not self.options.WAIT:
                if self.options.DRYRUN:
                    pid = -1
                else:
                    pid = tools.get_running_pid(pid_path=self.pid_path)
                if pid:
                    tools.info('OpenVPN daemon is running with PID: {}'.format(pid))
                    self.start_firewall(
                        server.config_path,
                        port_forwarding=server.port_forwarding,
                        block_lan=server_config.block_lan,                 #pylint: disable=no-member
                        disable_firewall=server_config.disable_firewall,   #pylint: disable=no-member
                    )
                    break
                tools.error('OpenVPN does not seem to be running.')
    else:
        if not self.options.WAIT and os.path.exists(self.log_path):
            sys.stderr.write('===== {} (begin) ====={}'.format(
                self.log_path, os.linesep))
            os.system('sudo cat "{}"'.format(self.log_path))
            sys.stderr.write('===== {} (end) ====={}'.format(
                self.log_path, os.linesep))
        tools.error('Failed to start PIA OpenVPN server.', fatal_error=True)
