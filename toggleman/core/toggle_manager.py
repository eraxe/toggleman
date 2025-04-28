"""
Toggle Manager for Toggleman.

This module handles the management of toggle scripts, including running, testing,
and monitoring their status.
"""

import os
import subprocess
import signal
import stat
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import shutil

from toggleman.core.debug import get_logger
from toggleman.core.script_generator import ScriptGenerator

logger = get_logger(__name__)


class ToggleManager:
    """Manages toggle scripts, including running and monitoring."""

    def __init__(self, config_manager):
        """Initialize the toggle manager.

        Args:
            config_manager: The configuration manager instance
        """
        self.config_manager = config_manager
        self.script_generator = ScriptGenerator(config_manager)

        # Initialize script cache
        self.script_cache = {}
        self.running_processes = {}

    def create_toggle(self, name: str, config: Dict[str, Any]) -> Tuple[bool, str]:
        """Create a new toggle script.

        Args:
            name: The name of the toggle script
            config: The configuration for the toggle script

        Returns:
            Tuple of (success, message)
        """
        # Validate configuration
        if not self._validate_config(config):
            return False, "Invalid configuration: missing required fields"

        # Save script configuration
        if not self.config_manager.save_script(name, config):
            return False, f"Failed to save script configuration for {name}"

        # Generate script file
        return self.script_generator.generate_script(name)

    def update_toggle(self, name: str, config: Dict[str, Any]) -> Tuple[bool, str]:
        """Update an existing toggle script.

        Args:
            name: The name of the toggle script
            config: The updated configuration

        Returns:
            Tuple of (success, message)
        """
        # Check if script exists
        if not self.config_manager.get_script(name):
            return False, f"Toggle script '{name}' not found"

        # Validate configuration
        if not self._validate_config(config):
            return False, "Invalid configuration: missing required fields"

        # Save script configuration
        if not self.config_manager.save_script(name, config):
            return False, f"Failed to save script configuration for {name}"

        # Regenerate script file
        return self.script_generator.generate_script(name)

    def delete_toggle(self, name: str) -> Tuple[bool, str]:
        """Delete a toggle script.

        Args:
            name: The name of the toggle script

        Returns:
            Tuple of (success, message)
        """
        # Get script config to check if it exists
        script_config = self.config_manager.get_script(name)
        if not script_config:
            return False, f"Toggle script '{name}' not found"

        # Stop any running processes for this script
        if name in self.running_processes:
            self._stop_process(name)

        # Delete script file
        return self.script_generator.delete_script(name)

    def run_toggle(self, name: str) -> Tuple[bool, str]:
        """Run a toggle script.

        Args:
            name: The name of the toggle script

        Returns:
            Tuple of (success, message)
        """
        # Get script configuration
        script_config = self.config_manager.get_script(name)
        if not script_config:
            return False, f"Toggle script '{name}' not found"

        # Get script path
        script_path = script_config.get("script_path", "")
        if not script_path or not os.path.exists(script_path):
            # Try to generate the script if it doesn't exist
            success, message = self.script_generator.generate_script(name)
            if not success:
                return False, f"Script file not found and could not be generated: {message}"

            # Get updated script config with path
            script_config = self.config_manager.get_script(name)
            script_path = script_config.get("script_path", "")

            if not script_path or not os.path.exists(script_path):
                return False, f"Failed to generate script file at {script_path}"

        # Check if script is executable
        if not os.access(script_path, os.X_OK):
            try:
                # Try to make it executable
                os.chmod(script_path, os.stat(script_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            except Exception as e:
                return False, f"Script file exists but is not executable: {e}"

        # Run the script
        try:
            # Run with shell=False for better security
            process = subprocess.Popen([script_path],
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE,
                                      start_new_session=True)  # Detach the process

            # Don't wait for it to complete - return immediately
            return True, f"Running toggle script {name}"
        except Exception as e:
            logger.error(f"Error running toggle script {name}: {e}")
            return False, f"Error running toggle script: {str(e)}"

    def test_toggle(self, name: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Test a toggle script and return detailed output.

        Args:
            name: The name of the toggle script

        Returns:
            Tuple of (success, message, details)
        """
        # Get script configuration
        script_config = self.config_manager.get_script(name)
        if not script_config:
            return False, f"Toggle script '{name}' not found", {}

        # Get script path
        script_path = script_config.get("script_path", "")
        if not script_path or not os.path.exists(script_path):
            # Try to generate the script if it doesn't exist
            success, message = self.script_generator.generate_script(name)
            if not success:
                return False, f"Script file not found and could not be generated: {message}", {}

            # Get updated script config with path
            script_config = self.config_manager.get_script(name)
            script_path = script_config.get("script_path", "")

        # Set debug mode for the test
        test_env = os.environ.copy()
        test_env["DEBUG"] = "true"

        # Run the script with capture
        try:
            result = subprocess.run([script_path],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    env=test_env,
                                    encoding='utf-8',
                                    timeout=10)

            details = {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "script_path": script_path,
                "config": script_config
            }

            if result.returncode == 0:
                return True, "Toggle script test completed successfully", details
            else:
                return False, f"Toggle script test failed with return code {result.returncode}", details

        except subprocess.TimeoutExpired:
            return False, "Toggle script test timed out after 10 seconds", {
                "stdout": "Timeout",
                "stderr": "Script execution timed out after 10 seconds",
                "return_code": -1,
                "script_path": script_path,
                "config": script_config
            }
        except Exception as e:
            logger.error(f"Error testing toggle script {name}: {e}")
            return False, f"Error testing toggle script: {str(e)}", {
                "stdout": "",
                "stderr": str(e),
                "return_code": -1,
                "script_path": script_path,
                "config": script_config
            }

    def test_toggle_with_timeout(self, name: str, timeout: int = 3) -> Tuple[bool, str, Dict[str, Any]]:
        """Test a toggle script with timeout and return detailed output.

        Args:
            name: The name of the toggle script
            timeout: Timeout in seconds

        Returns:
            Tuple of (success, message, details)
        """
        # Get script configuration
        script_config = self.config_manager.get_script(name)
        if not script_config:
            return False, f"Toggle script '{name}' not found", {}

        # Get script path
        script_path = script_config.get("script_path", "")
        if not script_path or not os.path.exists(script_path):
            # Try to generate the script if it doesn't exist
            success, message = self.script_generator.generate_script(name)
            if not success:
                return False, f"Script file not found and could not be generated: {message}", {}

            # Get updated script config with path
            script_config = self.config_manager.get_script(name)
            script_path = script_config.get("script_path", "")

        # Check if script is executable
        if not os.access(script_path, os.X_OK):
            try:
                # Try to make it executable
                os.chmod(script_path, os.stat(script_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            except Exception as e:
                return False, f"Script file exists but is not executable: {e}", {
                    "stdout": "",
                    "stderr": f"Script not executable: {e}",
                    "return_code": -1,
                    "script_path": script_path,
                    "config": script_config
                }

        # Set debug mode for the test
        test_env = os.environ.copy()
        test_env["DEBUG"] = "true"

        # Run the script with capture
        try:
            result = subprocess.run([script_path],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   env=test_env,
                                   encoding='utf-8',
                                   timeout=timeout)

            details = {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "script_path": script_path,
                "config": script_config
            }

            if result.returncode == 0:
                return True, "Toggle script test completed successfully", details
            else:
                return False, f"Toggle script test failed with return code {result.returncode}", details

        except subprocess.TimeoutExpired:
            return False, f"Toggle script test timed out after {timeout} seconds", {
                "stdout": "Timeout",
                "stderr": f"Script execution timed out after {timeout} seconds",
                "return_code": -1,
                "script_path": script_path,
                "config": script_config
            }
        except Exception as e:
            logger.error(f"Error testing toggle script {name}: {e}")
            return False, f"Error testing toggle script: {str(e)}", {
                "stdout": "",
                "stderr": str(e),
                "return_code": -1,
                "script_path": script_path,
                "config": script_config
            }

    def get_running_toggles(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all running toggle processes.

        Returns:
            Dictionary mapping script names to process information
        """
        # Update cache of running processes
        self._update_process_cache()

        return self.running_processes

    def is_toggle_running(self, name: str) -> bool:
        """Check if a toggle script process is running.

        Args:
            name: The name of the toggle script

        Returns:
            True if the process is running, False otherwise
        """
        # Update cache of running processes
        self._update_process_cache()

        return name in self.running_processes

    def _update_process_cache(self) -> None:
        """Update the cache of running toggle processes."""
        # Clear the current cache
        self.running_processes = {}

        # Get all script configurations
        scripts = self.config_manager.get_all_scripts()

        for name, config in scripts.items():
            # Get script path
            script_path = config.get("script_path", "")
            if not script_path or not os.path.exists(script_path):
                continue

            # Get app process pattern
            app_process = config.get("app_process", "")
            if not app_process:
                continue

            # Check if the app is running
            try:
                # Use pgrep to check for the app process
                result = subprocess.run(["pgrep", "-f", app_process],
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)

                if result.returncode == 0:
                    # Get list of PIDs
                    pids = result.stdout.decode('utf-8').strip().split('\n')

                    self.running_processes[name] = {
                        "pids": pids,
                        "config": config
                    }
            except Exception as e:
                logger.error(f"Error checking if {name} is running: {e}")

    def _stop_process(self, name: str) -> bool:
        """Stop a running toggle process.

        Args:
            name: The name of the toggle script

        Returns:
            True if the process was stopped successfully, False otherwise
        """
        # Check if process is in cache
        if name not in self.running_processes:
            self._update_process_cache()

            if name not in self.running_processes:
                return False

        # Get process info
        process_info = self.running_processes[name]
        pids = process_info.get("pids", [])

        # Stop each PID
        success = True
        for pid_str in pids:
            try:
                pid = int(pid_str)
                os.kill(pid, signal.SIGTERM)
            except Exception as e:
                logger.error(f"Error stopping process {pid} for {name}: {e}")
                success = False

        # Remove from cache
        if name in self.running_processes:
            del self.running_processes[name]

        return success

    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate a toggle script configuration.

        Args:
            config: The configuration to validate

        Returns:
            True if the configuration is valid, False otherwise
        """
        # Check for required fields
        required_fields = ["app_command", "app_process", "window_class"]

        for field in required_fields:
            if field not in config or not config[field]:
                logger.error(f"Missing required field in config: {field}")
                return False

        return True

    def export_toggle(self, name: str, export_path: str) -> Tuple[bool, str]:
        """Export a toggle script to a file.

        Args:
            name: The name of the toggle script
            export_path: The path to export to

        Returns:
            Tuple of (success, message)
        """
        # Get script configuration
        script_config = self.config_manager.get_script(name)
        if not script_config:
            return False, f"Toggle script '{name}' not found"

        # Get script path
        script_path = script_config.get("script_path", "")
        if not script_path or not os.path.exists(script_path):
            # Try to generate the script if it doesn't exist
            success, message = self.script_generator.generate_script(name)
            if not success:
                return False, f"Script file not found and could not be generated: {message}"

            # Get updated script config with path
            script_config = self.config_manager.get_script(name)
            script_path = script_config.get("script_path", "")

        # Export the script
        try:
            shutil.copy2(script_path, export_path)
            os.chmod(export_path, 0o755)  # Make executable
            return True, f"Exported toggle script to {export_path}"
        except Exception as e:
            logger.error(f"Error exporting toggle script {name}: {e}")
            return False, f"Error exporting toggle script: {str(e)}"