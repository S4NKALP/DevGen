# 📋 Project Roadmap & TODOs

This document outlines future improvements, features, and technical debt for `devgen`.

## 🚀 Priority: Short-Term (Reliability & DX)
- [ ] **Full Test Suite**: Implement `pytest` for all modules, especially `commit_generator` and `utils`.
- [x] **Interactive Commit Review**: Add a `--check` flag to `devgen commit run` that allows users to approve/edit the AI message before committing.
- [ ] **Project-Level Config**: Support `.devgen.yaml` in the repository root that overrides global `~/.devgen.yaml`.
- [ ] **Improved Gitignore Detection**: Auto-detect project type (Python, Node, Go) and suggest relevant `.gitignore` templates during `devgen gitignore run`.

## 🤖 AI & Intelligence
- [x] **Custom Prompts**: Allow users to define their own Jinja2 templates for commits in the config file(~/.devgen.yaml).
- [x] **Context-Aware Commits**: Send the manifest file (`package.json`, `pyproject.toml`) to the AI to provide better context for dependency changes.
- [ ] **Token Usage Dashboard**: Add a `devgen config tokens` command to estimate or track AI token consumption.
- [ ] **More Providers**: Add support for **Mistral**, **Cohere**, and **Groq** for faster/cheaper generations.

## 🛠️ Developer Experience (DX)
- [ ] **Pre-commit Hook Integration**: Provide a command to easily install `devgen` as a pre-commit hook.
- [x] **Shell Completion**: Implement `typer` shell completion for `bash`, `zsh`, and `fish`.
- [x] **Commit Undo**: `devgen commit undo` to easily revert the last AI-generated commit and unstage files.
- [x] **Multi-Group Commits**: Better handling of repositories where changes are spread across many unrelated directories.

## 🏗️ Refactoring & Technical Debt
- [ ] **Code Split**: Move CLI logic out of `devgen/cli` into separate service classes to improve testability.
- [ ] **Consistent Logging**: Standardize log output across all modules.
- [ ] **API Documentation**: Use Sphinx or MkDocs to generate documentation for the core modules.

## 🌍 Ecosystem
- [ ] **GitHub Action**: Create an official `devgen` GitHub Action for automated changelog updates on PR merge.
- [ ] **VS Code Extension**: A simple extension to trigger `devgen commit` from the sidebar.
