"""
MCP Server - A Python framework for building Model Context Protocol servers
"""

from mcpml.mcp_server.server import MCPServer, create_server
from mcpml.mcp_server.tools import execute_tool

# Import agent integrations for convenience
from mcpml.agent_integrations import MCPAgent, MCPOpenAIAgent

__all__ = [
    "MCPServer", 
    "create_server",
    "execute_tool",
    "MCPAgent",
    "MCPOpenAIAgent",
]

__version__ = "0.1.0"
