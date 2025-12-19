import asyncio
from dataclasses import dataclass


@dataclass
class CommandResult:
    returncode: int | None
    stdout: str
    stderr: str

    @property
    def success(self) -> bool:
        return self.returncode == 0


async def run_command(command: str | bytes, cwd: str | None = None) -> CommandResult:
    """
    Run a command and capture stdout, stderr, and return code.

    Args:
        command: Command as string (if shell=True) or list of args
        shell: Whether to run through shell (use False for security)
        timeout: Optional timeout in seconds

    Returns:
        CommandResult with returncode, stdout, stderr
    """
    proc = await asyncio.create_subprocess_shell(
        command,
        stderr=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        cwd=cwd,
    )

    stdout, stderr = await proc.communicate()

    return CommandResult(returncode=proc.returncode, stdout=stdout.decode(), stderr=stderr.decode())
