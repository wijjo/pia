"""Constant data for PIA command."""

import sys
import os

if sys.version_info.major < 3:
    sys.stderr.write('ERROR: This script requires Python version 3.{}'.format(os.linesep))
    sys.exit(1)

COMMAND_DESCRIPTION = 'Private Internet Access OpenVPN front-end.'

class SystemPackage:
    """Installable package."""
    def __init__(self, package, executable=None):
        self.package = package
        self.executable = executable

SYSTEM_PACKAGES = [
    SystemPackage('openvpn', executable='openvpn'),
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

# Directories
BASE_DIRECTORY = os.path.expanduser('~/.pia')
CONFIGURATION_DIRECTORY = os.path.join(BASE_DIRECTORY, 'configuration')
DOWNLOADS_DIRECTORY = os.path.join(BASE_DIRECTORY, 'downloads')
STATE_DIRECTORY = os.path.join(BASE_DIRECTORY, 'state')
PORT_FORWARDING_HTML_PATH = os.path.join(DOWNLOADS_DIRECTORY, 'forwarding.html')
PORT_FORWARDING_LIST_PATH = os.path.join(DOWNLOADS_DIRECTORY, 'forwarding.servers')
CONFIGURATION_PATH = os.path.join(CONFIGURATION_DIRECTORY, 'pia.conf')
CREDENTIALS_PATH = os.path.join(CONFIGURATION_DIRECTORY, 'pia.cred')
STATE_PATH = os.path.join(STATE_DIRECTORY, 'pia.state.json')
PID_FILE_PATH = os.path.join(STATE_DIRECTORY, 'pia.pid')
LOG_FILE_PATH = os.path.join(STATE_DIRECTORY, 'pia.log')
PORT_FILE_PATH = os.path.join(STATE_DIRECTORY, 'pia.port')
CLIENT_ID_FILE_PATH = os.path.join(STATE_DIRECTORY, 'pia.clientid.rnd')

# Various PIA URLs
BASE_URL = 'https://www.privateinternetaccess.com'
DOWNLOAD_URL = '/'.join([BASE_URL, 'openvpn'])
FORWARDING_REQUEST_URL = 'http://209.222.18.222:2000'
FORWARDING_REQUEST_USER_AGENT_STRING = ' '.join([
    'Mozilla/5.0',
    '(Macintosh; Intel Mac OS X 10_10_1)',
    'AppleWebKit/537.36 (KHTML, like Gecko)',
    'Chrome/39.0.2171.95 Safari/537.36',
])
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

# Additional directories to add to the PATH for a *IX super-user.
IS_UNIX_LIKE_PLATFORM = sys.platform in ['linux', 'darwin']
UNIX_ROOT_BIN_DIRECTORIES = ['/sbin', '/usr/sbin', '/usr/local/sbin', '/opt/sbin']

# Downloads expire after 1 week, and then are re-downloaded.
SECONDS_PER_DAY = 86400
CONFIGURATION_EXPIRATION = SECONDS_PER_DAY * 7
PORT_FORWARDING_LIST_EXPIRATION = SECONDS_PER_DAY * 7
BIG_NUMBER = 99999999
