"""Terminal UI utilities using Rich.

Provides consistent, beautiful output across all CLI commands.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from neptune_cli.types import AiLintFinding, AiLintReport, OutputMode

# Global console instance
console = Console(stderr=True)
stdout_console = Console()


class NeptuneUI:
    """UI helper for Neptune CLI commands.

    Provides consistent styling and handles JSON vs normal output modes.
    """

    def __init__(self, output_mode: OutputMode, verbose: bool = False) -> None:
        from neptune_cli.types import OutputMode as OM

        self.output_mode = output_mode
        self.verbose = verbose
        self._is_human = output_mode != OM.JSON

    @property
    def is_human(self) -> bool:
        """Whether output is for human consumption (not JSON)."""
        return self._is_human

    def header(self, title: str) -> None:
        """Print a section header."""
        if self.is_human:
            console.print()
            console.print(Text("🔵 Neptune", style="bold blue") + Text(f" • {title}", style="bold"))

    def step(self, emoji: str, message: str) -> None:
        """Print a step/progress message."""
        if self.is_human:
            prefix = f"  {emoji} " if emoji else "  "
            console.print(f"{prefix}{message}")

    def info(self, message: str) -> None:
        """Print an info message."""
        if self.is_human:
            console.print(f"   ℹ️  {message}")

    def success(self, message: str) -> None:
        """Print a success message."""
        if self.is_human:
            console.print(f"   [green]{message}[/green]")

    def warn(self, message: str) -> None:
        """Print a warning message."""
        if self.is_human:
            console.print(f"   ⚠️  [yellow]{message}[/yellow]")

    def error(self, message: str) -> None:
        """Print an error message."""
        if self.is_human:
            console.print(f"   ❌ [red]{message}[/red]")

    def done(self) -> None:
        """Print completion message."""
        if self.is_human:
            console.print("  🎉 All set")

    def verbose_msg(self, emoji: str, message: str) -> None:
        """Print a verbose message (only if verbose mode is on)."""
        if self.is_human and self.verbose:
            prefix = f"  {emoji} " if emoji else "  "
            console.print(f"{prefix}[dim]{message}[/dim]")

    def print_json(self, data: Any) -> None:
        """Print JSON output to stdout."""
        import json

        stdout_console.print_json(json.dumps(data, default=str))


@contextmanager
def spinner(message: str, output_mode: OutputMode):
    """Context manager for a spinner that respects output mode.

    Usage:
        with spinner("Loading...", output_mode) as update:
            # do work
            update("Still loading...")
    """
    from neptune_cli.types import OutputMode as OM

    if output_mode == OM.JSON:
        # No spinner in JSON mode
        yield lambda msg: None
        return

    with Progress(
        SpinnerColumn(style="green"),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task(description=message)

        def update(new_message: str) -> None:
            progress.update(task, description=new_message)

        yield update


def print_table(
    headers: list[str],
    rows: list[list[str]],
    title: str | None = None,
    output_mode: OutputMode | None = None,
) -> None:
    """Print a formatted table.

    Args:
        headers: Column headers
        rows: List of row data
        title: Optional table title
        output_mode: Output mode (skips if JSON)
    """
    from neptune_cli.types import OutputMode as OM

    if output_mode == OM.JSON:
        return

    table = Table(title=title, show_header=True, header_style="bold")

    for header in headers:
        table.add_column(header)

    for row in rows:
        table.add_row(*row)

    console.print(table)


def print_lint_report(ui: NeptuneUI, report: AiLintReport, output_mode: OutputMode) -> None:
    """Print AI lint report in human-readable format."""
    from neptune_cli.types import OutputMode as OM

    if output_mode == OM.JSON:
        return

    if not report.errors and not report.warnings and not report.suppressed:
        return

    console.print()
    ui.header("AI Lint Report")
    console.print()

    if report.summary.blocking:
        ui.warn("Blocking AI lint findings detected")
    else:
        ui.step("", "No blocking findings detected")

    _render_lint_section(ui, "Errors", report.errors, "red")
    _render_lint_section(ui, "Warnings", report.warnings, "yellow")
    _render_lint_section(ui, "Suppressed", report.suppressed, "cyan")

    if report.config.block_on_warnings:
        ui.step("", "Repo config is set to block on warnings (block_on_warnings = true)")

    if report.config.suppressed_codes:
        ui.step("", f"Suppressed rules: {', '.join(report.config.suppressed_codes)}")

    console.print()


def _render_lint_section(ui: NeptuneUI, label: str, findings: list[AiLintFinding], color: str) -> None:
    """Render a section of lint findings as a table."""
    if not findings:
        return

    ui.step("", f"{label} ({len(findings)})")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Category")
    table.add_column("Code")
    table.add_column("Message")
    table.add_column("Path")
    table.add_column("Suggestion")

    for finding in findings:
        table.add_row(
            _category_label(finding.category),
            finding.code,
            Text(finding.message, style=color),
            finding.path or "-",
            finding.suggestion or "-",
        )

    console.print(table)
    console.print()


def _category_label(category) -> str:
    """Get human-readable label for lint category."""
    from neptune_cli.types import AiLintCategory

    labels = {
        AiLintCategory.ARCHITECTURE: "Architecture",
        AiLintCategory.RESOURCE_SUPPORT: "Resource Support",
        AiLintCategory.WORKLOAD_SUPPORT: "Workload Support",
        AiLintCategory.CONFIGURATION_INVALID: "Configuration Invalid",
        AiLintCategory.UNKNOWN: "Other",
    }
    return labels.get(category, "Other")


def assess_lint_gate(
    report: AiLintReport,
    allow_errors: bool = False,
    allow_warnings: bool = False,
) -> tuple[bool, list[str]]:
    """Assess whether lint findings should block deployment.

    Returns:
        Tuple of (is_blocking, list of reasons)
    """
    from neptune_cli.types import LintGateAssessment

    reasons: list[str] = []

    error_count = len(report.errors)
    if error_count > 0 and not allow_errors:
        s = "" if error_count == 1 else "s"
        reasons.append(f"{error_count} blocking error{s} reported by AI lint")

    warning_count = len(report.warnings)
    if report.config.block_on_warnings and warning_count > 0 and not allow_warnings:
        s = "" if warning_count == 1 else "s"
        reasons.append(f"{warning_count} warning{s} with block_on_warnings enabled")

    return LintGateAssessment(blocking=len(reasons) > 0, reasons=reasons)


def confirm(prompt: str, default: bool = True) -> bool:
    """Ask for user confirmation.

    Returns default if not in interactive mode.
    """
    if not sys.stdin.isatty():
        return default

    from rich.prompt import Confirm

    return Confirm.ask(prompt, default=default, console=console)


def prompt_input(prompt: str, default: str = "") -> str:
    """Prompt for text input."""
    from rich.prompt import Prompt

    return Prompt.ask(prompt, default=default, console=console)


def prompt_password(prompt: str) -> str:
    """Prompt for password input (hidden)."""
    from rich.prompt import Prompt

    return Prompt.ask(prompt, password=True, console=console)


def prompt_select(prompt: str, choices: list[str], default: int = 0) -> int:
    """Prompt to select from a list of choices.

    Returns the index of the selected choice.
    """
    console.print(f"\n{prompt}")
    for i, choice in enumerate(choices):
        marker = ">" if i == default else " "
        console.print(f"  {marker} [{i + 1}] {choice}")

    while True:
        response = prompt_input(f"Enter choice [1-{len(choices)}]", str(default + 1))
        try:
            idx = int(response) - 1
            if 0 <= idx < len(choices):
                return idx
        except ValueError:
            pass
        console.print(f"[red]Please enter a number between 1 and {len(choices)}[/red]")


def print_diff(old_content: str, new_content: str, filename: str) -> None:
    """Print a diff between old and new content."""
    from difflib import unified_diff

    diff = list(
        unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
        )
    )

    if not diff:
        return

    console.print(f"\n--- {filename} ---")
    for line in diff[:60]:  # Limit output
        if line.startswith("+") and not line.startswith("+++"):
            console.print(f"[green]{line.rstrip()}[/green]")
        elif line.startswith("-") and not line.startswith("---"):
            console.print(f"[red]{line.rstrip()}[/red]")
        else:
            console.print(line.rstrip())

    if len(diff) > 60:
        console.print("... (truncated preview)")

    console.print()
