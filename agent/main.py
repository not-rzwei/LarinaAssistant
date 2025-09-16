# -*- coding: utf-8 -*-

import os
import sys
import json
import subprocess
from pathlib import Path

# utf-8
sys.stdout.reconfigure(encoding="utf-8")

# Get current main.py path and set parent directory as working directory
current_file_path = os.path.abspath(__file__)
current_script_dir = os.path.dirname(
    current_file_path
)  # Directory containing this script
project_root_dir = os.path.dirname(current_script_dir)  # Assumed project root directory

# Change CWD to project root directory
if os.getcwd() != project_root_dir:
    os.chdir(project_root_dir)
logger.info(f"set cwd: {os.getcwd()}")

# Add script's own directory to sys.path for importing utils, maa and other modules
if current_script_dir not in sys.path:
    sys.path.insert(0, current_script_dir)

from utils import logger

VENV_NAME = ".venv"  # Virtual environment directory name
VENV_DIR = Path(project_root_dir) / VENV_NAME

### Virtual Environment Related ###


def _is_running_in_our_venv():
    """Check if the script is running in the specific venv managed by this script."""
    current_python = Path(sys.executable).resolve()

    logger.debug(f"Current Python interpreter: {current_python}")

    if sys.platform.startswith("win"):
        # Windows: If in virtual environment, Python should be in Scripts directory
        if current_python.parent.name == "Scripts":
            return True
        else:
            logger.debug("Currently not in target virtual environment")
            return False
    else:
        # Linux/Unix: If in virtual environment, Python should be in bin directory
        if current_python.parent.name == "bin":
            return True
        else:
            logger.debug("Currently not in target virtual environment")
            return False


def ensure_venv_and_relaunch_if_needed():
    """
    Ensure venv exists, and if not already running in the script-managed venv,
    relaunch the script within it. Supports Linux and Windows systems.
    """
    logger.info(
        f"Detected system: {sys.platform}. Current Python interpreter: {sys.executable}"
    )

    if _is_running_in_our_venv():
        logger.info(f"Already running in target virtual environment ({VENV_DIR}).")
        return

    if not VENV_DIR.exists():
        logger.info(f"Creating virtual environment at {VENV_DIR}...")
        try:
            # Use the current Python running this script (system/external Python)
            subprocess.run(
                [sys.executable, "-m", "venv", str(VENV_DIR)],
                check=True,
                capture_output=True,
            )
            logger.info(f"Creation successful")
        except subprocess.CalledProcessError as e:
            logger.error(
                f"Creation failed: {e.stderr.decode(errors='ignore') if e.stderr else e.stdout.decode(errors='ignore')}"
            )
            logger.error("Exiting")
            sys.exit(1)
        except FileNotFoundError:
            logger.error(
                f"Command '{sys.executable} -m venv' not found. Please ensure 'venv' module is available."
            )
            logger.error("Cannot continue without virtual environment. Exiting.")
            sys.exit(1)

    if sys.platform.startswith("win"):
        python_in_venv = VENV_DIR / "Scripts" / "python.exe"
    else:
        python3_path = VENV_DIR / "bin" / "python3"
        python_path = VENV_DIR / "bin" / "python"
        if python3_path.exists():
            python_in_venv = python3_path
        elif python_path.exists():
            python_in_venv = python_path
        else:
            python_in_venv = python3_path  # Default to python3, let subsequent error handling catch it

    if not python_in_venv.exists():
        logger.error(
            f"Python interpreter not found in virtual environment {python_in_venv}."
        )
        logger.error(
            "Virtual environment creation may have failed or virtual environment structure is abnormal."
        )
        sys.exit(1)

    logger.info(f"Restarting using virtual environment Python")

    try:
        cmd = [str(python_in_venv)] + sys.argv
        logger.info(f"Executing command: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            cwd=os.getcwd(),
            env=os.environ.copy(),
            check=False,  # Don't throw exception on non-zero exit code
        )
        # Exit with subprocess exit code
        sys.exit(result.returncode)

    except Exception as e:
        logger.exception(f"Failed to restart script in virtual environment: {e}")
        sys.exit(1)


