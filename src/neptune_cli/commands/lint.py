"""Lint command - Run AI lint on the project."""

from __future__ import annotations

from pathlib import Path

import click

from neptune_cli.types import OutputMode, LintResult
from neptune_cli.ui import NeptuneUI, assess_lint_gate, print_lint_report, spinner
from neptune_cli.utils import resolve_project_name


@click.command("lint")
@click.option(
    "--allow-ai-errors",
    is_flag=True,
    help="Ignore blocking AI lint errors",
)
@click.option(
    "--allow-ai-warnings",
    is_flag=True,
    help="Ignore blocking AI lint warnings",
)
@click.pass_context
def lint_command(
    ctx: click.Context,
    allow_ai_errors: bool,
    allow_ai_warnings: bool,
) -> None:
    """Run the AI linter against the current project."""
    from neptune_cli.services.lint import run_ai_lint

    output_mode = ctx.obj.get("output_mode", OutputMode.NORMAL)
    verbose = ctx.obj.get("verbose", False)
    working_dir = ctx.obj.get("working_directory", Path.cwd())
    ui = NeptuneUI(output_mode, verbose=verbose)

    if output_mode != OutputMode.JSON:
        ui.header("AI Lint")

    # Resolve project name
    try:
        project_name = resolve_project_name(working_dir)
    except Exception:
        project_name = working_dir.name

    # Check for neptune.json
    spec_path = working_dir / "neptune.json"
    if not spec_path.exists():
        message = f"Missing {spec_path}. Run `neptune generate spec` before linting."
        if output_mode == OutputMode.JSON:
            result = LintResult(
                ok=False,
                project=project_name,
                ai_lint_report=None,
                messages=[message],
                next_action_command="neptune generate spec",
            )
            ui.print_json(result.model_dump())
        else:
            ui.warn("neptune.json not found in the current workspace")
            ui.info(f"Expected to find {spec_path}")
            ui.info("Run `neptune generate spec` to create it before linting.")
        ctx.exit(1)

    # Run lint using service
    try:
        with spinner("Analyzing project with AI lint...", output_mode):
            report = run_ai_lint(working_dir)
    except Exception as e:
        if output_mode == OutputMode.JSON:
            result = LintResult(
                ok=False,
                project=project_name,
                ai_lint_report=None,
                messages=[f"Failed to run AI lint: {e}"],
                next_action_command="neptune lint",
            )
            ui.print_json(result.model_dump())
        else:
            ui.error(f"Failed to run AI lint: {e}")
        ctx.exit(1)

    # Assess if findings are blocking
    assessment = assess_lint_gate(report, allow_ai_errors, allow_ai_warnings)

    if output_mode == OutputMode.JSON:
        result = LintResult(
            ok=not assessment.blocking,
            project=project_name,
            ai_lint_report=report,
            messages=assessment.reasons if assessment.blocking else None,
            next_action_command="neptune lint" if assessment.blocking else "neptune deploy",
        )
        ui.print_json(result.model_dump(mode="json"))
        return

    # Human-readable output
    print_lint_report(ui, report, output_mode)

    if assessment.blocking:
        for reason in assessment.reasons:
            ui.warn(f"Blocking: {reason}")
        ui.info("Use --allow-ai-errors / --allow-ai-warnings to override.")
        ctx.exit(1)
    else:
        ui.success("✅ No blocking AI lint findings")
