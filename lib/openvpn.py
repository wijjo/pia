"""OpenVPN support."""

import os

from . import tools

class Server(tools.Dumpable):
    """An OpenVPN server configuration."""

    def __init__(self, name, config_path, protocol, port_forwarding, recent_order):
        self.name = name
        self.config_path = config_path
        self.protocols = [protocol]
        self.port_forwarding = port_forwarding
        self.recent_order = recent_order
        self.latency = 99999999

    @property
    def remote(self):
        if not hasattr(self, '_remote'):
            class Remote:
                def __init__(self, address, port):
                    self.addr = address
                    self.port = port
            with tools.open_input_file(self.config_path) as config_file:
                for line in config_file.read_lines():
                    fields = line.strip().split()
                    if fields[0] == 'remote':
                        try:
                            self._remote = Remote(fields[1], int(fields[2]))
                            break
                        except (IndexError, ValueError):
                            tools.error('Unable to read or parse OpenVPN configuration:',
                                        [self.config_path],
                                        fatal_error=True)
                else:
                    tools.error('OpenVPN configuration is missing "remote" line:',
                                [self.config_path], fatal_error=True)
        return self._remote
