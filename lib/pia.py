"""PIA-specific functionality."""

import os
import time
import hashlib
import tempfile
import collections
from glob import glob
from html.parser import HTMLParser

from . import tools
from . import openvpn

# Various PIA URLs
BASE_DIRECTORY = os.path.expanduser('~/.pia')
BASE_URL = 'https://www.privateinternetaccess.com'
DOWNLOAD_URL = '/'.join([BASE_URL, 'openvpn'])
FORWARDING_REQUEST_URL = 'http://209.222.18.222:2000'
FORWARDING_HELP_URL = '/'.join([
    BASE_URL,
    'helpdesk',
    'kb',
    'articles',
    'how-do-i-enable-port-forwarding-on-my-vpn'
])

# Provisional port-forwarding server list. Serves as a fall-back until the
# current list can be scraped.
PROVISIONAL_PORT_FORWARDING_SERVER_LIST = [
    'CA Toronto',
    'CA Montreal',
    'CA Vancouver',
    'Czech Republic',
    'DE Berlin',
    'DE Frankfurt',
    'France',
    'Israel',
    'Netherlands',
    'Romania',
    'Spain',
    'Sweden',
    'Switzerland',
]

# Maps protocol names to file names.
PROTOCOL_ZIP_FILES = {
    'udp': 'openvpn.zip',
    'tcp': 'openvpn-tcp.zip',
    'strong-udp': 'openvpn-strong.zip',
    'strong-tcp': 'openvpn-strong-tcp.zip',
    'ip': 'openvpn-ip.zip',
}
PROTOCOLS = PROTOCOL_ZIP_FILES.keys()

CLIENT_ID_FILE_NAME = 'pia.clientid.rnd'
PORT_FORWARDING_LIST_EXPIRATION = 3600 * 24 * 7


class PIAError(tools.BaseException):
    """Exception raised for PIA-related errors."""
    pass


class OpenVPNConfigurationBundle:
    """Web/filesystem data for a downloaded server configuration bundle."""

    Server = collections.namedtuple('Server', ['name', 'path', 'protocol', 'forwarding'])

    def __init__(self, protocol, port_forwarding_names, download_dir, config_dir):
        self.protocol = protocol
        self.port_forwarding_names = port_forwarding_names or []
        if self.protocol not in PROTOCOLS:
            tools.error('Bad protocol: {}'.format(protocol), fatal_error=True)
        file_name = PROTOCOL_ZIP_FILES[self.protocol]
        self.download_path = os.path.join(download_dir, file_name)
        self.download_url = '/'.join([DOWNLOAD_URL, file_name])
        self.directory = os.path.join(config_dir, protocol)

    def install_configuration_files(self, force=False):
        """Download and install configuration."""
        downloaded = tools.download_file(self.download_url, self.download_path, force=force)
        if not downloaded and not force and self.servers:
            return False
        tools.unzip_to(self.download_path, self.directory)
        return True

    @property
    def servers(self):
        """On-demand/cached server list."""
        if not hasattr(self, '_servers'):
            self._servers = []
            for path in sorted(glob(os.path.join(self.directory, '*.ovpn'))):
                name = os.path.splitext(os.path.basename(path))[0]
                forwarding = (name in self.port_forwarding_names)
                self._servers.append(self.Server(name, path, self.protocol, forwarding))
        return self._servers


class PortForwardingServerNameScraper(HTMLParser):
    """Extracts port-forwarding server name list from HTML page URL."""

    def __init__(self):
        self.content_div_level = None
        self.content_ul_level = None
        self.is_found_item = False
        self.found = None
        super().__init__()

    def scrape(self, html_path, list_path):
        tools.download_file(FORWARDING_HELP_URL, html_path,
                            expiration=PORT_FORWARDING_LIST_EXPIRATION,
                            fatal_error=False)
        if os.path.exists(html_path):
            with tools.open_input_file(html_path) as html_file:
                self.feed(html_file.read())
        if self.found:
            with tools.open_output_file(list_path) as list_file:
                list_file.write_lines(*self.found)

    def handle_starttag(self, tag, attrs):
        self.is_found_item = False
        if self.content_div_level is None:
            if tag == 'div' and self.found is None:
                for attr_name, attr_value in attrs:
                    if attr_name == 'class' and 'article-content' in attr_value.split():
                        self.content_div_level = 1
                        break
            return
        if tag == 'div':
            self.content_div_level += 1
            return
        if tag == 'ul':
            if self.content_ul_level is None:
                self.content_ul_level = 0
            else:
                self.content_ul_level += 1
            return
        if tag == 'li' and self.content_ul_level == 0:
            if self.found is None:
                self.found = []
            self.found.append('')
            self.is_found_item = True

    def handle_data(self, data):
        if self.is_found_item:
            if data:
                self.found[-1] = self.found[-1] + data

    def handle_endtag(self, tag):
        if self.content_div_level is not None and tag == 'div':
            self.content_div_level -= 1
            if self.content_div_level == 0:
                self.content_div_level = None
                self.content_ul_level = None
        if self.content_ul_level is not None and tag == 'ul':
            self.content_ul_level -= 1


