# DevGen

<div align="center">

<img src="https://img.shields.io/pypi/v/devgen?color=blue&label=PyPI&logo=pypi&logoColor=white" alt="PyPI">
<img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python">
<a href="https://github.com/S4NKALP/devgen/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-GPL--3.0--or--later-blue.svg" alt="License"></a>

</div>

**DevGen** is an AI-powered developer toolkit that automates common Git and project management tasks. Generate semantic commit messages, changelogs, release notes, `.gitignore` files, and licenses—all from a single unified CLI.

## ✨ Features

- 🚀 **AI-Powered Commit Messages** - Automatically generate semantic commit messages from your staged changes using AI
- 📝 **Changelog Generation** - Create changelogs from git history using conventional commits
- 🚀 **Release Notes** - Generate clean, emoji-enhanced release notes for your releases
- 🙈 **Gitignore Templates** - Generate `.gitignore` files from GitHub's official templates
- 📄 **License Generation** - Quickly generate open source licenses with interactive setup
- ⚙️ **Multi-Provider AI Support** - Works with Gemini, OpenAI, Anthropic, HuggingFace, and OpenRouter

## 📦 Installation

```bash
# Stable release from PyPI
pip install devgen-cli

# Using pipx (recommended for isolated CLI)
pipx install devgen-cli

# Using uv (fast Python package manager)
uv tool install devgen-cli
```

## 🚀 Quick Start

### 1. Initial Setup

Configure your AI provider and API key:

```bash
devgen setup config
```

This will create a configuration file at `~/.devgen.yaml` with your preferred AI provider, model, and API key.

### 2. Generate Commit Messages

Stage your changes and let DevGen generate semantic commit messages:

```bash
# Dry run to preview commit messages
devgen commit run --dry-run

# Actually commit with AI-generated messages
devgen commit run

# Commit and automatically push
devgen commit run --push

# Force regeneration of commit messages
devgen commit run --force-rebuild
```

**How it works:**

- DevGen detects all staged and unstaged changes
- Groups files by directory
- Generates semantic commit messages for each group using AI
- Follows [Conventional Commits](https://www.conventionalcommits.org/) format

**Additional commit commands:**

```bash
# View cached commit messages
devgen commit list-cached

# Clear the commit cache
devgen commit clear-cache

# Check what files are staged
devgen commit validate
```

### 3. Generate Changelogs

Create changelogs from your git history:

```bash
# Generate changelog from last tag to HEAD
devgen changelog generate

# Generate from a specific reference
devgen changelog generate --from v1.0.0

# Output to a custom file
devgen changelog generate --output CHANGES.md
```

The changelog follows Semantic Release conventions, categorizing commits into:

- **BREAKING CHANGES**
- **Features**
- **Bug Fixes**
- **Documentation**
- **Other Changes**

### 4. Generate Release Notes

Create release notes for your releases:

```bash
# Generate release notes
devgen release notes --version 1.4.0

# Custom output file
devgen release notes --version 1.4.0 --output RELEASE.md

# From a specific reference
devgen release notes --version 1.4.0 --from v1.3.0
```

### 5. Generate .gitignore Files

Create `.gitignore` files from GitHub templates:

```bash
# Interactive mode (search and select templates)
devgen gitignore generate

# Specify templates directly
devgen gitignore generate Python Node Docker

# List available templates
devgen gitignore list

# Use cached templates (offline mode)
devgen gitignore generate --offline Python
```

**Options:**

- `--append` / `--overwrite` - Append to or overwrite existing `.gitignore`
- `--output` - Specify output file path (default: `.gitignore`)
- `--offline` - Use only cached templates

### 6. Generate Licenses

Generate open source licenses interactively:

```bash
devgen license generate
```

This will:

1. Show available licenses (MIT, Apache-2.0, GPL-3.0, etc.)
2. Prompt for author name
3. Prompt for year (defaults to current year)
4. Generate the license file

**Available licenses:**

- MIT
- Apache-2.0
- GPL-2.0, GPL-3.0
- LGPL-2.1
- AGPL-3.0
- BSD-2-Clause, BSD-3-Clause
- MPL-2.0
- EPL-2.0
- BSL-1.0
- CC0-1.0
- Unlicense

## ⚙️ Configuration

Configuration is stored in `~/.devgen.yaml`. You can edit it manually or use the interactive setup:

```bash
devgen setup config
```

**Configuration options:**

- `provider` - AI provider: `gemini`, `openai`, `anthropic`, `huggingface`, or `openrouter`
- `model` - Model name (e.g., `gemini-2.5-flash`, `gpt-4`, `claude-3-opus`)
- `api_key` - Your API key
- `emoji` - Enable/disable emojis in commit messages (default: `true`)

## 📋 Command Reference

### Commit Commands

```bash
devgen commit run [--dry-run] [--push] [--debug] [--force-rebuild]
devgen commit validate
devgen commit list-cached
devgen commit clear-cache
```

### Changelog Commands

```bash
devgen changelog generate [--output FILE] [--from REF]
```

### Release Commands

```bash
devgen release notes [--version VERSION] [--output FILE] [--from REF]
```

### Gitignore Commands

```bash
devgen gitignore generate [TEMPLATES...] [--output FILE] [--append/--overwrite] [--offline]
devgen gitignore list [--cached]
```

### License Commands

```bash
devgen license generate [--output FILE]
```

### Setup Commands

```bash
devgen setup config
```

## 🎯 Use Cases

- **Automated Commit Workflow**: Let AI analyze your changes and generate meaningful commit messages
- **Release Preparation**: Automatically generate changelogs and release notes from git history
- **Project Setup**: Quickly add `.gitignore` and license files to new projects
- **CI/CD Integration**: Use in scripts to automate documentation generation

## 🔧 Requirements

- Python 3.10 or higher
- Git repository (for commit/changelog/release features)
- API key for your chosen AI provider

## 📝 License

This project is licensed under the GPL-3.0-or-later License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📚 Links

- **Homepage**: [https://github.com/S4NKALP/devgen](https://github.com/S4NKALP/devgen)
- **PyPI**: [https://pypi.org/project/devgen](https://pypi.org/project/devgen)

## 🙏 Acknowledgments

- Uses GitHub's official [gitignore templates](https://github.com/github/gitignore)
- Follows [Conventional Commits](https://www.conventionalcommits.org/) specification
