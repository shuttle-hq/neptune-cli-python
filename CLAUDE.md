# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Neptune CLI is a Python CLI tool and MCP (Model Context Protocol) server for interacting with Neptune (neptune.dev), a cloud deployment platform. It enables AI agents to deploy and manage containerized applications on AWS infrastructure (ECS/Fargate).

## Development Commands

```bash
# Install dependencies
uv sync

# Run the CLI
uv run neptune --help

# Run MCP server (stdio transport - default)
uv run neptune mcp

# Run MCP server (HTTP transport)
uv run neptune mcp --transport=http --host=0.0.0.0 --port=8001

# Lint and format
uv run ruff check src/
uv run ruff format src/
```

## Architecture

The codebase follows a straightforward structure:

- **cli.py**: Click-based CLI entry point with `neptune` command group (login, mcp subcommands)
- **mcp.py**: FastMCP server exposing Neptune operations as MCP tools (deploy, provision, logs, secrets, buckets)
- **client.py**: HTTP client wrapper for Neptune API using `requests` and `neptune-common` models
- **config.py**: Pydantic-based settings with JSON file persistence (`~/.config/neptune/config.json`) and env var support (`NEPTUNE_` prefix)
- **auth.py**: OAuth callback handler using a local HTTP server for browser-based login

## Key Patterns

- MCP tools return structured dicts with `status`, `message`, and `next_step` fields to guide AI agents
- All API calls use bearer token auth from `SETTINGS.access_token`
- Project configuration is defined in `neptune.json` files (validated against a remote schema)
- Deployments build Docker images locally and push to ECR

## Configuration

- Environment variables: `NEPTUNE_API_BASE_URL`, `NEPTUNE_ACCESS_TOKEN`
- Config file: `~/.config/neptune/config.json`
- Default API: `https://beta.neptune.dev/v1`
