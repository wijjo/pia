"""IPTables interface."""

from . import tools

def run(*args):
    tools.run_command('sudo', 'iptables', *args)

def reset_input():
    run('--policy', 'INPUT', 'ACCEPT')

def reset_output():
    run('--policy', 'OUTPUT', 'ACCEPT')

def reset_forwarding():
    run('--policy', 'FORWARD', 'ACCEPT')

def enable_input_device(device):
    run('-A', 'INPUT', '-i', device, '-j', 'ACCEPT')

def enable_output_device(device):
    run('-A', 'OUTPUT', '-o', device, '-j', 'ACCEPT')

def enable_input_address(device, address):
    run('-A', 'INPUT', '-i', device, '-s', address, '-j', 'ACCEPT')

def enable_output_address(device, address):
    run('-A', 'OUTPUT', '-o', device, '-d', address, '-j', 'ACCEPT')

def enable_input_port(device, protocol, port):
    run('-A', 'INPUT', '-o', device,
            '-p', protocol, '--dport', port, '-j', 'ACCEPT')

def enable_output_port(device, protocol, address, port):
    run('-A', 'OUTPUT', '-o', device, '-d', address,
            '-p', protocol, '--dport', port, '-j', 'ACCEPT')

def enable_input_states(*states):
    state_string = ','.join(states)
    run('-A', 'INPUT', '-m', 'state', '--state', state_string, '-j', 'ACCEPT')

def disable_input():
    run('--policy', 'INPUT', 'DROP')

def disable_output():
    run('--policy', 'OUTPUT', 'DROP')

def disable_forwarding():
    run('--policy', 'FORWARD', 'DROP')

def clear_all():
    run('-Z')
    run('-F')
    run('-X')
