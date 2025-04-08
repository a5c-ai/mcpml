import os
from setuptools import setup, find_packages

# Read dependencies from pyproject.toml
requires = [
    "fastapi>=0.95.0",
    "uvicorn>=0.21.0",
    "pydantic>=2.0.0",
    "openai>=1.0.0",
    "openai-agents>=0.0.1",
    "typer>=0.9.0",
    "python-dotenv>=1.0.0",
    "PyYAML>=6.0.2",
    "requests>=2.31.0",
    "rich>=13.3.0",
]

dev_requires = [
    "pytest>=7.0.0",
    "black>=23.0.0",
    "isort>=5.0.0",
    "mypy>=1.0.0",
    "ruff>=0.0.262",
]

# Read the README.md for the long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="mcpml",
    version="0.1.2",
    description="A Python framework for building MCP servers with CLI and OpenAI Agent support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Tal Muskal",
    author_email="tal@a5c.ai",
    url="https://github.com/a5c-ai/mcpml",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=requires,
    extras_require={
        "dev": dev_requires,
    },
    entry_points={
        "console_scripts": [
            "mcpml=mcpml.cli.main:app",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    license="MIT",
) 