### Configuration Related ###


def read_interface_version(interface_file_name="./interface.json") -> str:
    interface_path = Path(project_root_dir) / interface_file_name
    assets_interface_path = Path(project_root_dir) / "assets" / interface_file_name

    target_path = None
    if interface_path.exists():
        target_path = interface_path
    elif assets_interface_path.exists():
        return "DEBUG"

    if target_path is None:
        logger.warning("interface.json not found")
        return "unknown"

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            interface_data = json.load(f)
            return interface_data.get("version", "unknown")
    except Exception:
        logger.exception(
            f"Failed to read interface.json version, file path: {target_path}"
        )
        return "unknown"


def read_pip_config() -> dict:
    config_dir = Path("./config")
    config_dir.mkdir(exist_ok=True)
    config_path = config_dir / "pip_config.json"
    default_config = {
        "enable_pip_install": True,
        "mirror": "https://pypi.tuna.tsinghua.edu.cn/simple",
        "backup_mirror": "https://mirrors.ustc.edu.cn/pypi/simple",
    }
    if not config_path.exists():
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)
        return default_config
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logger.exception(
            "Failed to read pip configuration, using default configuration"
        )
        return default_config


### Dependency Installation Related ###


def find_local_wheels_dir():
    """Find whl files in local deps directory"""
    project_root = Path(project_root_dir)
    deps_dir = project_root / "deps"

    if deps_dir.exists() and any(deps_dir.glob("*.whl")):
        whl_count = len(list(deps_dir.glob("*.whl")))
        logger.info(f"Found local deps directory containing {whl_count} whl files")
        return deps_dir

    logger.debug("deps directory not found or no whl files in directory")
    return None


def _run_pip_command(cmd_args: list, operation_name: str) -> bool:
    try:
        logger.info(f"Starting {operation_name}")
        logger.debug(f"Executing command: {' '.join(cmd_args)}")

        # Use subprocess.Popen for real-time output
        process = subprocess.Popen(
            cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Redirect stderr to stdout
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,  # Line buffering
            universal_newlines=True,
        )

        # Collect all output for logging
        all_output = []

        # Read output in real time, but do not print to terminal
        for line in iter(process.stdout.readline, ""):
            line = line.rstrip("\n\r")
            if line.strip():  # Only collect non-empty lines
                all_output.append(line)  # Collect to list

        # Wait for process to end
        return_code = process.wait()

        # Log complete output
        if all_output:
            full_output = "\n".join(all_output)
            logger.debug(f"{operation_name} output:\n{full_output}")

        if return_code == 0:
            logger.info(f"{operation_name} completed")
            return True
        else:
            logger.error(f"Error during {operation_name}. Return code: {return_code}")
            return False

    except Exception as e:
        logger.exception(f"Unknown exception during {operation_name}: {e}")
        return False


