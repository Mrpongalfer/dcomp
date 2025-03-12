# dcomp
Distributed Computing setup using IPFS 
# Singularity Mesh: Ethereal Installer and Distributed Computing Framework

## Introduction

Singularity Mesh is a lightweight, self-deploying framework for creating a decentralized distributed computing network. It leverages IPFS (InterPlanetary File System) for peer-to-peer communication and resource advertisement, enabling nodes to discover each other and contribute computational resources to a shared task pool.

This framework is designed for maximum automation and ease of deployment, embodying the principles of AI-driven infrastructure management. The `ethereal_installer.py` script automates the entire setup process, from dependency installation to agent and dashboard deployment, requiring minimal manual intervention.

## Features

*   **Automated Deployment:**  Fully automated installation and configuration using the `ethereal_installer.py` script.
*   **Decentralized Architecture:** Utilizes IPFS for peer discovery and task distribution, creating a resilient and scalable network.
*   **Resource Advertisement:** Swarm Agents automatically advertise their CPU, Memory, and Disk resources to the network.
*   **Task Execution:** Agents fetch and securely execute tasks from a shared task queue, contributing computational power to the mesh.
*   **Optional Observer Dashboard:** Provides a web-based dashboard for monitoring node resources in real-time.
*   **Command-Line Interface (CLI) for Agent Control:** Offers a simple CLI for managing and monitoring Swarm Agents.
*   **Background Agent Execution:** Agents can run in the background without a CLI for silent operation.
*   **Easy Uninstallation:** Includes platform-specific uninstall scripts for clean removal of all components.
*   **Robust Error Handling and Logging:** Comprehensive logging throughout the installer and agent scripts for debugging and monitoring.
*   **Configuration Files:** Uses JSON configuration files for agent and dashboard settings, allowing for customization.
*   **Secure Task Execution:** Employs `subprocess.Popen` with timeouts for safer and more controlled task execution.

## Getting Started

### Prerequisites

