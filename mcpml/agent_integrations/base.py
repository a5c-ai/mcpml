from __future__ import annotations

import abc
from typing import Any, Dict, List, Optional


class MCPAgent(abc.ABC):
    """
    Base class for all MCP agents
    """

    def __init__(self):
        """
        Initialize the agent
        
        Args:
            mcp_config: Path to MCP configuration file
        """

    @abc.abstractmethod
    def run(self, query: str) -> Any:
        """
        Run the agent with a query
        
        Args:
            query: The user query to process
            
        Returns:
            The result of processing the query
        """
        pass

