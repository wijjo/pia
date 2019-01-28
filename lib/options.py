"""Runtime options."""


# Attributes set by the CLI after parsing arguments
# Initialized here mainly to humor pylint.
#TODO: this is silly, and requires keeping this file in sync with the CLI.
HELP_TOPICS = []
DRYRUN = False
PROTOCOL = None
VERBOSE = False
NEW_PORT = None
USER_ONLY = None
REFRESH_OPENVPN_FILES = None
CREATE_USER_CONFIG = None
WAIT = None
OPTION_SET = None
FORCE = None
