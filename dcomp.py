import subprocess
import sys
import os
import platform
import json
import shutil
import uuid
import logging
import threading
import time
import psutil
import requests
from flask import Flask, render_template

# Enhanced Logging Configuration for Robustness and Debugging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants for enhanced clarity and maintainability
SWARM_AGENT_SCRIPT_NAME = "swarm_agent.py"
OBSERVER_DASHBOARD_SCRIPT_NAME = "observer_dashboard.py"
UNINSTALL_SCRIPT_WINDOWS_NAME = "uninstall_singularity_mesh.bat"
UNINSTALL_SCRIPT_POSIX_NAME = "uninstall_singularity_mesh.sh"
TEMPLATES_DIR_NAME = "templates"
DASHBOARD_HTML_NAME = "dashboard.html"
ERROR_HTML_NAME = "error.html"
AGENT_CONFIG_FILE = "swarm_agent_config.json"
DASHBOARD_CONFIG_FILE = "observer_dashboard_config.json"
IPFS_CONFIG_FILE = "ipfs_config.json" # Placeholder for future IPFS configuration management

# --- Configuration Management ---
def load_config(config_file):
    """Load configuration from a JSON file, creating default if not exists."""
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_config(config_file, config_data):
    """Save configuration data to a JSON file."""
    with open(config_file, 'w') as f:
        json.dump(config_data, f, indent=4, sort_keys=True) # Added sort_keys for consistent output

def generate_node_id():
    """Generate a unique node ID using UUID."""
    return str(uuid.uuid4())

# --- Dependency Installation ---
def install_dependencies():
    """Installs required Python packages, handling potential blinker conflicts."""
    logging.info("Starting dependency installation...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install",
                                 "ipfshttpclient", "psutil", "flask", "requests",
                                 "--ignore-installed", "blinker"], # Explicitly ignore blinker to avoid conflicts
                                stdout=subprocess.DEVNULL, # Suppress output for cleaner installation
                                stderr=subprocess.DEVNULL)
        logging.info("Dependencies installed successfully (blinker conflict avoided).")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error during dependency installation: {e}")
        logging.warning("Dependency installation issues encountered. Singularity Mesh may still function if dependencies are system-wide.")
        logging.warning("Consider using a Python virtual environment (venv) for isolated and reliable deployments.")
        # Proceed with deployment even if dependency installation fails - for maximum automation and resilience

# --- IPFS Configuration and Setup ---
def configure_ipfs():
    """Configures IPFS, initializes if necessary, and handles IPFS installation check."""
    logging.info("Starting IPFS configuration...")
    try:
        ipfs_path = os.path.expanduser("~/.ipfs")
        if not os.path.exists(ipfs_path):
            logging.info("Initializing IPFS...")
            subprocess.check_call(["ipfs", "init"],
                                    stdout=subprocess.DEVNULL, # Suppress init output
                                    stderr=subprocess.DEVNULL)
            logging.info("IPFS initialized.")
        else:
            logging.info("IPFS already initialized.")

        # Basic IPFS connectivity test - enhanced for robustness
        try:
            subprocess.check_output(["ipfs", "id"], timeout=10) # Timeout to prevent indefinite hang
            logging.info("IPFS command-line tools are functional.")
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
            logging.error(f"IPFS command-line tools check failed: {e}")
            logging.error("Please ensure IPFS is correctly installed and accessible in your system's PATH.")
            logging.error("Refer to IPFS documentation: https://docs.ipfs.tech/install/")
            sys.exit(1) # Exit if IPFS is not functional

    except FileNotFoundError:
        logging.error("IPFS command 'ipfs' not found. IPFS command-line tools are required.")
        logging.error("Please ensure IPFS is installed and added to your system's PATH.")
        logging.error("Refer to IPFS documentation for installation: https://docs.ipfs.tech/install/")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        logging.error(f"Error configuring IPFS: {e}")
        sys.exit(1)

