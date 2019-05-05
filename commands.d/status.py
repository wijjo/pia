"""Status command."""

from lib import tools
from lib import provider

name = 'status'
help = 'display connection status'
arguments = []

def execute(options):
    provider_tool = provider.Tool()
    pid = tools.get_running_pid(pid_path=provider_tool.pid_path)
    def _path(path):
        path2 = tools.shorten_path(path)
        if not os.path.exists(path):
            return tools.DisplayItem(path2, tools.DisplayItem(' (missing)', attributes='red'))
        return path2
    tools.display_table([
        ['Server status', 'running' if pid else 'not running'],
        ['Process ID', str(pid) if pid is not None else '-'],
        ['Base directory', _path(provider_tool.base_dir)],
        ['Configuration directory', _path(provider_tool.config_dir)],
        ['Downloads directory', _path(provider_tool.download_dir)],
        ['State directory', _path(provider_tool.state_dir)],
        ['Configuration file', _path(provider_tool.config_path)],
        ['Credentials file', _path(provider_tool.cred_path)],
        ['Log file', _path(provider_tool.log_path)],
        ['State file', _path(provider_tool.state_path)],
        ['Process PID file', _path(provider_tool.pid_path)],
        ['Forwarded port file', _path(provider_tool.port_path)],
    ] + [[label, _path(path)] for label, path in provider_tool.provider.iterate_status_paths()],
    header=['Description', 'Data'])
