"""Configuration meta-data and support functions."""

import os
import re
from configparser import ConfigParser

from . import tools


class Meta:
    """Configuration meta-data."""

    class BadValue(Exception):
        pass

    class Option:
        """Base class for option meta-data."""
        def __init__(self, name, default_value=None):
            self.name = name
            self.default_value = default_value

    class Boolean(Option):
        """Boolean option meta-data."""

        def __init__(self, name, default_value=False):
            super().__init__(name, default_value=default_value)

        def check_value(self, value):
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                if value.lower() in ('yes', 'true'):
                    return True
                if value.lower() in ('no', 'false'):
                    return False
            raise Meta.BadValue('Bad Boolean string value: {}'.format(str(value)))

        def generate_default_configuration_text(self):
            yield '{} = {}'.format(self.name, 'yes' if self.default_value else 'no')

    class Choice(Option):
        """Multiple choice option meta-data."""

        def __init__(self, name, choices, default_value=None):
            self.choices = choices
            if default_value is None:
                default_value = choices[0]
            super().__init__(name, default_value=default_value)

        def check_value(self, value):
            if value in self.choices:
                return value
            raise Meta.BadValue([
                'Choice value ({}) is not one of: {}'.format(
                    str(value), ', '.join([str(choice) for choice in self.choices])),
            ])

        def generate_default_configuration_text(self):
            yield '# {} choices: {}'.format(self.name, ', '.join(self.choices))
            yield '{} = {}'.format(self.name, self.choices[0])

    # All supported meta-options.
    options = [
        Boolean('block_lan', default_value=False),
        Boolean('disable_dns_change', default_value=False),
        Boolean('disable_firewall', default_value=False),
        Boolean('disable_kill_switch', default_value=False),
        Boolean('mace_ad_blocking', default_value=False),
        Boolean('port_forwarding', default_value=False),
        Choice('discipline', ['first', 'recent', 'fastest', 'rotation'], default_value='first'),
    ]

    @classmethod
    def check_data(cls, raw_option_set):
        """Validate and convert raw options to a dictionary."""
        option_data = {}
        for meta_option in cls.options:
            try:
                value = raw_option_set.get(meta_option.name, '')
                option_data[meta_option.name] = meta_option.check_value(value)
            except cls.BadValue as exc:
                tools.warning('Bad {} configuration "{}" value: {}'.format(
                    meta_option.__class__.__name__,
                    meta_option.name,
                    str(raw_option_set.get(meta_option.name))
                ), [exc])
        return option_data


class ServerOptionSet(tools.Dumpable):
    """A user-specified server configuration."""
    def __init__(self, servers, option_data):
        self.servers = servers
        for key, value in option_data.items():
            setattr(self, key, value)


class Data:
    """User configuration data."""

    def __init__(self, path, openvpn_servers):
        self.path = path
        self.openvpn_servers = openvpn_servers
        self._clear()

    def _clear(self):
        self.raw_option_sets = {}
        self.default_config = None

    def load(self):
        """Read and parse the user configuration file."""
        self._clear()
        user_config = ConfigParser()
        with tools.open_input_file(self.path) as config_file:
            user_config.read_file(config_file)
            for section in user_config.sections():
                if self.default_config is None:
                    self.default_config = section
                self.raw_option_sets[section] = user_config[section]
        if not self.raw_option_sets or not self.default_config:
            tools.error('No option sets found in file:', [self.path], fatal_error=True)

    def generate(self):
        """Generate a new configuration file."""
        self._clear()
        tools.info('Generating user configuration:', [self.path])
        with tools.open_output_file(self.path) as config_file:
            config_file.write('''\
# The DEFAULT section has the data for unspecified options. Any of
# the options can be overridden in named configuration sections.
[DEFAULT]
# A comma-separated list of host names with '*' wildcards is allowed.
servers =
# Yes/no options default internally to "no", the most common choice.
# The internal "no" default can be changed here for specific options.
''')
        for meta_option in Meta.options:
            for line in meta_option.generate_default_configuration_text():
                config_file.write(line)
                config_file.write(os.linesep)
        config_file.write('''
# The first named configuration is also the default choice.
# The configuration name choice is arbitrary, but must be unique.
#[primary]
#servers = UK London
''')
        config_file.write('''
# Example with multiple rotated wildcard servers, and port-forwarding. All
# disciplines fall back to the next sequential server when one is unavailable.
#[port-forward]
#servers = CA *, France
#port_forwarding = yes
#discipline = rotation
''')

    def get_server(self, name=None):
        """Return named or default configuration option set."""
        name = name or self.default_config
        if name not in self.raw_option_sets:
            tools.error('Option set not found: {}'.format(name), fatal_error=True)
        raw_option_set = self.raw_option_sets[name]
        servers_string = raw_option_set.get('servers', None)
        if servers_string:
            server_patterns = [pat.strip() for pat in servers_string.split(',')]
        else:
            server_patterns = []
        matched_server_names = set()
        matching_openvpn_servers = []
        for pattern in server_patterns:
            regex_pattern = r'^{}$'.format(pattern.replace('*', '.*'))
            server_matcher = re.compile(regex_pattern, re.IGNORECASE)
            for openvpn_server in self.openvpn_servers:
                if server_matcher.match(openvpn_server.name):
                    if openvpn_server.name not in matched_server_names:
                        matched_server_names.add(openvpn_server.name)
                        matching_openvpn_servers.append(openvpn_server)
        if not matching_openvpn_servers:
            tools.warning('No matching servers for pattern.')
        option_data = Meta.check_data(raw_option_set)
        return ServerOptionSet(matching_openvpn_servers, option_data)