*   **Python 3.x:**  Ensure Python 3 and `pip` are installed on your system.
*   **IPFS Desktop (Recommended) or IPFS Command-Line Tools:**
    *   **IPFS Desktop (Recommended for ease of use):** Download and install [IPFS Desktop](https://docs.ipfs.tech/install/ipfs-desktop/).  While IPFS Desktop provides a user-friendly interface, ensure the IPFS command-line tools are also accessible in your system's PATH for Singularity Mesh to function correctly in a command-line environment.
    *   **IPFS Command-Line Tools (Alternative):** Follow the installation instructions for IPFS command-line tools from the official [IPFS documentation](https://docs.ipfs.tech/install/command-line/). Ensure the `ipfs` command is accessible in your system's PATH.

### Installation

1.  **Download `ethereal_installer.py` and `templates` folder:** Ensure you have downloaded the `ethereal_installer.py` script and the `templates` folder (containing `dashboard.html` and `error.html`) to your desired installation directory.
2.  **Run the Installer:** Open your command prompt or terminal, navigate to the directory where you saved `ethereal_installer.py`, and execute the installer script:

    ```bash
    python ethereal_installer.py
    ```

    *   The installer will:
        *   Install required Python dependencies.
        *   Configure and verify IPFS installation.
        *   Deploy the `swarm_agent.py` script.
        *   Deploy the `observer_dashboard.py` script and templates (optional dashboard).
        *   Create platform-specific uninstall scripts.
    *   Upon successful installation, you will see a completion message with instructions on running the Swarm Agent and Observer Dashboard.

### Running the Swarm Agent

*   **Start IPFS Daemon:** Before starting the Swarm Agent, ensure the IPFS daemon is running on your machine. Open a new terminal or command prompt and run:

    ```bash
    ipfs daemon
    ```

    Leave this terminal window running in the background.

*   **Run Swarm Agent with CLI Control:** To start the Swarm Agent with a command-line interface for monitoring and control, open another terminal or command prompt, navigate to the installation directory, and execute:

    ```bash
    python swarm_agent.py
    ```

    *   The agent CLI will start, providing commands like `status`, `tasks`, `stop`, `exit`, and `help`.

*   **Run Swarm Agent in Background (No CLI):** To run the Swarm Agent silently in the background without the CLI, execute:

    ```bash
    python swarm_agent.py --no-cli
    ```

    *   In this mode, the agent will run in the background, advertising resources and processing tasks without user interaction in the terminal.

### Running the Observer Dashboard (Optional)

1.  **Start the Observer Dashboard:** Open a new terminal or command prompt, navigate to the installation directory, and execute:

    ```bash
    python observer_dashboard.py
    ```

    *   The dashboard will start a Flask development server.

2.  **Access the Dashboard in your Browser:** Open a web browser and go to the address provided in the console output (typically `http://127.0.0.1:5000/` or `http://0.0.0.0:5000/`).

    *   The dashboard will display real-time resource usage (CPU, Memory, Disk) for the node where it is running, along with the Node ID and last updated timestamp.
    *   The dashboard auto-refreshes every 5 seconds to provide near real-time monitoring.

### Submitting Tasks to the Swarm

*   **Using IPFS PubSub:** Tasks are submitted to the Swarm Agents via IPFS PubSub. You can use the IPFS command-line tools to publish tasks to the `omnitide_swarm_tasks` topic.

    *   **Task Format:** Tasks should be published as JSON messages with the following structure:

        ```json
        {
            "task_id": "your_task_id",
            "instruction": "python_code_to_execute"
        }
        ```

    *   **Example Task Submission:** To submit a task that prints a message with the node's platform information, use the following IPFS command:

        ```bash
        ipfs pubsub pub omnitide_swarm_tasks '{"task_id": "system_info_task", "instruction": "import platform; print(f\'System Info Task executed on node: {platform.system()} {platform.release()} {platform.machine()}\') "}'
        ```

    *   **Important:** Replace `"python_code_to_execute"` with the actual Python code you want the Swarm Agents to execute. Keep tasks short and non-interactive for this basic example.

### Architecture

Singularity Mesh operates on a decentralized architecture leveraging IPFS PubSub for communication.

*   **Swarm Agent (`swarm_agent.py`):**
    *   The core component running on each node.
    *   Responsible for:
        *   Monitoring and advertising node resources (CPU, Memory, Disk) to the IPFS network via PubSub.
        *   Subscribing to the IPFS PubSub topic (`omnitide_swarm_tasks`) to fetch tasks.
        *   Executing tasks securely using `subprocess.Popen` with timeouts.
        *   Maintaining a task queue and execution history.
        *   Providing a command-line interface (CLI) for control and monitoring (optional).

*   **Observer Dashboard (`observer_dashboard.py`):**
    *   An optional Flask web application for monitoring node resources.
    *   Provides a real-time view of resource usage for the node where it is running.
    *   Connects to the local IPFS node to retrieve node ID.
    *   Uses `psutil` to gather system resource information.
    *   Renders a dynamic dashboard webpage using HTML templates.

*   **IPFS (InterPlanetary File System):**
    *   The decentralized communication backbone of Singularity Mesh.
    *   Used for:
        *   **Peer Discovery:** Agents implicitly discover each other through the IPFS network.
        *   **Resource Advertisement:** Agents publish resource information to the `omnitide_swarm_tasks` PubSub topic.
        *   **Task Distribution:** Tasks are published to the `omnitide_swarm_tasks` PubSub topic, and agents subscribe to receive and process them.

### Security Considerations

*   **Task Execution Environment:**  Tasks are executed using `subprocess.Popen` in a separate Python process, which provides some level of isolation. However, for production environments, **it is crucial to implement a more robust, sandboxed task execution environment** (e.g., using containers or secure sandboxing libraries) to mitigate the risks of executing arbitrary code received over the network.
*   **IPFS PubSub Security:** Basic IPFS PubSub is not encrypted or authenticated. For sensitive tasks or deployments in untrusted environments, consider using IPFS Cluster or other secure, decentralized task queueing systems that offer encryption and authentication.
*   **Network Security:** Ensure your network is properly secured, especially if deploying Singularity Mesh across a public network. Consider using firewalls and network segmentation to limit exposure.
*   **Resource Monitoring:** The Observer Dashboard provides basic resource monitoring. For production deployments, implement more comprehensive monitoring and alerting systems to track node health and performance.

### Troubleshooting

*   **IPFS Daemon Not Running:** Ensure the IPFS daemon (`ipfs daemon`) is running before starting Swarm Agents or the Observer Dashboard.
*   **"ipfs" command not found:** Verify that IPFS command-line tools are installed and correctly added to your system's PATH environment variable. Re-run the installer or manually configure your PATH if necessary.
*   **Dependency Installation Errors:** If you encounter errors during dependency installation, ensure you have Python 3.x and `pip` installed. You can try running the installer again. If issues persist, consider using a Python virtual environment (`venv`) to isolate dependencies.
*   **Dashboard Not Accessible:** If you cannot access the Observer Dashboard in your browser, ensure the `observer_dashboard.py` script is running and check the console output for the correct access URL (typically `http://127.0.0.1:5000/` or `http://0.0.0.0:5000/`). Also, check if any firewalls are blocking access to the dashboard port (default: 5000).
*   **Agent Not Fetching Tasks:** Verify that both Swarm Agents and the task submission process are connected to the same IPFS network and PubSub topic (`omnitide_swarm_tasks`). Check the Swarm Agent logs for any errors related to IPFS connection or PubSub subscription.

### Uninstallation

To uninstall Singularity Mesh, run the appropriate uninstall script created during installation:

*   **Windows:** Run `uninstall_singularity_mesh.bat`
*   **macOS/Linux:** Run `./uninstall_singularity_mesh.sh` in your terminal.

    *   The uninstall script will stop any running Swarm Agent and Observer Dashboard processes, delete the deployed scripts, configuration files, and the `templates` directory.

### Future Enhancements

*   **Enhanced Task Management:** Implement a more robust task queueing system with features like task prioritization, persistence, and result tracking.
*   **Secure Task Sandboxing:** Integrate containerization (Docker, Podman) or secure sandboxing libraries to create isolated and secure task execution environments.
*   **Advanced Resource Management:** Implement dynamic resource allocation and scheduling algorithms for optimized task distribution.
*   **Fault Tolerance and Self-Healing:** Enhance the framework's resilience with automatic node recovery and task redistribution mechanisms.
*   **Monitoring and Alerting:** Develop a more comprehensive monitoring and alerting system for network health and performance.
*   **Task Result Aggregation:** Implement mechanisms for collecting and aggregating task results from distributed agents.
*   **User Interface for Task Submission and Management:** Create a user-friendly web interface or CLI for submitting and managing tasks.
*   **Security Enhancements:** Integrate encryption and authentication for IPFS PubSub communication and task data.

### Contributing

Contributions to Singularity Mesh are welcome! Please feel free to fork the repository, submit pull requests, and report issues.

### License


---

This `README.md` provides a comprehensive overview of Singularity Mesh, including installation, usage, architecture, security considerations, troubleshooting, and future enhancements. It should serve as excellent documentation for users and developers.
