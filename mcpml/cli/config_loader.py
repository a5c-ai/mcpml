import hashlib
import importlib
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Tuple, Optional
from dotenv import load_dotenv
import typer
import yaml


from mcpml.config.mcpml import MCPMLConfig


logger = logging.getLogger(__name__)

def get_cache_dir() -> Path:
    """Gets the cache directory for cloned repositories."""
    cache_base = Path.home() / ".cache" / "mcpml" / "repos"
    cache_base.mkdir(parents=True, exist_ok=True)
    return cache_base

def is_github_url(source: str) -> bool:
    """Checks if the source string is a GitHub URL."""
    return source.startswith("https://github.com/") or source.startswith("git@github.com:")

def run_git_command(command: list[str], cwd: Optional[Path] = None) -> bool:
    """Runs a git command using subprocess."""
    try:
        process = subprocess.run(
            ["git"] + command,
            capture_output=True,
            text=True,
            check=True,
            cwd=cwd,
        )
        logger.debug(f"Git command '{' '.join(command)}' successful. Output:\n{process.stdout}")
        return True
    except FileNotFoundError:
        logger.error("Error: 'git' command not found. Please ensure Git is installed and in your PATH.")
        return False
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running git command '{' '.join(command)}':\n{e.stderr}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred while running git command '{' '.join(command)}': {e}")
        return False

def run_command(command: list[str], cwd: Optional[Path] = None) -> bool:
    """Runs a general command using subprocess."""
    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            cwd=cwd,
        )
        logger.debug(f"Command '{' '.join(command)}' successful. Output:\n{process.stdout}")
        return True
    except FileNotFoundError:
        logger.error(f"Error: '{command[0]}' command not found.")
        return False
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running command '{' '.join(command)}':\n{e.stderr}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred while running command '{' '.join(command)}': {e}")
        return False

def run_installation_scripts(repo_path: Path) -> None:
    """Runs installation scripts and installs requirements if they exist."""
    # Check for and run OS-specific installation script
    install_script = None
    if sys.platform.startswith('win'):
        install_script = repo_path / "install-deps.cmd"
    else:
        install_script = repo_path / "install-deps.sh"
    
    if install_script.exists():
        logger.info(f"Found installation script {install_script}. Running...")
        if sys.platform.startswith('win'):
            success = run_command([str(install_script)], cwd=repo_path)
        else:
            # Make the script executable
            os.chmod(install_script, 0o755)
            success = run_command(["bash", str(install_script)], cwd=repo_path)
        
        if not success:
            logger.warning(f"Failed to run installation script {install_script}")
        else:
            logger.info(f"Installation script {install_script} completed successfully")
    
    # Check for and install requirements.txt
    requirements_file = repo_path / "requirements.txt"
    if requirements_file.exists():
        logger.info(f"Found requirements.txt. Installing dependencies...")
        success = run_command([sys.executable, "-m", "pip", "install", "-r", str(requirements_file)], cwd=repo_path)
        if not success:
            logger.warning("Failed to install requirements")
        else:
            logger.info("Requirements installed successfully")

