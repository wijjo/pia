"""Start command."""
import sys
import os

from lib import tools
from lib import command
from lib import provider

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
    command.Argument(
        '--no-firewall', dest='NO_FIREWALL', action='store_true',
        help='do not configure the firewall'
    ),
]

def execute(options):
    # Make sure credentials are available
    provider_tool = provider.Tool()
    _credentials = provider_tool.credentials
    server_config = provider_tool.config.get_server(name=options.SERVER_CONFIG)
    pid = tools.get_running_pid(pid_path=provider_tool.pid_path)
    if pid:
        tools.error('OpenVPN server is already running.', fatal_error=True)
    if options.VERBOSE:
        tools.info2(server_config)
    servers = provider_tool.select_servers(server_config)
    if not servers:
        tools.error('No matching servers found.', fatal_error=True)
    if options.VERBOSE:
        tools.info2(servers)
    tools.delete_file(provider_tool.pid_path, provider_tool.port_path)
    for server in servers:
        tools.info('Connecting to: {}'.format(server.name))
        cmd_args = ['sudo', 'openvpn']
        if not options.WAIT:
            cmd_args.extend(['--daemon', '--log', provider_tool.log_path])
        cmd_args.extend(['--config', server.config_path])
        # --auth-user-pass option must follow --config in order to override.
        cmd_args.extend(['--auth-user-pass', provider_tool.cred_path])
        if not options.WAIT:
            cmd_args.extend(['--writepid', provider_tool.pid_path])
        if provider_tool.saved_state.data.recent_servers:
            provider_tool.saved_state.data.recent_servers.append(server.name)
        else:
            provider_tool.saved_state.data.recent_servers = [server.name]
        proc = tools.run_command(*cmd_args)
        if proc.returncode == 0:
            if not options.WAIT:
                if options.DRYRUN:
                    pid = -1
                else:
                    pid = tools.get_running_pid(pid_path=provider_tool.pid_path)
                if pid:
                    tools.info('OpenVPN daemon is running with PID: {}'.format(pid))
                    if not options.NO_FIREWALL and not server_config.disable_firewall:  #pylint: disable=no-member
                        provider_tool.start_firewall(
                            server.config_path,
                            port_forwarding=server.port_forwarding,
                            block_lan=server_config.block_lan,  #pylint: disable=no-member
                            new_port=options.NEW_PORT,
                        )
                    break
                tools.error('OpenVPN does not seem to be running.')
    else:
        if not options.WAIT and os.path.exists(provider_tool.log_path):
            sys.stderr.write('===== {} (begin) ====={}'.format(
                provider_tool.log_path, os.linesep))
            os.system('sudo cat "{}"'.format(provider_tool.log_path))
            sys.stderr.write('===== {} (end) ====={}'.format(
                provider_tool.log_path, os.linesep))
        tools.error('Failed to start PIA OpenVPN server.', fatal_error=True)
