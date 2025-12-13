# DevGen

<div align="center">

> **Your AI Powerhouse for Git & Project Management.**
> Stop wasting time on repetitive tasks. Automate your commits, changelogs, and project essentials with a single CLI.
>
> PyPI didn't allow the original name, so you'll find it as **devgen-cli** on PyPI

<a href="https://pypi.org/project/devgen-cli"><img src="https://img.shields.io/pypi/v/devgen-cli?color=blue&label=PyPI&logo=pypi&logoColor=white" alt="PyPI"></a>
<img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python">
<a href="https://github.com/S4NKALP/DevGen/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-GPL--3.0--or--later-blue.svg" alt="License"></a>

</div>

---

**DevGen** isn't just another CLI tool it's your development workflow on steroids. By leveraging state of the art AI models, DevGen turns tedious manual tasks into one click magic. From semantic commit messages to comprehensive release notes, DevGen handles the boring stuff so you can focus on building.

## ⚡ Why DevGen?

**🧠 AI Brain**
Semantic commit messages powered by Gemini, OpenAI, Claude, HuggingFace, and OpenRouter. It reads your diffs and understands your code.

**🚀 Battle Tested**
Generates **Conventional Commits** and **Semantic Versioning** compliant changelogs that actually make sense.

**⚡ Lightning Fast**
Smart caching and async operations mean you never wait longer than necessary.

**Project Essentials**
Quickly add `.gitignore` and license files to your existing projects. Access cached templates instantly, even without internet.

**🛠️ Zero Friction**
Interactive setup gets you running in seconds.

## 📦 Installation

Get started in seconds.

```bash
# Recommended: Install via pipx for an isolated environment
pipx install devgen-cli

# Or use uv for blazing speed
uv tool install devgen-cli

# Standard pip install
pip install devgen-cli
```

## 🚀 Quick Start

**1. Initialize & Configure**
Tell DevGen which AI provider to use.

```bash
devgen setup config
```

**2. Stage & Commit**
Stage your files and let AI write the message.

```bash
git add .
devgen commit run
```

_Boom. Done._

## 💡 Feature Deep Dive

### 🤖 AI Powered Commits

Stop writing "fix bug" or "wip". DevGen analyzes your staged changes, groups them by component, and generates meaningful, semantic commit messages.

```bash
# Preview what DevGen will generate
devgen commit run --dry-run

# Commit and push in one go
devgen commit run --push
```

### 📝 Changelogs & Release Notes

Turn your git history into beautiful, readable documentation.

```bash
# Generate a changelog from the last tag
devgen changelog generate

# Create release notes for v2.0.0
devgen release notes --version 2.0.0
```

### 🛡️ Essential Files

Don't waste time searching for templates. Generate the essential files for your project instantly.

```bash
# Interactive search for gitignore templates
devgen gitignore generate

# Generate a license interactively
devgen license generate
```

## ⚙️ Configuration

Your settings live in `~/.devgen.yaml`. You can tweak your AI provider, model, and preferences there.

| Option     | Description                                                  |
| :--------- | :----------------------------------------------------------- |
| `provider` | `gemini`, `openai`, `anthropic`, `huggingface`, `openrouter` |
| `model`    | Specific model name (e.g., `gemini-2.5-flash`, `gpt-4o`)     |
| `emoji`    | Enable/disable gitmojis in commits (`true`/`false`)          |

## 🤝 Contributing

We love contributions! Found a bug? Want a new feature? Open an issue or submit a PR.

## � Acknowledgments

DevGen wouldn't be possible without these amazing open-source projects and AI providers:

- **[Typer](https://typer.tiangolo.com/)** & **[Rich](https://rich.readthedocs.io/)** for building the beautiful, intuitive, and responsive CLI interface.
- **[Questionary](https://github.com/tmbo/questionary)** for creating interactive, user-friendly prompts and selection menus.
- **[Jinja2](https://jinja.palletsprojects.com/)** for the powerful template engine used to generate files and messages.
- **[Google Gemini](https://deepmind.google/technologies/gemini/)**, **[OpenAI](https://openai.com/)**, **[Anthropic](https://www.anthropic.com/)**, **[HuggingFace](https://huggingface.co/)**, and **[OpenRouter](https://openrouter.ai/)** for providing the advanced AI models that power the semantic generation features.

## �📝 License

Proudly open source under the [GPL-3.0-or-later](LICENSE) License.

---

<div align="center">
Made with ❤️ by <a href="https://github.com/S4NKALP">Sankalp</a>
</div>