# --- Swarm Agent Deployment ---
def deploy_swarm_agent():
    """Deploys the Swarm Agent script, embedding configuration and AI logic."""
    logging.info("Deploying Swarm Agent...")

    node_id = generate_node_id() # Generate unique Node ID on deployment
    agent_config = {
        "node_id": node_id,
        "ipfs_pubsub_topic": "omnitide_swarm_tasks", # Standard topic for task communication
        "resource_advertisement_interval": 30, # seconds, adjust as needed
        "task_execution_timeout": 60 # seconds, task timeout
    }
    save_config(AGENT_CONFIG_FILE, agent_config) # Save agent config

    agent_script_content = f"""
import ipfshttpclient
import psutil
import time
import json
import subprocess
import logging
import uuid

# --- Enhanced Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(node_id)s - %(message)s')

AGENT_CONFIG_FILE = "{AGENT_CONFIG_FILE}"
TASK_EXECUTION_TIMEOUT = 60 # Default task timeout in seconds, can be overridden in config

def load_agent_config():
    \"\"\"Loads agent configuration from JSON file.\"\"\"
    try:
        with open(AGENT_CONFIG_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Configuration file error: {{e}}")
        return {{}}

class SwarmAgent:
    \"\"\"Represents a Swarm Agent node in the distributed computing network.\"\"\"

    def __init__(self):
        \"\"\"Initializes the Swarm Agent, loads configuration, and connects to IPFS.\"\"\"
        self.config = load_agent_config()
        self.node_id = self.config.get("node_id", "UNKNOWN_NODE_ID")
        self.ipfs_pubsub_topic = self.config.get("ipfs_pubsub_topic", "omnitide_swarm_tasks")
        self.resource_advertisement_interval = self.config.get("resource_advertisement_interval", 30)
        self.task_execution_timeout = self.config.get("task_execution_timeout", TASK_EXECUTION_TIMEOUT)
        self.logger = logging.LoggerAdapter(logging.getLogger(__name__), {{'node_id': self.node_id}}) # Logger with node_id context

        try:
            self.ipfs_client = ipfshttpclient.connect()
            self.logger.info(f"Agent initialized. IPFS Node ID: {{self.ipfs_client.id()['ID']}}")
        except Exception as e:
            self.logger.error(f"IPFS connection error: {{e}}")
            self.logger.error("Agent will run in resource advertising mode only.")
            self.ipfs_client = None

        self.resource_info = self.get_resource_info()
        self.task_queue = []
        self.task_execution_history = []
        self.is_running = False # Flag to control agent's main loop


    def get_resource_info(self):
        \"\"\"Collects and returns system resource information.\"\"\"
        ipfs_id = self.ipfs_client.id()['ID'] if self.ipfs_client else "IPFS_Not_Connected"
        return {{
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'node_id': self.node_id,
            'ipfs_node_id': ipfs_id,
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
        }}

    def advertise_resources(self):
        \"\"\"Publishes resource information to the IPFS PubSub topic.\"\"\"
        if not self.ipfs_client:
            self.logger.warning("Resource advertising disabled: IPFS client not initialized.")
            return

        resource_data = self.get_resource_info()
        self.logger.info(f"Advertising resources: {{resource_data}}")
        try:
            self.ipfs_client.pubsub.publish(self.ipfs_pubsub_topic, json.dumps(resource_data))
        except Exception as e:
            self.logger.error(f"Error publishing resource info to IPFS PubSub: {{e}}")


    def fetch_tasks(self):
        \"\"\"Fetches tasks from the IPFS PubSub topic with enhanced subscription handling.\"\"\"
        if not self.ipfs_client:
            self.logger.warning("Task fetching disabled: IPFS client not initialized.")
            return []

        if self.task_queue: # Prioritize existing tasks in queue
            return self.task_queue

        try:
            self.logger.info("Fetching new tasks from IPFS PubSub...")
            messages = self.ipfs_client.pubsub.subscribe(self.ipfs_pubsub_topic, timeout=5) # Reduced timeout
            task_count = 0
            for message in messages:
                if message['from'] != self.ipfs_client.id()['ID'] and message['data']:
                    try:
                        task_data = json.loads(message['data'].decode('utf-8'))
                        if self.validate_task(task_data): # Validate task structure before adding to queue
                            task_data['task_internal_id'] = str(uuid.uuid4()) # Assign unique internal ID
                            self.task_queue.append(task_data)
                            task_count += 1
                            self.logger.info(f"Task received: {{task_data.get('task_id', 'N/A')}}, Internal ID: {{task_data['task_internal_id']}}")
                        else:
                            self.logger.warning(f"Invalid task format received, ignoring: {{task_data}}")
                    except json.JSONDecodeError:
                        self.logger.warning("Non-JSON message received on PubSub, ignoring.")
                if task_count >= 5: # Limit tasks fetched per cycle to prevent queue overload - adjust as needed
                    self.logger.info("Fetched maximum tasks per cycle. Processing queue.")
                    break # Break after fetching a reasonable number of tasks

            if not self.task_queue:
                self.logger.debug("No new tasks fetched in this cycle.") # Debug log when no new tasks

        except Exception as e:
            self.logger.error(f"Error fetching tasks from IPFS PubSub: {{e}}")
        return self.task_queue


    def validate_task(self, task_data):
        \"\"\"Validates the structure of a task data dictionary.\"\"\"
        required_keys = ['task_id', 'instruction']
        if not isinstance(task_data, dict):
            return False
        return all(key in task_data for key in required_keys)


    def execute_task(self, task):
        \"\"\"Executes a task using subprocess with timeout and enhanced error handling.\"\"\"
        task_id = task.get('task_id', 'UNKNOWN_TASK_ID')
        task_internal_id = task.get('task_internal_id', 'N/A') # Retrieve internal task ID
        instruction = task.get('instruction')

        if not instruction:
            self.logger.warning(f"Task {{task_id}}, Internal ID: {{task_internal_id}} has no instruction. Skipping.")
            return

        self.logger.info(f"Executing task: {{task_id}}, Internal ID: {{task_internal_id}}, Instruction: {{instruction}}")
        start_time = time.time()
        process = None

        try:
            process = subprocess.Popen(['python', '-c', instruction],
                                    shell=False,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    timeout=self.task_execution_timeout)

            stdout, stderr = process.communicate()
            return_code = process.returncode # Capture return code immediately

            if return_code == 0:
                self.logger.info(f"Task {{task_id}}, Internal ID: {{task_internal_id}} completed successfully.")
                self.logger.debug(f"Task {{task_id}}, Internal ID: {{task_internal_id}} stdout: {{stdout.decode()}}")
            else:
                self.logger.error(f"Task {{task_id}}, Internal ID: {{task_internal_id}} failed, Return Code: {{return_code}}")
                self.logger.error(f"Task {{task_id}}, Internal ID: {{task_internal_id}} stderr: {{stderr.decode()}}")


            self.task_execution_history.append({{
                'task_id': task_id,
                'task_internal_id': task_internal_id,
                'status': 'success' if return_code == 0 else 'failed',
                'start_time': start_time,
                'end_time': time.time(),
                'return_code': return_code,
                'stdout': stdout.decode(),
                'stderr': stderr.decode()
            }})


        except subprocess.TimeoutExpired:
            self.logger.warning(f"Task {{task_id}}, Internal ID: {{task_internal_id}} timed out. Terminating.")
            if process:
                process.terminate()
            self.task_execution_history.append({{
                'task_id': task_id,
                'task_internal_id': task_internal_id,
                'status': 'timeout',
                'start_time': start_time,
                'end_time': time.time(),
                'return_code': None,
                'stdout': '',
                'stderr': 'Task execution timed out'
            }})

        except Exception as e:
            self.logger.error(f"Error executing task {{task_id}}, Internal ID: {{task_internal_id}}: {{e}}")
            self.task_execution_history.append({{
                'task_id': task_id,
                'task_internal_id': task_internal_id,
                'status': 'exception',
                'start_time': start_time,
                'end_time': time.time(),
                'return_code': None,
                'stdout': '',
                'stderr': str(e)
            }})


    def start(self):
        \"\"\"Starts the Swarm Agent main loop in a separate thread.\"\"\"
        if not self.is_running:
            self.is_running = True
            self.agent_thread = threading.Thread(target=self._run_loop, daemon=True) # Daemon thread for background execution
            self.agent_thread.start()
            self.logger.info("Swarm Agent main loop started in background thread.")


    def stop(self):
        \"\"\"Stops the Swarm Agent main loop gracefully.\"\"\"
        if self.is_running:
            self.is_running = False
            self.agent_thread.join(timeout=10) # Wait for thread to stop, with timeout
            self.logger.info("Swarm Agent main loop stopped.")
        else:
            self.logger.info("Swarm Agent is not running.")


    def _run_loop(self):
        \"\"\"Main loop for the Swarm Agent, handling resource advertising and task execution.\"\"\"
        self.logger.info(f"Agent main loop started. Node ID: {{self.node_id}}")
        resource_advertisement_timer = 0

        while self.is_running: # Loop controlled by is_running flag
            current_time = time.time()
            if current_time - resource_advertisement_timer >= self.resource_advertisement_interval:
                self.advertise_resources()
                resource_advertisement_timer = current_time

            tasks_to_execute = self.fetch_tasks()
            if tasks_to_execute:
                task = tasks_to_execute.pop(0)
                self.execute_task(task)
            else:
                self.logger.debug("No tasks in queue. Waiting...")

            time.sleep(5) # Reduced sleep for responsiveness

        self.logger.info("Agent main loop завершено.") # Loop завершено when is_running is False



    def run_agent_cli(self):
        \"\"\"Provides a basic command-line interface for agent control and status.\"\"\"
        self.start() # Start agent in background

        try:
            while True:
                command = input("Agent Command (status/tasks/stop/exit): ").strip().lower()
                if command == 'status':
                    print(f"Node ID: {{self.node_id}}, IPFS ID: {{self.resource_info['ipfs_node_id']}}, CPU: {{self.resource_info['cpu_percent']}}%, Memory: {{self.resource_info['memory_percent']}}%, Disk: {{self.resource_info['disk_percent']}}%, Running: {{self.is_running}}")
                elif command == 'tasks':
                    print("Task Queue:")
                    for task in self.task_queue:
                        print(f"  - Task ID: {{task.get('task_id', 'N/A')}}, Internal ID: {{task.get('task_internal_id', 'N/A')}}, Instruction: {{task.get('instruction', 'N/A')}}")
                    print("\\nTask Execution History:")
                    for history_item in self.task_execution_history:
                        print(f"  - Task ID: {{history_item.get('task_id', 'N/A')}}, Internal ID: {{history_item.get('task_internal_id', 'N/A')}}, Status: {{history_item.get('status', 'N/A')}}, Return Code: {{history_item.get('return_code', 'N/A')}}, Start: {{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(history_item.get('start_time', 0))) if history_item.get('start_time') else 'N/A'}}, End: {{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(history_item.get('end_time', 0))) if history_item.get('end_time') else 'N/A'}}") # Formatted timestamps
                elif command == 'stop':
                    self.stop()
                    break # Exit CLI loop after stopping agent
                elif command == 'exit':
                    if self.is_running:
                        self.stop() # Stop agent before exiting
                    break # Exit CLI loop
                elif command == 'help':
                    print("Available commands: status, tasks, stop, exit, help")
                else:
                    print("Invalid command. Type 'help' for available commands.")

        except KeyboardInterrupt:
            print("\\nAgent CLI interrupted. Stopping agent...")
            self.stop()
        finally:
            print("Agent CLI завершено.") # CLI завершено on exit


if __name__ == "__main__":
    agent = SwarmAgent()
    agent.run_agent_cli() # Start agent with CLI control
"""
    with open(SWARM_AGENT_SCRIPT_NAME, "w") as f:
        f.write(agent_script_content)
    logging.info("Swarm Agent deployed.")