def install_requirements(req_file="requirements.txt", pip_config=None) -> bool:
    req_path = (
        Path(project_root_dir) / req_file
    )  # Ensure relative to project root directory
    if not req_path.exists():
        logger.error(f"{req_file} file does not exist at {req_path.resolve()}")
        return False

    # Find local deps directory
    deps_dir = find_local_wheels_dir()
    if deps_dir:
        logger.info(f"Installing using local whl files, directory: {deps_dir}")

        cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-U",
            "-r",
            str(req_path),
            "--no-warn-script-location",
            "--break-system-packages",
            "--find-links",
            str(deps_dir),  # pip will prioritize files here
            "--no-index",  # Disable online index
        ]

        if _run_pip_command(cmd, f"installing dependencies from local deps"):
            return True
        else:
            logger.warning(
                "Local deps installation failed, falling back to pure online installation"
            )

    # Fall back to online installation
    primary_mirror = pip_config.get("mirror", "")
    backup_mirror = pip_config.get("backup_mirror", "")

    if primary_mirror:
        # Use primary mirror source, only add one backup source to avoid conflicts
        cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-U",
            "-r",
            str(req_path),
            "--no-warn-script-location",
            "--break-system-packages",
            "-i",
            primary_mirror,
        ]

        # Only add one backup source
        if backup_mirror:
            cmd.extend(["--extra-index-url", backup_mirror])
            logger.info(
                f"Installing dependencies using primary source {primary_mirror} and backup source {backup_mirror}"
            )
        else:
            logger.info(
                f"Installing dependencies using primary source {primary_mirror}"
            )

        if _run_pip_command(cmd, f"installing dependencies from {req_path.name}"):
            return True
        else:
            logger.error("Online installation failed")
            return False
    else:
        # If no primary mirror source is configured, use pip's local global configuration
        cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-U",
            "-r",
            str(req_path),
            "--no-warn-script-location",
            "--break-system-packages",
        ]

        if _run_pip_command(
            cmd,
            f"installing dependencies from {req_path.name} (local global configuration)",
        ):
            return True
        else:
            logger.error("Installation failed using pip local global configuration")
            return False


def check_and_install_dependencies():
    """Check and install project dependencies"""
    pip_config = read_pip_config()
    enable_pip_install = pip_config.get("enable_pip_install", True)

    logger.info(f"Enable pip dependency installation: {enable_pip_install}")

    if enable_pip_install:
        logger.info("Starting dependency installation/update")
        if install_requirements(pip_config=pip_config):
            logger.info("Dependency check and installation completed")
        else:
            logger.warning(
                "Dependency installation failed, program may not run correctly"
            )
    else:
        logger.info(
            "Pip dependency installation disabled, skipping dependency installation"
        )


### Core Business ###


def agent(is_dev_mode=False):
    try:
        # Clear module cache
        utils_modules = [
            name for name in list(sys.modules.keys()) if name.startswith("utils")
        ]
        for module_name in utils_modules:
            del sys.modules[module_name]

        # Dynamically import all content from utils
        import utils
        import importlib

        importlib.reload(utils)

        # Import all public attributes from utils to current namespace
        for attr_name in dir(utils):
            if not attr_name.startswith("_"):
                globals()[attr_name] = getattr(utils, attr_name)

        if is_dev_mode:
            from utils.logger import change_console_level

            change_console_level("DEBUG")
            logger.info("Development mode: Log level set to DEBUG")

        from maa.agent.agent_server import AgentServer
        from maa.toolkit import Toolkit

        import custom

        Toolkit.init_option("./")

        if len(sys.argv) < 2:
            logger.error("Missing required socket_id parameter")
            return

        socket_id = sys.argv[-1]
        logger.info(f"socket_id: {socket_id}")

        AgentServer.start_up(socket_id)
        logger.info("AgentServer started")
        AgentServer.join()
        AgentServer.shut_down()
        logger.info("AgentServer closed")
    except ImportError as e:
        logger.error(f"Failed to import module: {e}")
        logger.error("Consider reconfiguring environment")
        sys.exit(1)
    except Exception as e:
        logger.exception("Exception occurred during agent runtime")
        raise


### Program Entry Point ###


def main():
    current_version = read_interface_version()
    is_dev_mode = current_version == "DEBUG"

    # If Linux system or development mode, start virtual environment
    if sys.platform.startswith("linux") or is_dev_mode:
        ensure_venv_and_relaunch_if_needed()

    check_and_install_dependencies()

    if is_dev_mode:
        os.chdir(Path("./assets"))
        logger.info(f"set cwd: {os.getcwd()}")

    agent(is_dev_mode=is_dev_mode)


if __name__ == "__main__":
    main()
