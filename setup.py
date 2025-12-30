"""
Setup script for devgen package.
"""

from setuptools import find_packages, setup

setup(
    name="devgen-cli",
    version="0.2.4",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "anthropic>=0.75.0",
        "google-generativeai>=0.8.5",
        "jinja2>=3.1.6",
        "openai>=2.11.0",
        "pyyaml>=6.0.3",
        "questionary>=2.1.1",
        "requests>=2.32.5",
        "rich>=14.2.0",
        "toml>=0.10.2",
        "typer>=0.20.0",
    ],
    entry_points={
        "console_scripts": [
            "devgen=devgen.cli.main:app",
        ],
    },
    author="Sankalp Tharu",
    author_email="sankalptharu50028@gmail.com",
    description="A collection of developer tools",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/S4NKALP/devgen",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.10",
)
