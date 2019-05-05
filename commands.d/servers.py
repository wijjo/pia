"""Servers command."""

name = 'servers'
help = 'list available servers'

from lib import tools

def execute(options):
    server_rows = []
    server_num = 0
    header = ['Number', 'Name', 'Forwarding', 'Protocols']
    for server in self.openvpn_servers:
        server_num += 1
        protocols = ' '.join(server.protocols)
        server_rows.append([server_num, server.name, server.port_forwarding, protocols])
    tools.display_table(server_rows, header=header, title='Available servers')
