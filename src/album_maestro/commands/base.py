"""Contract shared by top-level commands."""

import argparse
from abc import ABC, abstractmethod
from typing import ClassVar


class Command(ABC):
    """A command that configures its parser and handles the parsed result.

    ``configure`` runs while the parser tree is built. After argparse selects a
    command, ``run`` receives the completed namespace and performs the work.
    """

    name: ClassVar[str]
    help: ClassVar[str]

    @abstractmethod
    def configure(self, parser: argparse.ArgumentParser) -> None:
        """Add this command's arguments to its parser."""

    @abstractmethod
    def run(self, args: argparse.Namespace) -> int:
        """Run this command using parsed arguments."""


class LibraryCommand(Command):
    """Base for commands that operate on an existing music library."""

    def configure(self, parser: argparse.ArgumentParser) -> None:
        """Add the shared library option and this command's arguments."""

        parser.add_argument(
            "--library",
            default=".",
            metavar="DIRECTORY",
            help="Library directory (default: current directory)",
        )
        self.configure_arguments(parser)

    @abstractmethod
    def configure_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add this library command's command-specific arguments."""
