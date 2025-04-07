from __future__ import annotations

import importlib
import inspect  
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

from mcpml.config.mcpml import MCPServerDefinition
from mcpml.agent_integrations.base import MCPAgent
from mcpml.agent_integrations.openai import MCPOpenAIAgent

logger = logging.getLogger(__name__)


def create_agent(
    agent_type: str = "simple",
    instructions: str = "You are a helpful AI assistant.",
    model: str = "gpt-4o",
    mcp_servers: Optional[List[MCPServerDefinition]] = None,
    tools: Optional[List[str]] = None,
    output_type: Optional[Type] = None,
    **kwargs: Any,
) -> MCPAgent:
    """
    Create an agent based on the specified type
    
    Args:
        agent_type: Type of agent to create
        instructions: Instructions for the agent
        model: Model to use for the agent
        mcp_servers: List of MCP server names to use
        output_type: Optional Pydantic model for structured output
        **kwargs: Additional parameters for the agent
        
    Returns:
        An instance of MCPAgent
    """
    mcp_servers = mcp_servers or []
    
    # First, try to load a custom agent type from the current working directory
    custom_agent = _load_custom_agent_type(agent_type, instructions, model, output_type, **kwargs)
    if custom_agent:
        return custom_agent
    
    # If no custom agent was found, use the built-in types
    if agent_type == "simple":
        # Simple agent using OpenAI
        return MCPOpenAIAgent(
            model=model,
            instructions=instructions,
            output_type=output_type,
            tools=tools,
            mcp_servers=mcp_servers,
            **kwargs
        )
    else:
        logger.warning(f"Unknown agent type '{agent_type}', falling back to simple agent")
        return MCPOpenAIAgent(
            model=model,
            instructions=instructions,
            output_type=output_type,
            tools=tools,
            mcp_servers=mcp_servers,
            **kwargs
        )


def _load_custom_agent_type(
    agent_type: str,
    instructions: str,
    model: str,
    output_type: Optional[Type] = None,
    **kwargs
) -> Optional[MCPAgent]:
    """
    Attempt to load a custom agent type from the current working directory
    
    Args:
        agent_type: The type of agent to load
        instructions: Instructions for the agent
        model: Model to use for the agent
        output_type: Optional Pydantic model for structured output
        **kwargs: Additional parameters for the agent
        
    Returns:
        An instance of MCPAgent if found, None otherwise
    """
    # Possible locations for custom agent types
    search_paths = [
        # Current working directory
        os.getcwd(),
        # 'agents' directory in current working directory
        os.path.join(os.getcwd(), "agents"),
        # 'agent_types' directory in current working directory
        os.path.join(os.getcwd(), "agent_types"),
    ]
    
    # Add search paths to sys.path temporarily
    original_sys_path = sys.path.copy()
    for path in search_paths:
        if path not in sys.path and os.path.exists(path):
            sys.path.insert(0, path)
    
    try:
        # Try different module naming patterns
        possible_modules = [
            f"{agent_type}_agent",  # example: researcher_agent.py
            f"agent_{agent_type}",   # example: agent_researcher.py
            agent_type,              # example: researcher.py
            f"agents.{agent_type}",  # example: agents/researcher.py
            f"agent_types.{agent_type}",  # example: agent_types/researcher.py
        ]
        
        for module_name in possible_modules:
            try:
                # Try to import the module
                module = importlib.import_module(module_name)
                
                # Look for a class that inherits from MCPAgent
                for name, obj in inspect.getmembers(module):
                    if (
                        inspect.isclass(obj) 
                        and issubclass(obj, MCPAgent) 
                        and obj != MCPAgent
                    ):
                        logger.info(f"Found custom agent type '{agent_type}' in module '{module_name}'")
                        
                        # Create an instance of the agent
                        return obj(
                            model=model,
                            instructions=instructions,
                            output_type=output_type,
                            **kwargs
                        )
            
            except (ImportError, ModuleNotFoundError):
                continue
        
        return None
    
    finally:
        # Restore original sys.path
        sys.path = original_sys_path
