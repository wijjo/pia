"""Install command."""

import os

from lib import tools
from lib import command
from lib import provider

name = 'install'
help = 'install PIA/OpenVPN prerequisites and configurations'

arguments = [
    command.Argument(
        '-r', '--refresh-openvpn-files', dest='REFRESH_OPENVPN_FILES',
        action='store_true', help='force OpenVPN configuration file refresh'
    ),
    command.Argument(
        '-c', '--create-user-config', dest='CREATE_USER_CONFIG', action='store_true',
        help='create new configuration file, even if one exists'
    ),
    command.Argument(
        '-u', '--user-only', dest='USER_ONLY', action='store_true',
        help='only update the user configuration'
    ),
]

REQUIRED_PACKAGES = [
    tools.Package('openvpn', executable='openvpn'),
]

def execute(options):
    provider_tool = provider.Tool()
    num_actions = 0
    if not options.USER_ONLY:
        num_actions += tools.install_packages(REQUIRED_PACKAGES)
    num_actions += provider_tool.provider.install_configuration_files(
        force=options.REFRESH_OPENVPN_FILES)
    if not os.path.exists(provider_tool.cred_path):
        provider_tool.credentials.create()
        num_actions += 1
    if not os.path.exists(provider_tool.config_path) or options.CREATE_USER_CONFIG:
        provider_tool.config.generate()
        num_actions += 1
    if num_actions > 0:
        tools.info('Installation actions performed: {}'.format(num_actions))
    else:
        tools.info('No installation actions were needed.')
