"""Provider base classes."""

import os
import re
import collections
import time

from . import tools
from . import configuration
from . import credentials
from . import firewall

Paths = collections.namedtuple('Server', [
    'config_dir', 'state_dir', 'download_dir', 'port_path'
])


PROVIDER_CLASS = None


DEVICE_WAIT_SLEEP_SECONDS = 0
DEVICE_WAIT_MAX_RETRIES = 5


def set_provider_class(provider_class):
    """
    Establish the VPN provider class.

    IMPORTANT: This must have been called with a VPN provider class before
    attempting to create a provider Tool.
    """
    global PROVIDER_CLASS
    PROVIDER_CLASS = provider_class


class Tool:
    """Utility class used by VPN provider-related sub-commands."""

    vpn_device_regex = re.compile(r'TUN/TAP device (\w+) opened')
    iproute_show_regex = re.compile(r'^default via ([0-9.]+) dev (\w+) ')
    vpn_config_remote_regex = re.compile(r'^\s*remote ([^\s]+) (\d+)\s*$')
    vpn_config_protocol_regex = re.compile(r'^\s*proto (\w+)\s*$')

    def __init__(self):
        if not PROVIDER_CLASS:
            tools.error('No VPN provider class was configured.', fatal_error=True)
        self.base_dir = tools.get_directory('~', '.{}'.format(PROVIDER_CLASS.short_name)).path
        self.config_dir = tools.get_directory(self.base_dir, 'configuration').path
        self.state_dir = tools.get_directory(self.base_dir, 'state').path
        self.download_dir = tools.get_directory(self.base_dir, 'downloads').path
        self.config_path = os.path.join(self.config_dir, '{}.conf'.format(PROVIDER_CLASS.short_name))
        self.cred_path = os.path.join(self.config_dir, '{}.cred'.format(PROVIDER_CLASS.short_name))
        self.port_path = os.path.join(self.state_dir, '{}.port'.format(PROVIDER_CLASS.short_name))
        self.state_path = os.path.join(self.state_dir, '{}.state.json'.format(PROVIDER_CLASS.short_name))
        self.pid_path = os.path.join(self.state_dir, '{}.pid'.format(PROVIDER_CLASS.short_name))
        self.log_path = os.path.join(self.state_dir, '{}.log'.format(PROVIDER_CLASS.short_name))
        self.provider = PROVIDER_CLASS(Paths(
            self.config_dir,
            self.state_dir,
            self.download_dir,
            self.port_path,
        ))
        # Data loaded (lazily) from the user configuration file.
        self.saved_state = tools.PersistentJSONData(self.state_path, 'state')

    def cleanup(self):
        """Cleanup, e.g. flush persistent data."""
        self.saved_state.save()

    @property
    def openvpn_servers(self):
        """Provide and manage cached OpenVPN server list."""
        if not hasattr(self, '_openvpn_servers'):
            recent_server_names = self.saved_state.data.recent_servers or []     #pylint: disable=E1101
            self._openvpn_servers = self.provider.get_servers(recent_server_names)
        return self._openvpn_servers

    @property
    def config(self):
        """On-demand access to user configuration data."""
        if not hasattr(self, '_config'):
            self._config = configuration.Data(self.config_path, self.openvpn_servers)
            self._config.load()
        return self._config

    @property
    def credentials(self):
        """On-demand access to user credentials."""
        if not hasattr(self, '_credentials'):
            self._credentials = credentials.Credentials(self.cred_path)
        return self._credentials

    def select_servers(self, server_config):
        """Select a server based on options, selection method, and persistent state."""
        # Create the server sequence based on the selected discipline.
        discipline = (server_config.discipline or 'first').lower()
        if discipline == 'first':
            servers = server_config.servers
        elif discipline == 'fastest':
            for server in servers:
                server.latency = tools.test_server_latency(server.remote.addr)
            servers = sorted(server_config.servers,
                             key=lambda server: server.latency)
        elif discipline == 'recent':
            servers = sorted(server_config.servers,
                             key=lambda server: server.recent_order)
        elif discipline == 'rotation':
            servers = sorted(server_config.servers,
                             key=lambda server: server.recent_order,
                             reverse=True)
        else:
            tools.error('Bad server selection discipline: {}'.format(discipline), fatal_error=True)
        # Filter based on port forwarding, or not.
        if server_config.port_forwarding:
            servers = list(filter(lambda server: server.port_forwarding, servers))
        return servers or None

    def get_vpn_data(self, vpn_config_path):
        """Parse OpenVPN configuration file and return select data."""
        class VPNConfigData:
            def __init__(self):
                self.lan_addr = None
                self.def_dev = None
                self.vpn_dev = None
                self.addr = None
                self.port = None
                self.protocol = None
        data = VPNConfigData()
        proc = tools.capture_command('ip', 'route', 'show', always_run=True)
        for line in proc.stdout.split(os.linesep):
            matched = self.iproute_show_regex.search(line)
            if matched:
                data.lan_addr = matched.group(1)
                data.def_dev = matched.group(2)
                break
        else:
            tools.error('Failed to find default device using "ip route show".',
                        fatal_error=True)
        for retry_num in range(DEVICE_WAIT_MAX_RETRIES + 1):
            if retry_num > 0:
                tools.info('Waiting for TUN/TAP device -- retry {} of {}'.format(
                           retry_num, DEVICE_WAIT_MAX_RETRIES))
            time.sleep(DEVICE_WAIT_SLEEP_SECONDS)
            proc = tools.capture_command('sudo', 'cat', self.log_path, always_run=True)
            for line in proc.stdout.split(os.linesep):
                matched = self.vpn_device_regex.search(line)
                if matched:
                    data.vpn_dev = matched.group(1)
                    tools.info('Found TUN/TAP devicd: {}'.format(data.vpn_dev))
                    break
            else:
                continue
            break
        if not data.vpn_dev and tools.DRYRUN:
            data.vpn_dev = '(dryrun-tun-device)'
        if not data.vpn_dev:
            tools.error('Failed to find TUN/TAP device in log: {}'.format(self.log_path),
                        fatal_error=True)
        with tools.open_input_file(vpn_config_path) as vpn_config_file:
            for line in vpn_config_file:
                matched = self.vpn_config_remote_regex.match(line)
                if matched:
                    data.addr = matched.group(1)
                    data.port = matched.group(2)
                matched = self.vpn_config_protocol_regex.match(line)
                if matched:
                    data.protocol = matched.group(1)
        return data

    def start_firewall(self, config_path,
                       port_forwarding=False,
                       block_lan=False,
                       new_port=False):
        """Start the VPN-tweaked firewall."""
        vpn = self.get_vpn_data(config_path)
        tools.info('Resetting the firewall ...')
        firewall.reset()
        tools.info('Starting the firewall ...')
        sshd_port = tools.get_sshd_port()
        tools.info('SSHD port is {}.'.format(sshd_port))
        firewall.start(vpn.def_dev, vpn.vpn_dev, vpn.lan_addr, vpn.port, vpn.protocol, sshd_port)
        if port_forwarding:
            new_string = ' (new)' if new_port else ''
            tools.info('Determining{} forwarded port ...'.format(new_string))
            forwarded_port = self.provider.get_forwarded_port(new_port=new_port)
            tools.info('Forwarding port {}...'.format(forwarded_port))
            firewall.forward_port(vpn.vpn_dev, forwarded_port)
        if not block_lan:
            tools.info('Enabling LAN address {} on {} ...'.format(vpn.def_dev, vpn.lan_addr))
            firewall.enable_lan(vpn.def_dev, vpn.lan_addr)
        tools.info('Firewall enabled.')
