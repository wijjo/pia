"""Firewall management."""

from . import tools

def _iptables_run(*args):
    tools.run_command('sudo', 'iptables', *args)

def _iptables_reset_input():
    _iptables_run('--policy', 'INPUT', 'ACCEPT')

def _iptables_reset_output():
    _iptables_run('--policy', 'OUTPUT', 'ACCEPT')

def _iptables_reset_forwarding():
    _iptables_run('--policy', 'FORWARD', 'ACCEPT')

def _iptables_enable_input_device(device):
    _iptables_run('-A', 'INPUT', '-i', device, '-j', 'ACCEPT')

def _iptables_enable_output_device(device):
    _iptables_run('-A', 'OUTPUT', '-o', device, '-j', 'ACCEPT')

def _iptables_accept_forwarding():
    _iptables_run('-A', 'FORWARD', '-j', 'ACCEPT')

def _iptables_enable_input_address(device, address):
    _iptables_run('-A', 'INPUT', '-i', device, '-s', address, '-j', 'ACCEPT')

def _iptables_enable_output_address(device, address):
    _iptables_run('-A', 'OUTPUT', '-o', device, '-d', address, '-j', 'ACCEPT')

def _iptables_enable_input_protocol(device, protocol, port):
    _iptables_run('-A', 'INPUT', '-o', device,
                        '-p', protocol, '--dport', port, '-j', 'ACCEPT')

def _iptables_enable_output_protocol(device, protocol, address, port):
    _iptables_run('-A', 'OUTPUT', '-o', device, '-d', address,
                        '-p', protocol, '--dport', port, '-j', 'ACCEPT')

def _iptables_enable_input_states(*states):
    state_string = ','.join(states)
    _iptables_run('-A', 'INPUT', '-m', 'state', '--state', state_string, '-j', 'ACCEPT')

def _iptables_disable_input():
    _iptables_run('--policy', 'INPUT', 'DROP')

def _iptables_disable_output():
    _iptables_run('--policy', 'OUTPUT', 'DROP')

def _iptables_disable_forwarding():
    _iptables_run('--policy', 'FORWARD', 'DROP')

def _iptables_clear_all():
    _iptables_run('-Z')
    _iptables_run('-F')
    _iptables_run('-X')

# Public methods.

def reset():
    """Reset the firewall."""
    _iptables_reset_input()
    _iptables_reset_output()
    _iptables_reset_forwarding()
    _iptables_clear_all()

def start(def_dev, vpn_dev, lan_addr, port, protocol):
    """Start the firewall."""
    _iptables_disable_output()
    _iptables_disable_input()
    _iptables_disable_forwarding()
    _iptables_enable_output_device('lo')
    _iptables_enable_output_device(vpn_dev)
    _iptables_enable_output_protocol(def_dev, protocol, lan_addr, port)
    _iptables_enable_input_device('lo')
    _iptables_enable_input_states('ESTABLISHED', 'RELATED')

def forward_port(device, port):
    """Forward a port."""
    _iptables_enable_input_protocol(device, 'tcp', port)
    _iptables_enable_input_protocol(device, 'udp', port)

def enable_lan(device, address):
    """Enable LAN access."""
    _iptables_enable_output_address(device, address)
    _iptables_enable_input_address(device, address)
