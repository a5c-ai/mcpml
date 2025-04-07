from __future__ import annotations

import importlib
import json
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional

import typer
from typer.models import CommandInfo
from click import Context, Command
import yaml
from rich.console import Console
from rich.table import Table

from mcpml.mcp_server.server import create_server
from mcpml.mcp_server.tools import execute_tool
from mcpml.cli.config_loader import load_config_from_source

app = typer.Typer(help="MCPML - Model Context Protocol Markup Language")
console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mcpml-cli")


def get_default_config_path() -> Path:
    """Get the default config path"""
    return Path("mcpml.yaml")
from dotenv import load_dotenv


# Define a global config option for all commands
def config_callback(value: Optional[str]):
    if value is None:
        # Use default config path from mcpml.config.mcpml
        return None
    return value


ConfigOption = typer.Option(
    None,
    "--config", "-c",
    help="Path to configuration file (local path or GitHub URL)",
    callback=config_callback
)

# Import the standard config - will be used as a fallback
from mcpml.config.mcpml import config as default_config
load_dotenv('./.env')
load_dotenv()
def get_config_and_setup_env(config_source: Optional[str] = None):
    """
    Gets the configuration and sets up the environment.
    If config_source is provided, it will be used instead of the default config.
    Returns a tuple of (config, config_dir)
    """
    if config_source:
        # Load from the provided source (local or GitHub)
        try:
            logger.info(f"Loading configuration from source: {config_source}")
            config, config_dir = load_config_from_source(config_source)
            
            # Set up the environment
            if str(config_dir) not in sys.path:
                sys.path.insert(0, str(config_dir))
                logger.debug(f"Added {config_dir} to sys.path")
            
            # Load environment variables
            if config.settings.env_file:
                env_file_path = config_dir / config.settings.env_file
                if env_file_path.exists():
                    logger.info(f"Loading environment variables from {env_file_path}")
                    load_dotenv(env_file_path)
                else:
                    logger.warning(f"Environment file not found: {env_file_path}")
            
            return config, config_dir
        except Exception as e:
            logger.error(f"Error loading configuration from {config_source}: {e}")
            console.print(f"[bold red]Error:[/] Failed to load configuration from {config_source}: {e}")
            raise typer.Exit(1)
    else:
        # Use the default configuration
        if default_config is None:
            console.print(f"[bold red]Error:[/] Default configuration not found")
            raise typer.Exit(1)
        
        # The default config is already loaded in the module, just need to set up env
        if default_config.settings.env_file:
            load_dotenv(default_config.settings.env_file)
        else:
            load_dotenv()
        
        # Add current directory to path (same as before)
        if os.getcwd() not in sys.path:
            sys.path.append(os.getcwd())
            
        return default_config, Path(os.getcwd())


def list_tools(
    format: str = typer.Option(
        "table", help="Output format (table, json, yaml)"
    ),
    config_source: Optional[str] = ConfigOption,
):
    """List available tools"""
    config, _ = get_config_and_setup_env(config_source)
    
    tools = config.tools
    
    if format == "json":
        # Convert to JSON-serializable format
        result = {"tools": []}
        for tool in tools:
            tool_data = {
                "name": tool.name,
                "description": tool.description,
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.type,
                        "description": p.description,
                        "required": p.required,
                        "default": p.default,
                    }
                    for p in tool.parameters
                ],
            }
            result["tools"].append(tool_data)
        console.print(json.dumps(result, indent=2))
    
    elif format == "yaml":
        # Convert to YAML-serializable format
        result = {"tools": []}
        for tool in tools:
            tool_data = {
                "name": tool.name,
                "description": tool.description,
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.type,
                        "description": p.description,
                        "required": p.required,
                        "default": p.default,
                    }
                    for p in tool.parameters
                ],
            }
            result["tools"].append(tool_data)
        console.print(yaml.dump(result, default_flow_style=False))
    
    else:  # table
        table = Table(title="Available Tools")
        table.add_column("Name")
        table.add_column("Description")
        table.add_column("Parameters")
        
        for tool in tools:
            params = []
            for p in tool.parameters:
                req = "*" if p.required else ""
                params.append(f"{p.name}{req}: {p.type}")
            
            table.add_row(
                tool.name,
                tool.description,
                ", ".join(params),
            )
        
        console.print(table)



