# MCP Server Markup Language (MCPML)

A Python framework for building [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol/docs) servers with CLI and OpenAI Agent support.

## Features

- 🚀 **MCP Server Framework**: Build MCP-compliant servers in Python
- 🔧 **CLI Tools**: All server capabilities exposed as CLI commands
- 🤖 **OpenAI Agent SDK Support**: Implement tools as OpenAI agents Or as simple python functions
- 🔄 **Agent-to-MCP Integration**: Agents can consume MCP services via config
- 🛠️ **Extensible Architecture**: Easily add custom tools and services
- 🔌 **Dynamic Loading**: Support for custom agent types and tool implementations from the execution directory
- 📦 **Structured Output**: Support for structured output using Pydantic models

## Installation

```bash
pip install git+https://github.com/a5c-ai/mcpml#egg=mcpml
```

## .env

```
OPENAI_API_KEY=your_openai_api_key
```

or 

```
AZURE_OPENAI_ENDPOINT=https://your-azure-openai-endpoint.openai.azure.com
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
OPENAI_API_VERSION=api_version

```

## Usage

```bash
mcpml --help
```

```bash
mcpml run
```
mcpml.yaml is the default config file for the MCPML server.

```bash
mcpml run --config https://github.com/a5c-ai/some-mcpml-server
```

```bash
mcpml --config mcpml.yaml tools some-tool run --arg1 value1 --arg2 value2
```

## License

MIT
