# DevGen

<div align="center">

**AI-Powered Git & Project Workflows in One CLI**

Stop wasting time on repetitive tasks. DevGen automates commits, changelogs, `.gitignore`, and license files using AI — from cloud providers or a local Ollama model.

> PyPI didn't allow the original name, so you'll find it as **devgen-cli** on PyPI

> <a href="https://pypi.org/project/devgen-cli"><img src="https://img.shields.io/pypi/v/devgen-cli?color=blue&label=PyPI&logo=pypi&logoColor=white" alt="PyPI"></a>
> <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python">
> <a href="https://github.com/S4NKALP/DevGen/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-GPL--3.0--or--later-blue.svg" alt="License"></a>
> <a href="https://github.com/S4NKALP/DevGen/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/S4NKALP/DevGen/ci.yml?branch=main&label=CI" alt="CI"></a>
> <a href="https://github.com/S4NKALP/DevGen/actions/workflows/pre-commit.yml"><img src="https://img.shields.io/github/actions/workflow/status/S4NKALP/DevGen/pre-commit.yml?branch=main&label=Pre-Commit" alt="Pre-Commit"></a>

</div>

## Why DevGen

DevGen is a CLI for the parts of development that should be invisible. It writes Conventional Commits from your diff, drafts SemVer changelogs, fetches `.gitignore` and license templates, and routes everything through whichever AI provider you prefer — including a fully local Ollama model if you don't want to send code to the cloud.

## Features

- **AI-Powered Commits** — Conventional Commit messages generated from your staged diff, grouped by directory, with optional emoji prefixes.
- **Multiple Providers** — Google Gemini, OpenAI, Anthropic, OpenRouter, HuggingFace, and local Ollama, all behind one CLI.
- **Smart Caching** — `.gitignore` and license templates are cached for offline use; AI responses are de-duplicated.
- **Conventional Changelogs** — `feat`, `fix`, `refactor`, `perf`, `docs`, `test`, `build`, `ci`, `chore`, `style`, and a `BREAKING CHANGES` section.
- **Project Scaffolding** — Pull `.gitignore` from GitHub's collection and drop in SPDX license files (MIT, Apache-2.0, GPL-3.0, AGPL-3.0, BSD, MPL-2.0, …).
- **Custom Templates** — Override the commit-message prompt via a `.tpl` file in your config.
- **Interactive Setup** — `devgen setup` walks you through provider + API key + options.
- **Undo Support** — `devgen commit undo` rolls back the last AI commit while keeping changes staged.
- **Token-Limit Aware** — When a diff exceeds a model's context window, you get a single actionable error with `--max-groups` and `--max-diff-size` hints.

## Supported AI Providers

| Provider | Notes |
|---|---|
| **Google Gemini** | Default-friendly, generous free tier |
| **OpenAI** | GPT-4o, GPT-4.1, o-series |
| **Anthropic** | Claude 3.5 / 3.7 / 4 |
| **OpenRouter** | Single key, many models |
| **HuggingFace** | Inference API |
| **Ollama** | Fully local, no API key, no data leaves your machine |

## Installation

```bash
# Recommended: isolated environment
pipx install devgen-cli

# Or use uv for speed
uv tool install devgen-cli

# Or plain pip
pip install devgen-cli

# Shell completion (bash/zsh/fish)
devgen --install-completion
```

Requires **Python 3.10 or newer**.

## Quick Start

```bash
# 1. Configure a provider and API key
devgen setup config

# 2. Stage your work as usual
git add .

# 3. Let DevGen write the commit message
devgen commit run

# 4. Or preview first, then commit
devgen commit run --dry-run
devgen commit run --push
```

## Commands

| Command | Description |
|---|---|
| `devgen setup config` | Interactive provider / API key / options wizard |
| `devgen commit run` | Stage, generate message, commit (optionally `--push`, `--check`, `--dry-run`) |
| `devgen commit undo` | Undo the last AI commit, keep changes staged |
| `devgen changelog` | Generate a Conventional Commits changelog from recent history |
| `devgen release-notes` | Generate release notes for a version range |
| `devgen gitignore list` | List available GitHub `.gitignore` templates |
| `devgen gitignore add <name> …` | Add `.gitignore` entries to the current project |
| `devgen license list` | List available SPDX licenses |
| `devgen license add <spdx>` | Add a LICENSE file to the current project |

Run `devgen <command> --help` for full options on any subcommand.

## Custom Templates

DevGen uses `.tpl` files for its commit prompt. To override the default, set `custom_template` in your config (see `devgen config info`) and point it at a `.tpl` file with `{{ diff_text }}`, `{{ context }}`, `{{ group_name }}`, and the conditional `{% if use_emoji %}` block.

Example minimal template:

```
{{ diff_text }}
Summarize the change above in one Conventional Commit line.
```

## Architecture

DevGen is built around a small set of composable components:

- **`BaseProvider`** — abstract base for every AI provider; handles API-key validation, token-limit detection, and error wrapping. Adding a new provider is one subclass with a single `_generate()` method.
- **`GitOperator`** — all `subprocess` calls to `git` live here, behind a `GitError` exception.
- **`DiffBuilder` / `FileGrouper` / `ManifestInspector`** — split a staged diff into per-directory groups with compact project context, so the model sees a focused slice instead of a wall of text.
- **`Section` enum** — single source of truth for changelog ordering and emoji, shared by `ChangelogGenerator` and `ReleaseNotesGenerator`.

The CLI entry point is `devgen.cli.main:app` (Typer), exposed as the `devgen` script.

## Development

```bash
git clone https://github.com/S4NKALP/DevGen.git
cd DevGen
uv sync --all-extras --dev      # install runtime + dev deps
uv run pre-commit run --all-files
uv run devgen --help
```

The project uses `uv` for dependency management, `ruff` for lint + format, and `pyright` for type checking. CI runs all three on Python 3.10 through 3.13 (see `.github/workflows/ci.yml`).

## Contributing

Issues and PRs welcome. Please run `uv run pre-commit run --all-files` before opening a PR so CI stays green.

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).

## Acknowledgments

Built on the shoulders of:

- **Typer** & **Rich** — CLI and terminal UI
- **Questionary** — interactive prompts
- **Jinja2** — template rendering under the hood
- **Google Gemini**, **OpenAI**, **Anthropic**, **OpenRouter**, **HuggingFace**, and **Ollama** — AI providers
- **Ruff** — lint and format

<div align="center">
Made with ❤️ by <a href="https://github.com/S4NKALP">Sankalp</a>
</div>
