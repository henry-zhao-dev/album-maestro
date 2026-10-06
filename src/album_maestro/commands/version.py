"""Implementation of the ``album-maestro version`` command."""

import argparse
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version

from album_maestro.commands.base import Command

PACKAGE_NAME = "album-maestro"


class VersionCommand(Command):
    """Print the installed Album Maestro version."""

    name = "version"
    help = "Show the Album Maestro version."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        """Configure the version command, which takes no arguments."""

    def run(self, args: argparse.Namespace) -> int:
        """Print the installed package version."""

        try:
            current_version = package_version(PACKAGE_NAME)
        except PackageNotFoundError:
            print("Unable to determine the Album Maestro version.")
            return 1

        print(current_version)
        return 0