class PIAProvider:
    """PIA provider class with required attributes and methods."""

    long_name = 'Private Internet Access'
    short_name = 'pia'

    def __init__(self, paths):
        self.download_dir = paths.download_dir
        self.config_dir = paths.config_dir
        self.port_path = paths.port_path
        self.html_path = os.path.join(paths.download_dir, '{}.html'.format(self.short_name))
        self.list_path = os.path.join(paths.download_dir, '{}.list'.format(self.short_name))
        self.client_id_path = os.path.join(paths.state_dir, 'pia.clientid.rnd')

    @property
    def port_forwarding_server_names(self):
        """Get scraped or fall-back port-forwarding server name list."""
        if not hasattr(self, '_port_forwarding_server_names'):
            scraper = PortForwardingServerNameScraper()
            scraper.scrape(self.html_path, self.list_path)
            port_forwarding_server_names = None
            if os.path.exists(self.list_path):
                with tools.open_input_file(self.list_path) as list_file:
                    port_forwarding_server_names = list(list_file.read_lines())
            if not port_forwarding_server_names:
                tools.warning('Using fall-back port-forwarding server name list.')
                port_forwarding_server_names = PROVISIONAL_PORT_FORWARDING_SERVER_LIST
            self._port_forwarding_server_names = port_forwarding_server_names
        return self._port_forwarding_server_names

    def get_forwarded_port(self, new_port=False):
        """Forward a port, if connected, and return the port number."""
        if tools.DRYRUN:
            return 9999
        time.sleep(2)
        # Load or generate the client ID hash for the request parameter.
        if os.path.exists(self.client_id_path) and not new_port:
            with tools.open_input_file(self.client_id_path) as id_file:
                client_id = id_file.read().strip()
        else:
            client_id = hashlib.sha256(os.urandom(16384)).hexdigest()
            with tools.open_output_file(self.client_id_path, mkdir=True) as id_file:
                id_file.write(client_id)
        full_url = '/'.join([FORWARDING_REQUEST_URL, '?client_id={}'.format(client_id)])
        json_response = tools.download_json(full_url, timeout=4)
        if json_response:
            try:
                port = int(json_response.get('port'))
            except ValueError:
                tools.error('Invalid returned port value "{}".'.format(port))
            if port:
                with tools.open_output_file(self.port_path) as port_file:
                    port_file.write(str(port))
                tools.info('Forwarded port ({}) saved to file:'.format(port),
                                [self.port_path])
                return port
        else:
            tools.error('Failed to establish port forwarding.')

    def iterate_openvpn_bundles(self):
        """Generate OpenVPN configuration data for all supported protocols."""
        for protocol in PROTOCOLS:
            yield OpenVPNConfigurationBundle(
                protocol,
                self.port_forwarding_server_names,
                self.download_dir,
                self.config_dir,
            )

    def get_servers(self):
        """Get VPN servers."""
        recent = self.saved_state.data.recent_servers or [] #pylint: disable=E1101
        servers = {}
        for openvpn_protocol_bundle in self.iterate_openvpn_bundles():
            for server in openvpn_protocol_bundle.servers:
                if server.name not in servers:
                    if server.name in recent:
                        recent_order = recent.index(server.name) + 1
                    else:
                        recent_order = len(recent) + 1
                    servers[server.name] = openvpn.Server(
                        server.name,
                        server.path,
                        server.protocol,
                        server.forwarding,
                        recent_order,
                    )
                else:
                    servers[server.name].protocols.append(server.protocol)
        if not servers:
            raise PIAError(
                'OpenVPN files not found.',
                'You may need to run the "install" command.'
            )
        return sorted(servers.values(), key=lambda server: server.name)

    def install_configuration_files(self, force=False):
        """Install configuration files and return the number installed."""
        num_installed = 0
        for bundle in self.iterate_openvpn_bundles():
            num_installed += bundle.install_configuration_files(force=force)
        return num_installed

    def iterate_status_paths(self):
        """Yield label/path pairs for status display."""
        yield ('Client ID file', self.client_id_path)