def resolve_remote_config(source: str) -> Path:
    """
    Resolves a configuration source. If it's a GitHub URL, clones or updates
    the repo in a cache directory and returns the local path. Otherwise,
    returns the source path directly.
    """
    if is_github_url(source):
        repo_url = source
        # Create a unique directory name based on the URL hash
        url_hash = hashlib.sha256(repo_url.encode()).hexdigest()[:16]
        # Try to extract a readable name, e.g., 'user-repo'
        try:
            repo_name = Path(repo_url.split(':')[-1].replace('.git', '')).name
            readable_name = repo_name.replace('/', '-')
            local_repo_path = get_cache_dir() / f"{readable_name}-{url_hash}"
        except Exception:
            local_repo_path = get_cache_dir() / url_hash

        logger.info(f"Resolving remote config: {repo_url} -> {local_repo_path}")

        if local_repo_path.exists():
            logger.info(f"Repository exists at {local_repo_path}. Attempting to update...")
            if not run_git_command(["pull"], cwd=local_repo_path):
                logger.warning(f"Failed to update repository {local_repo_path}. Using cached version.")
            else:
                # Run installation scripts after successful update
                run_installation_scripts(local_repo_path)
        else:
            logger.info(f"Cloning repository {repo_url} to {local_repo_path}...")
            if not run_git_command(["clone", repo_url, str(local_repo_path)]):
                raise RuntimeError(f"Failed to clone repository: {repo_url}")
            # Run installation scripts after successful clone
            run_installation_scripts(local_repo_path)

        return local_repo_path
    else:
        # Assume it's a local path
        local_path = Path(source).resolve()
        if local_path.is_file():
             # If it's a file, return the parent directory
             return local_path.parent
        elif local_path.is_dir():
            # If it's a directory, return it directly
             return local_path
        else:
            raise FileNotFoundError(f"Local configuration source not found: {source}")


def load_config_from_source(source: str) -> Tuple[MCPMLConfig, Path]:
    """
    Loads MCPML configuration from a given source (local path or GitHub URL).

    Args:
        source: The configuration source (e.g., 'mcpml.yaml', './my_config_dir', 'https://github.com/user/repo').

    Returns:
        A tuple containing the loaded MCPMLConfig object and the Path to the
        directory containing the mcpml.yaml file.

    Raises:
        FileNotFoundError: If the configuration file cannot be found.
        RuntimeError: If cloning fails or YAML parsing fails.
    """
    try:
        config_dir = resolve_remote_config(source)
        config_file_path = config_dir / "mcpml.yaml"

        logger.info(f"Attempting to load configuration from: {config_file_path}")

        if not config_file_path.is_file():
            # If source was a directory or repo URL, mcpml.yaml must be inside
            raise FileNotFoundError(f"Configuration file 'mcpml.yaml' not found in {config_dir}")

        # Add the config directory to sys.path *before* loading config
        # in case the config itself references types defined within the repo
        if str(config_dir) not in sys.path:
             sys.path.insert(0, str(config_dir))
             logger.debug(f"Added {config_dir} to sys.path")

        # Load the config (assuming MCPMLConfig has a suitable class method)
        # You might need to adjust this based on how MCPMLConfig loads YAML
        with open(config_file_path, 'r') as f:
             config_dict = yaml.safe_load(f)
             if not config_dict:
                 raise ValueError(f"Configuration file is empty or invalid: {config_file_path}")
             # Assume MCPMLConfig can be instantiated from a dict or has a from_dict method
             # This part depends heavily on the actual MCPMLConfig implementation
             if hasattr(MCPMLConfig, 'from_dict'):
                 config = MCPMLConfig.from_dict(config_dict)
             elif hasattr(MCPMLConfig, 'parse_obj'): # Pydantic v1 style
                 config = MCPMLConfig.parse_obj(config_dict)
             elif hasattr(MCPMLConfig, 'model_validate'): # Pydantic v2 style
                 config = MCPMLConfig.model_validate(config_dict)
             else:
                 # Basic instantiation if no specific method exists
                  try:
                     config = MCPMLConfig(**config_dict)
                  except TypeError:
                     logger.error("Cannot instantiate MCPMLConfig. Please ensure it has a suitable constructor or factory method (e.g., from_dict, parse_obj, model_validate).")
                     raise RuntimeError("Failed to load configuration due to MCPMLConfig instantiation error.")
        
        if(config is None):
            raise typer.Exit(1)

        # Load the environment variables
        load_dotenv('./.env')
        logger.info(f"Successfully loaded configuration from {config_file_path}")
        return config, config_dir

    except FileNotFoundError as e:
        logger.error(f"Configuration loading failed: {e}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred during configuration loading: {e}")
        raise RuntimeError(f"Failed to load configuration from {source}: {e}") 