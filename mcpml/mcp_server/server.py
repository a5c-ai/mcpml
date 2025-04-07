from __future__ import annotations

import asyncio
import importlib
import inspect
import logging
from typing import Any, Callable, Dict, List, Literal, Optional, Type, Union

from mcp import stdio_server
from pydantic import BaseModel, Field
import uvicorn

from mcpml.config.mcpml import ToolDefinition, ToolParameter, MCPMLConfig
from mcpml.mcp_server.tools import execute_tool
from mcpml.config import MCPMLConfig
logger = logging.getLogger(__name__)
from mcp.server.sse import SseServerTransport
from mcp.server.stdio import stdio_server
from mcp.server import Server as MCPServer
from mcp.types import (
    Tool,
)

class MCPMLServer:
    """
    Model Context Protocol Server implementation
    """
    _mcp_server: MCPServer
    config: MCPMLConfig
    def __init__(self, config: MCPMLConfig):
        self._mcp_server = MCPServer(name=config.name)
        self.config = config
        self._setup_handlers()
    def convert_to_mcp_schema(self, tool: ToolDefinition) -> Dict[str, Any]:
        """Convert a ToolDefinition to an MCP schema."""
        # if the tool is a function, load the implementation and get the parameters.
        # if the tool is an agent, the parameters are input:str
        if tool.type == "function":
            # load the implementation and get the parameters
            
            module_name, function_name = tool.implementation.rsplit(".", 1)
            module = importlib.import_module(module_name)
            implementation = getattr(module, function_name)
            # get the parameters from the implementation
            parameters = inspect.signature(implementation).parameters
            # convert the parameters to an MCP schema (depending on the type)
            schema = {}
            for name, param in parameters.items():
                if param.annotation == inspect.Parameter.empty:
                    schema[name] = {"type": "string"}
                elif param.annotation == str:
                    schema[name] = {"type": "string"}
                elif param.annotation == int:
                    schema[name] = {"type": "integer"}
                elif param.annotation == float:
                    schema[name] = {"type": "number"}
                else:
                    schema[name] = {"type": param.annotation.__name__}
            return schema

        else:
            return {"input": {"type": "string"}}
        
    def _setup_handlers(self) -> None:
        """Set up core MCP protocol handlers."""
        app = self._mcp_server
        # self._mcp_server.list_resources()(self.list_resources)
        # self._mcp_server.read_resource()(self.read_resource)
        # self._mcp_server.list_prompts()(self.list_prompts)
        # self._mcp_server.get_prompt()(self.get_prompt)
        @app.list_tools()
        async def list_tools() -> list[Tool]:
            """List all available tools."""
            tools = self.config.tools
            return [
                Tool(
                    name=tool.name,
                    description=tool.description,
                    inputSchema={
                        "type": "object",
                        "properties": self.convert_to_mcp_schema(tool)
                    }
                )
                for tool in tools
            ]
        
        @app.call_tool()
        async def call_tool(tool_name: str, parameters: Dict[str, Any]) -> Any:
            """Call a tool with the given name and parameters."""
            return execute_tool(tool_name, **parameters)

    def run(self, transport: Literal["stdio", "sse"] = "stdio") -> None:
        """Run the FastMCP server. Note this is a synchronous function.

        Args:
            transport: Transport protocol to use ("stdio" or "sse")
        """
        TRANSPORTS = Literal["stdio", "sse"]
        if transport not in TRANSPORTS.__args__:  # type: ignore
            raise ValueError(f"Unknown transport: {transport}")

        if transport == "stdio":
            asyncio.run(self.run_stdio_async())
        else:  # transport == "sse"
            asyncio.run(self.run_sse_async())
    async def run_stdio_async(self) -> None:
        """Run the server using stdio transport."""
        async with stdio_server() as (read_stream, write_stream):
            await self._mcp_server.run(
                read_stream,
                write_stream,
                self._mcp_server.create_initialization_options(),
            )
    async def run_sse_async(self) -> None:
        """Run the server using SSE transport."""
        from starlette.applications import Starlette
        from starlette.routing import Route, Mount

        sse = SseServerTransport("/messages/")

        async def handle_sse(request):
            async with sse.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                await self._mcp_server.run(
                    streams[0],
                    streams[1],
                    self._mcp_server.create_initialization_options(),
                )

        starlette_app = Starlette(
            debug=self.config.settings.log_level.lower() == "debug",
            routes=[
                Route("/sse", endpoint=handle_sse),
                Mount("/messages/", app=sse.handle_post_message),
            ],
        )

        config = uvicorn.Config(
            starlette_app,
            host=self.config.settings.server.host,
            port=self.config.settings.server.port,
            log_level=self.config.settings.log_level.lower(),
        )
        server = uvicorn.Server(config)
        await server.serve()




def create_server(config: MCPMLConfig) -> MCPMLServer:
    """
    Create a new MCP server
    
    Args:
        config_path: Path to the tools configuration file
        
    Returns:
        A configured MCPServer instance
    """
    return MCPMLServer(config)
