from dataclasses import dataclass
from typing import List, Union
import subprocess


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def success(self) -> bool:
        return self.returncode == 0


def run_command(
    command: Union[str, List[str]], shell: bool = False, timeout: int | None = None, cwd: str | None = None
) -> CommandResult:
    """
    Run a command and capture stdout, stderr, and return code.

    Args:
        command: Command as string (if shell=True) or list of args
        shell: Whether to run through shell (use False for security)
        timeout: Optional timeout in seconds

    Returns:
        CommandResult with returncode, stdout, stderr
    """
    result = subprocess.run(
        command,
        shell=shell,
        capture_output=True,  # Captures both stdout and stderr
        text=True,  # Returns strings instead of bytes
        timeout=timeout,
        cwd=cwd,
    )

    return CommandResult(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
