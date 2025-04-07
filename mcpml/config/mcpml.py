from __future__ import annotations

import os
from typing import Dict, List, Any, Optional

from pydantic import BaseModel, Field
import yaml


class MCPRequest(BaseModel):
    tool: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class MCPResponse(BaseModel):
    result: Any
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MCPError(BaseModel):
    error: str
    details: Optional[Dict[str, Any]] = None


class MCPToolDescription(BaseModel):
    name: str
    description: str
    parameters: List[ToolParameter]


class MCPServerDefinition(BaseModel):
    name: str
    url: Optional[str] = None
    description: Optional[str] = None
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None

class ServerSettings(BaseModel):
    """Server settings"""
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"


class Settings(BaseModel):
    """Application settings"""
    server: ServerSettings = Field(default_factory=ServerSettings)
    env_file: Optional[str] = ".env"
    log_level: str = "INFO"

class MCPMLConfig(BaseModel):
    name: str
    mcpServers: List[MCPServerDefinition]
    tools: List[ToolDefinition]
    settings: Settings



class ToolParameter(BaseModel):
    """Tool parameter definition."""
    name: str
    type: str
    description: str
    required: bool = True
    default: Optional[Any] = None


class ToolDefinition(BaseModel):
    """Tool definition."""
    name: str
    description: str
    implementation: Optional[str] = None
    type: str = "function"  # function or agent
    agent_type: Optional[str] = None
    model: Optional[str] = None
    instructions: Optional[str] = None
    parameters: List[ToolParameter] = []
    output_schema: Optional[str] = None
    mcp_servers: Optional[List[str]] = None
    tools: Optional[List[str]] = None

def load_mcpml_config(config_path: str) -> Optional[MCPMLConfig]:
    if not os.path.exists(config_path):
        return None
    with open(config_path, "r") as f:
        yamlString = f.read()
        config = yaml.load(yamlString, Loader=yaml.FullLoader)
    return MCPMLConfig(**config)
        
# load config from file
config = load_mcpml_config("mcpml.yaml")
if not config:
    print("mcpml.yaml file not found")