# --- Observer Dashboard Deployment ---
def deploy_observer_dashboard():
    """Deploys the optional Observer Dashboard, including Flask app and templates."""
    logging.info("Deploying Observer Dashboard (Optional)...")

    dashboard_config = {
        "dashboard_port": 5000 # Standard port for Flask development server
    }
    save_config(DASHBOARD_CONFIG_FILE, dashboard_config) # Save dashboard config

    dashboard_script_content = f"""
from flask import Flask, render_template
import ipfshttpclient
import psutil
import time
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DASHBOARD_CONFIG_FILE = "{DASHBOARD_CONFIG_FILE}"

def load_dashboard_config():
    try:
        with open(DASHBOARD_CONFIG_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Dashboard config load error: {{e}}")
        return {{}}


app = Flask(__name__)
dashboard_config = load_dashboard_config()
dashboard_port = dashboard_config.get("dashboard_port", 5000)


@app.route('/')
def dashboard():
    \"\"\"Renders the main dashboard page with node information.\"\"\"
    try:
        ipfs_client = ipfshttpclient.connect()
        node_id = ipfs_client.id()['ID']
        resource_info = get_resource_info()
        return render_template('{DASHBOARD_HTML_NAME}', node_id=node_id, resource_info=resource_info)
    except Exception as e:
        logging.error(f"Dashboard data fetch error: {{e}}")
        return render_template('{ERROR_HTML_NAME}', error=str(e))

def get_resource_info():
    \"\"\"Retrieves resource usage information using psutil.\"\"\"
    return {{
        'cpu_percent': psutil.cpu_percent(),
        'memory_percent': psutil.virtual_memory().percent,
        'disk_percent': psutil.disk_usage('/').percent,
        'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
    }}

if __name__ == '__main__':
    logging.info(f"Starting Observer Dashboard on port {{dashboard_port}}...")
    app.run(debug=True, host='0.0.0.0', port=dashboard_port)
"""
    with open(OBSERVER_DASHBOARD_SCRIPT_NAME, "w") as f:
        f.write(dashboard_script_content)

    templates_dir = os.path.join(os.getcwd(), TEMPLATES_DIR_NAME)
    os.makedirs(templates_dir, exist_ok=True)

    dashboard_html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Swarm Observer Dashboard</title>
    <meta http-equiv="refresh" content="5">
    <style>
        body {{ font-family: sans-serif; }}
        .dashboard-container {{ width: 80%; margin: 20px auto; }}
        .section {{ margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .section h2 {{ margin-top: 0; }}
        .data-item {{ margin-bottom: 8px; }}
    </style>
</head>
<body>
    <div class="dashboard-container">
        <div class="section">
            <h2>Swarm Node Dashboard</h2>
            <div class="data-item"><strong>Node ID:</strong> {{ node_id }}</div>
            <div class="data-item"><strong>Last Updated:</strong> {{ resource_info.timestamp }}</div>
        </div>
        <div class="section">
            <h3>Resource Usage:</h3>
            <div class="data-item"><strong>CPU:</strong> {{ resource_info.cpu_percent }}%</div>
            <div class="data-item"><strong>Memory:</strong> {{ resource_info.memory_percent }}%</div>
            <div class="data-item"><strong>Disk:</strong> {{ resource_info.disk_percent }}%</div>
        </div>
        <p>Dashboard auto-updating every 5 seconds.</p>
    </div>
</body>
</html>
"""
    error_html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Swarm Observer Dashboard - Error</title>
</head>
<body>
    <div class="dashboard-container">
        <h1>Error</h1>
        <p>Failed to load dashboard data. Please check console logs for details.</p>
        <p><strong>Error Message:</strong> {{ error }}</p>
    </div>
</body>
</html>
"""
    with open(os.path.join(templates_dir, DASHBOARD_HTML_NAME), 'w') as f:
        f.write(dashboard_html_content)
    with open(os.path.join(templates_dir, ERROR_HTML_NAME), 'w') as f:
        f.write(error_html_content)

    logging.info("Observer Dashboard (Optional) deployed. Run observer_dashboard.py to start.")


# --- Uninstall Script Creation ---
def create_uninstall_script():
    """Creates platform-specific uninstall scripts for clean removal."""
    logging.info("Creating Uninstall Script...")
    uninstall_script_content_windows = f"""
@echo off
echo Uninstalling Singularity Mesh...
taskkill /F /IM python.exe /T >nul 2>&1
del /f "{SWARM_AGENT_SCRIPT_NAME}"
del /f "{OBSERVER_DASHBOARD_SCRIPT_NAME}"
del /f "{AGENT_CONFIG_FILE}"
del /f "{DASHBOARD_CONFIG_FILE}"
rmdir /s /q "{TEMPLATES_DIR_NAME}"
echo Singularity Mesh uninstalled.
pause
"""
    uninstall_script_content_posix = f"""#!/bin/bash
echo "Uninstalling Singularity Mesh..."
pkill -f "python {SWARM_AGENT_SCRIPT_NAME}" || true
pkill -f "python {OBSERVER_DASHBOARD_SCRIPT_NAME}" || true
rm -f "{SWARM_AGENT_SCRIPT_NAME}"
rm -f "{OBSERVER_DASHBOARD_SCRIPT_NAME}"
rm -f "{AGENT_CONFIG_FILE}"
rm -f "{DASHBOARD_CONFIG_FILE}"
rm -rf "{TEMPLATES_DIR_NAME}"
echo "Singularity Mesh uninstalled."
"""

    if platform.system() == "Windows":
        with open(UNINSTALL_SCRIPT_WINDOWS_NAME, "w") as f:
            f.write(uninstall_script_content_windows)
        logging.info(f"Uninstall script created: {UNINSTALL_SCRIPT_WINDOWS_NAME}")
    else: # Assuming POSIX-like system (Linux, macOS)
        with open(UNINSTALL_SCRIPT_POSIX_NAME, "w") as f:
            f.write(uninstall_script_content_posix)
        subprocess.check_call(["chmod", "+x", UNINSTALL_SCRIPT_POSIX_NAME]) # Make executable
        logging.info(f"Uninstall script created: {UNINSTALL_SCRIPT_POSIX_NAME}")

# --- Main Installer Function ---
def main():
    """Main installation function orchestrating the deployment process."""
    logging.info("Starting Ethereal Installer for Singularity Mesh...")
    install_dependencies() # Install Python dependencies
    configure_ipfs()      # Configure IPFS and check installation
    deploy_swarm_agent()  # Deploy Swarm Agent script with embedded logic
    deploy_observer_dashboard() # Deploy optional Observer Dashboard
    create_uninstall_script() # Create platform-specific uninstall scripts

    logging.info("\n----------------------------------------------------------")
    logging.info("              Singularity Mesh Installation Complete!         ")
    logging.info("----------------------------------------------------------")
    logging.info(f"\nTo run the Swarm Agent, execute: python {SWARM_AGENT_SCRIPT_NAME}")
    logging.info(f"  - For command-line control, use: python {SWARM_AGENT_SCRIPT_NAME}") # Clarified agent execution
    logging.info(f"  - To start agent in background (no CLI):  python {SWARM_AGENT_SCRIPT_NAME} --no-cli") # Added background start option
    logging.info(f"To run the Observer Dashboard (optional), execute: python {OBSERVER_DASHBOARD_SCRIPT_NAME} (and open in browser at http://<your_ip>:{load_config(DASHBOARD_CONFIG_FILE).get('dashboard_port', 5000)})")
    logging.info(f"\nRun {UNINSTALL_SCRIPT_WINDOWS_NAME} (Windows) or ./{UNINSTALL_SCRIPT_POSIX_NAME} (macOS/Linux) to uninstall.")
    logging.info("----------------------------------------------------------")

if __name__ == "__main__":
    if "--no-cli" in sys.argv: # Check for --no-cli argument to run agent without CLI
        agent = SwarmAgent()
        agent.start() # Start agent in background, no CLI
        logging.info("Swarm Agent started in background (no CLI).")
        while True: # Keep main thread alive in background mode
            time.sleep(60) # Keep main thread alive, check every minute (adjust as needed)

    else:
        main() # Run installer and default to CLI agent run
