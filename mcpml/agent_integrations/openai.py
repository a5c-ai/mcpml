from __future__ import annotations

import importlib
import json
import logging
import os
from typing import Any, Dict, List, Optional, Type, Union
import asyncio

import requests
import yaml

from agents import Agent, Runner, Tool, Model, ModelSettings, ModelResponse, TResponseInputItem, AgentOutputSchema, Handoff, ModelTracing, ModelProvider, RunConfig, function_tool
from agents.mcp import MCPServerSse, MCPServerStdio
from agents import OpenAIChatCompletionsModel
from mcpml.mcp_server.tools import execute_tool
from mcpml.agent_integrations.base import MCPAgent
from mcpml.config.mcpml import config,ToolDefinition,MCPServerDefinition
from openai import AsyncOpenAI, AsyncAzureOpenAI
logger = logging.getLogger(__name__)


class CustomModelProvider(ModelProvider):
    def get_model(self, model_name: str | None) -> Model:
        if(os.environ.get("AZURE_OPENAI_API_KEY")):
            client = AsyncAzureOpenAI(
                api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
                azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),     
                api_version=os.environ.get("OPENAI_API_VERSION"),
            )
        else:
            client = AsyncOpenAI(
                api_key=os.environ.get("OPENAI_API_KEY"),
            )
        return OpenAIChatCompletionsModel(model=model_name, openai_client=client)

class MCPOpenAIAgent(MCPAgent):
    """
    OpenAI Agent SDK integration that can use MCP tools
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        mcp_servers: Optional[List[MCPServerDefinition]] = None,
        instructions: str = "You are a helpful AI assistant.",
        cache_tools_list: bool = True,
        tools: Optional[List[str]] = None,
        output_type: Optional[Type] = None,
    ):
        """
        Initialize the OpenAI agent
        
        Args:
            model: The OpenAI model to use
            mcp_servers: Dictionary of MCP server name to URL
            instructions: Instructions for the agent
            cache_tools_list: Whether to cache the list of tools from MCP servers
            output_type: Optional Pydantic model to define the structure of the agent's output
        """
        super().__init__()
        self.model = model
        self.instructions = instructions
        self.cache_tools_list = cache_tools_list
        self.output_type = output_type
        
        
        self.mcp_servers = {}
        self.tools = []
        if(tools):
            for tool_name in tools:
                tool = next((t for t in config.tools if t.name == tool_name), None)
                if(tool):
                    self.add_tool(tool)
                else:
                    raise ValueError(f"Tool not found: {tool_name}")
        # Add additional MCP servers if provided directly
        if mcp_servers:
            for server in mcp_servers:
                if(server.url):
                    self._add_mcp_server(server.name, server.url)
                elif(server.command):
                    self._add_mcp_stdio_server(server.name, server.command, server.args,server.env)        

    def _add_mcp_server(self, name: str, url: str) -> None:
        """
        Add an MCP server using HTTP/SSE transport
        
        Args:
            name: Name of the server
            url: URL of the server
        """
        self.mcp_servers[name] = {
            "type": "sse",
            "url": url,
            "server": MCPServerSse(
                url=url, 
                cache_tools_list=self.cache_tools_list
            )
        }

    def _add_mcp_stdio_server(self, name: str, command: str, args: List[str], env: Dict[str, str]) -> None:
        """
        Add an MCP server using stdio transport
        
        Args:
            name: Name of the server
            command: Command to run
            args: Arguments for the command
        """
        self.mcp_servers[name] = {
            "type": "stdio",
            "command": command,
            "args": args,
            "env": env,
            "server": MCPServerStdio(
                params={
                    "command": command,
                    "args": args,
                    "env": env,
                },
                cache_tools_list=self.cache_tools_list
            )
        }

    def add_tool(self, tool: ToolDefinition) -> None:
        """
        Add a tool to the agent
        
        Args:
            tool: The tool to add
        """
        # make tool
        tool_function = None
        if(tool.implementation):
            # load the implementation
            # split the implementation into module and function 
            module, function = tool.implementation.rsplit(".", 1)
            implementation = importlib.import_module(module)            
            tool_function = getattr(implementation, function)
            tool_function = function_tool(tool_function)
        else:
            # create a function that will invoke the agent
            @function_tool
            def invoke_agent(input:str):
                return execute_tool(tool.name,input)
            tool_function = invoke_agent
        self.tools.append(tool_function)
    
    async def run_async(self, max_turns:int=10, **kwargs) -> Any:
        """
        Run the agent with a query asynchronously
        
        Args:
            max_turns: The maximum number of turns the agent can take
            **kwargs: The user query to process
            
        Returns:
            The result of processing the query
        """
        try:
            # Get all MCP servers
            mcp_servers = [server_info["server"] for server_info in self.mcp_servers.values()]
            for name,server in self.mcp_servers.items():
                # connect the server
                print("connecting to server",name)
                await server["server"].connect()

            # Create an agent with the MCP tools and servers

            agent_kwargs = {
                "name": "MCP OpenAI Agent",
                "instructions": self.instructions,
                "tools": self.tools,
            }
            
            # Add output type if specified
            if self.output_type:
                agent_kwargs["output_type"] = self.output_type
            
            agent = Agent(**agent_kwargs,mcp_servers=mcp_servers,output_type=self.output_type,model=self.model)
            
            # Run the agent
            result = await Runner.run(agent,
                                      run_config=RunConfig(model_provider=CustomModelProvider()),
                                      max_turns=max_turns,
                                      **kwargs)
            
            # Return the final output
            if self.output_type and hasattr(result, "final_output_as"):
                # Get the typed output if an output type was specified
                return result.final_output_as(self.output_type)
            else:
                return result.final_output
        
        except Exception as e:
            logger.exception("Error running OpenAI agent")
            return f"Error: {str(e)}"

    def run(self, max_turns:int=10, **kwargs) -> Any:
        """
        Run the agent with a query
        
        Args:
            **kwargs: The user query to process
            max_turns: The maximum number of turns the agent can take
            
        Returns:
            The result of processing the query
        """
        return asyncio.run(self.run_async(max_turns=max_turns,**kwargs))

    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute a tool call manually (for tools not handled by MCP)
        
        Args:
            tool_name: Name of the tool
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        # For custom tools not handled by the MCP servers

        return {"error": f"Tool '{tool_name}' not implemented as a direct tool"}
