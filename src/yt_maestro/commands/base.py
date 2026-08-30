"""Contract shared by top-level commands and nested command operations."""

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
