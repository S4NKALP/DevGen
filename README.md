# DevGen
<div align="center">
  
**Your AI Powerhouse for Git & Project Management.**
Stop wasting time on repetitive tasks. Automate your commits, changelogs, and project essentials with a single CLI.
  
> PyPI didn't allow the original name, so you'll find it as **devgen-cli** on PyPI
> <a href="https://pypi.org/project/devgen-cli"><img src="https://img.shields.io/pypi/v/devgen-cli?color=blue&label=PyPI&logo=pypi&logoColor=white" alt="PyPI"></a>
> <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python">
> <a href="https://github.com/S4NKALP/DevGen/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-GPL--3.0--or--later-blue.svg" alt="License"></a>
> <a href="https://github.com/S4NKALP/DevGen/actions/workflows/publish.yml"><img src="https://img.shields.io/github/actions/workflow/status/S4NKALP/DevGen/publish.yml?branch=main&label=Build" alt="Build Status"></a>
> <a href="https://github.com/S4NKALP/DevGen/actions/workflows/pre-commit.yml"><img src="https://img.shields.io/github/actions/workflow/status/S4NKALP/DevGen/pre-commit.yml?branch=main&label=Pre-Commit" alt="Pre-Commit Status"></a>
  
</div>

## Overview

DevGen is an innovative CLI tool designed to streamline your development workflow by automating repetitive tasks such as commits, changelogs, and project essentials. Leveraging state-of-the-art AI models, DevGen transforms tedious manual tasks into one-click magic, enabling you to focus on building and improving your projects.

## Features

- **AI-Powered Commits**: Generate semantic, context-aware commit messages using AI models from Gemini, OpenAI, Anthropic, HuggingFace, and OpenRouter.
- **Battle-Tested**: Produces Conventional Commits and Semantic Versioning compliant changelogs that make sense.
- **Lightning Fast**: Utilizes smart caching and async operations for speedy performance.
- **Project Essentials**: Quickly add `.gitignore` and license files to your projects, with access to cached templates even offline.
- **Zero Friction**: Interactive setup gets you running in seconds.
- **Customizable**: Define your own commit message structure using Jinja2 templates.

## Tech Stack

- **Python 3.10+**: The primary programming language.
- **Typer & Rich**: For building the intuitive and responsive CLI interface.
- **Questionary**: For interactive prompts and selection menus.
- **Jinja2**: For the powerful template engine.
- **AI Models**: From Google Gemini, OpenAI, Anthropic, HuggingFace, and OpenRouter.
- **Rich 14.3.3**: For text-based user interfaces.
- **Uv**: For dependency management and installation.
- **OpenAI 2.29.0**: For AI model integration.
- **Anthropic 0.86.0**: For AI model integration.
- **Ruff 0.15.7**: For code linting and formatting.
- **Google GenAI 1.68.0**: For AI model integration.

## Installation

Get started with DevGen in seconds using one of the following methods:

```bash
# Recommended: Install via pipx for an isolated environment
pipx install devgen-cli

# Or use uv for blazing speed
uv tool install devgen-cli

# Standard pip install
pip install devgen-cli

# Enable Shell Completion (bash/zsh/fish)
devgen --install-completion
```

## Usage

### Initialize & Configure

Tell DevGen which AI provider to use.

```bash
devgen setup config
```

### Stage & Commit

Stage your files and let AI write the message.

```bash
git add .
devgen commit run
```

### Preview Commit Message

Preview what DevGen will generate without committing.

```bash
devgen commit run --dry-run
```

### Commit and Push

Commit and push in one go.

```bash
devgen commit run --push
```

### Review and Edit

Review and edit AI messages before committing.

```bash
devgen commit run --check
```

### Undo Last Commit

Undo the last AI commit and keep changes staged.

```bash
devgen commit undo
```

## API Documentation

For more detailed API information and available commands, please refer to the [DevGen CLI Documentation](https://devgen.readthedocs.io/).

## Contributing

We welcome contributions! Found a bug? Want a new feature? Open an issue or submit a PR.

## Development

To set up the development environment, follow these steps:

1. Clone the repository: `git clone https://github.com/S4NKALP/DevGen.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Run tests: `pytest`

## Deployment

To deploy DevGen, follow these steps:

1. Build the package: `python setup.py sdist`
2. Upload to PyPI: `twine upload dist/*`

## Troubleshooting

If you encounter any issues, please refer to our [Troubleshooting Guide](https://devgen.readthedocs.io/en/latest/troubleshooting.html).

## License

Proudly open source under the [GPL-3.0-or-later](LICENSE) License.

## Acknowledgments

DevGen wouldn't be possible without these amazing open-source projects and AI providers:

- **Typer** & **Rich** for the CLI interface.
- **Questionary** for interactive prompts.
- **Jinja2** for the template engine.
- **Google Gemini**, **OpenAI**, **Anthropic**, **HuggingFace**, and **OpenRouter** for the AI models.

<div align="center">
Made with ❤️ by <a href="https://github.com/S4NKALP">Sankalp</a>
</div>