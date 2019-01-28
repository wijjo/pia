"""Configuration meta-data and support functions."""

import os

from . import constants
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


def generate_configuration():
    """Generate a new configuration file."""
    tools.info('Generating user configuration:', [constants.CONFIGURATION_PATH])
    with tools.open_output_file(constants.CONFIGURATION_PATH) as config_file:
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