tools_app = typer.Typer(help="Manage MCP tools")

@tools_app.command("list")
def list_tools_command(
    format: str = typer.Option(
        "table", help="Output format (table, json, yaml)"
    ),
    config_source: Optional[str] = ConfigOption,
):
    """List available tools"""
    list_tools(format, config_source)



# append the current dir (cwd) to the sys.path
sys.path.append(os.getcwd())

@tools_app.command("run")
def run_tool(
    tool_name: str = typer.Argument(..., help="Name of the tool to execute"),
    input_json: str = typer.Argument(None, help="JSON string with tool parameters"),
    config_source: Optional[str] = ConfigOption,
):
    """Run a specific tool with JSON input"""
    config, config_dir = get_config_and_setup_env(config_source)
    
    # Find the tool definition
    tool = next((t for t in config.tools if t.name == tool_name), None)
    if not tool:
        console.print(f"[bold red]Error:[/] Tool '{tool_name}' not found in configuration")
        raise typer.Exit(1)
    
    # Load the input parameters
    if input_json:
        try:
            parameters = json.loads(input_json)
        except json.JSONDecodeError:
            console.print(f"[bold red]Error:[/] Invalid JSON input: {input_json}")
            raise typer.Exit(1)
    else:
        parameters = {}
    
    # Execute the tool
    try:
        if tool.implementation:
            # Function tool
            module_name, function_name = tool.implementation.rsplit('.', 1)
            module = importlib.import_module(module_name)
            function = getattr(module, function_name)
            result = function(**parameters)
        else:
            # Agent tool
            result = execute_tool(tool.name, input=parameters)
        
        # Print the result
        if isinstance(result, dict) or isinstance(result, list):
            console.print(json.dumps(result, indent=2))
        else:
            console.print(str(result))
    
    except Exception as e:
        console.print(f"[bold red]Error executing tool '{tool_name}':[/] {str(e)}")
        raise typer.Exit(1)

# register the commands
app.add_typer(tools_app, name="tools")

# The following code is only run if default_config is available (backward compatibility)
if default_config is not None:
    # Dynamically add individual tool commands for backward compatibility
    for tool in default_config.tools:
        tool_args = tool.parameters
        tool_args_dict = {p.name: p for p in tool_args}
        cmd = typer.Typer(help=tool.description, name=tool.name)
        
        if tool.implementation:
            # Function
            module_name, function_name = tool.implementation.rsplit('.', 1)
            try:
                # Use try/except to avoid breaking if the module can't be imported yet
                module = importlib.import_module(module_name)
                function = getattr(module, function_name)
                
                cmd.registered_commands.append(
                    CommandInfo(
                        name="run",
                        callback=function,
                        help=tool.description,
                    )
                )
            except (ImportError, AttributeError) as e:
                logger.warning(f"Could not register tool {tool.name}: {e}")
                # Skip this tool but don't crash
                continue
        else:
            # Agent
            def create_function(_tool):
                def f(input:str):        
                    res = execute_tool(_tool.name, input=input)
                    print("res", _tool.name, res)
                    return res
                return f
            function = create_function(tool)
            
            cmd.registered_commands.append(
                CommandInfo(
                    name="run",
                    callback=function,
                    help=tool.description,
                )
            )
        
        tools_app.add_typer(cmd, name=tool.name)

@app.command("run")
def run_server(
    transport: str = typer.Option("stdio", help="Transport protocol to use (stdio, sse)"),
    config_source: Optional[str] = ConfigOption,
):
    """Run the MCP server"""
    config, config_dir = get_config_and_setup_env(config_source)
    
    console.print(f"[green]Starting MCP server[/] with config: {config}")
    server = create_server(config)
    server.run(transport)

if __name__ == "__main__":
    app()



