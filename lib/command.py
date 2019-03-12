"""Command line sub-command handling."""

import sys
import argparse
import inspect

from . import tools

class Argument(object):
    """Positional/keyword arguments for ArgumentParser.add_argument()."""

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class SubCommand(object):
    """Base sub-command class."""

    def __init__(self, argument_parser, sub_command_argument_parsers):
        # Help needs access to CLI argument parsers.
        self.argument_parser = argument_parser
        self.sub_command_argument_parsers = sub_command_argument_parsers
        # Set during invoke_run()
        self.options = None

    def execute(self):
        """Required method to execute the sub-command."""
        raise NotImplementedError

    def invoke_run(self, options):
        """Invoke the sub-class run() method."""
        self.options = options
        try:
            if hasattr(self, 'setup'):
                self.setup()    #pylint: disable=E1101
            if hasattr(self, 'execute'):
                self.execute()  #pylint: disable=E1101
            if hasattr(self, 'cleanup'):
                self.cleanup()  #pylint: disable=E1101
        except BaseException as exc:
            tools.error(exc, fatal_error=True)


class Help(SubCommand):
    """'help' sub-command class."""

    name = 'help'
    help = 'display general or command-specific help'
    arguments = [
        Argument(
            dest='HELP_TOPICS', nargs='*',
            help='topic(s) for specific help'
        ),
    ]

    def execute(self):
        if self.options.HELP_TOPICS:
            for topic in self.options.HELP_TOPICS:
                if topic in self.sub_command_argument_parsers:
                    self.sub_command_argument_parsers[topic].print_help()
                else:
                    tools.error('Bad help topic: {}'.format(topic))
        else:
            self.argument_parser.print_help()


def process_commands(sub_command_classes, description):
    """Parse arguments and invoke the sub-command."""

    argument_parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    argument_parser.add_argument(
        '-v', '--verbose', dest='VERBOSE', action='store_true',
        help='display extra verbose information')

    argument_parser.add_argument(
        '-n', '--dry-run', dest='DRYRUN', action='store_true',
        help='preview actions by performing a dry run')

    sub_command_sub_parsers = argument_parser.add_subparsers(
        dest='COMMAND',
        metavar='COMMAND',
    )

    sub_command_argument_parsers = {}

    for name in sorted(sub_command_classes.keys()):
        cls = sub_command_classes[name]
        sub_parser = sub_command_sub_parsers.add_parser(name, help=cls.help)
        sub_command_argument_parsers[name] = sub_parser
        if hasattr(cls, 'arguments'):
            for argument in cls.arguments:
                sub_command_argument_parsers[name].add_argument(
                    *argument.args, **argument.kwargs)
    parsed_args = argument_parser.parse_args()
    if not parsed_args.COMMAND:
        argument_parser.print_help()
        sys.exit(1)
    # Make global options available globally.
    if parsed_args.VERBOSE:
        tools.VERBOSE = parsed_args.VERBOSE
    if parsed_args.DRYRUN:
        tools.DRYRUN = parsed_args.DRYRUN
    sub_command_class = sub_command_classes[parsed_args.COMMAND]
    sub_command = sub_command_class(argument_parser, sub_command_argument_parsers)
    sub_command.invoke_run()


def find_command_classes(commands, module):
    """Populate a command dictionary for a module."""
    for _name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and issubclass(obj, SubCommand):
            if hasattr(obj, 'name'):
                commands[obj.name] = obj


def main(description):
    """Main function."""
    # Find all the sub-command subclasses in this module.
    sub_command_classes = {}
    find_command_classes(sub_command_classes, sys.modules[__name__])
    process_commands(sub_command_classes, description)
