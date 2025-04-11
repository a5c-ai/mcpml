"""
MCP Tools implementation with dynamic loading support.
"""

import importlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, Union

from mcpml.config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mcp-tools")

def _import_module_from_string(module_path: str) -> Any:
    """
    Import a module from a string path, checking both local and installed modules.
    
    Args:
        module_path: Path to the module (e.g., "tools.hello")
        
    Returns:
        The imported module
    
    Raises:
        ImportError: If module cannot be found
    """
    # First try importing directly (for installed modules)
    try:
        return importlib.import_module(module_path)
    except ImportError:
        logger.debug(f"Could not import {module_path} directly, trying local import")
    
    # Try importing from current directory
    current_dir = os.getcwd()
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    try:
        return importlib.import_module(module_path)
    except ImportError as e:
        logger.error(f"Failed to import {module_path}: {e}")
        raise ImportError(f"Could not import {module_path}")



def execute_tool(tool_name: str, **kwargs) -> Any:
    """
    Execute a tool with the given parameters.
    
    Args:
        tool_name: Name of the tool to execute
        config_path: Path to the tools configuration file
        parameters: Dictionary of parameters to pass to the tool
        
    Returns:
        The result of the tool execution
    """
    tools =  config.tools    
    print("execute_tool", tool_name, kwargs)
    tool = next((t for t in tools if t.name == tool_name), None)
    if not tool:
        raise ValueError(f"Tool not found: {tool_name}")

    # Load implementation
    if tool.type == "function":
        # Parse implementation path
        module_path, function_name = tool.implementation.rsplit('.', 1)
        
        # Import module
        module = _import_module_from_string(module_path)
        
        # Get function
        func = getattr(module, function_name)
        

        # Execute function
        result = func(**kwargs)
        
        # Handle output schema if specified
        if tool.output_schema:
            try:
                schema_module_path, schema_class_name = tool.output_schema.rsplit('.', 1)
                schema_module = _import_module_from_string(schema_module_path)
                schema_class = getattr(schema_module, schema_class_name)
                result = schema_class.model_validate(result)
            except (ImportError, AttributeError) as e:
                logger.warning(f"Could not apply output schema: {e}")
        
        return result
    
    elif tool.type == "agent":
        # Agent-based tool implementation would go here
        # This requires integrating with the agent factory
        from mcpml.agent_integrations.factory import create_agent
        # if the tools has mcp_servers, use them, otherwise use the default ones
        if tool.mcp_servers is None:
            mcp_servers = config.mcpServers
        elif len(tool.mcp_servers) > 0:
            # filter the mcp_servers to only include the ones in the tool
            mcp_servers = [server for server in config.mcpServers if server.name in tool.mcp_servers]
        else:
            mcp_servers = []
        # same for tools
        if tool.tools is None:
            tools = config.tools
            # filter self
            tools = [t.name for t in tools if t.name != tool.name]
        elif len(tool.tools) > 0:
            tools = config.tools
            # filter the tools to only include the ones in the tool
            tools = [t.name for t in tools if t.name in tool.tools]
        else:
            tools = []
        if tool.max_turns is not None:
            kwargs["max_turns"] = tool.max_turns
        agent = create_agent(agent_type=tool.agent_type, model=tool.model, instructions=tool.instructions, mcp_servers=mcp_servers,tools=tools)
        result = agent.run(**kwargs)
        return result
    
    else:
        raise ValueError(f"Unknown tool type: {tool.type}")
