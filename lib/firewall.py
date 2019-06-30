"""Firewall management."""

from . import tools, iptables

def reset():
    """Reset the firewall."""
    iptables.reset_input()
    iptables.reset_output()
    iptables.reset_forwarding()
    iptables.clear_all()

def start(def_dev, vpn_dev, lan_addr, vpn_port, vpn_protocol, sshd_port):
    """Start the firewall."""
    iptables.disable_output()
    iptables.disable_input()
    iptables.disable_forwarding()
    iptables.enable_output_device('lo')
    iptables.enable_output_device(vpn_dev)
    iptables.enable_output_port(def_dev, vpn_protocol, lan_addr, vpn_port)
    iptables.enable_input_device('lo')
    iptables.enable_input_states('ESTABLISHED', 'RELATED')

def forward_port(device, port):
    """Forward a port."""
    iptables.enable_input_port(device, 'tcp', port)
    iptables.enable_input_port(device, 'udp', port)

def enable_lan(device, address):
    """Enable LAN access."""
    iptables.enable_output_address(device, address)
    iptables.enable_input_address(device, address)
