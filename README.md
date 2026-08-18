# AgentForge Agents

Agent execution and orchestration layer for **AgentForge**.

The `agentforge-agents` repository contains the core agent abstractions, built-in agents, agent configuration system, tool system, registry, and execution-related components used by the AgentForge platform.

## Overview

The Agents repository is responsible for:

* Defining the base agent architecture
* Providing built-in AI agents
* Loading agents dynamically from configuration
* Registering and managing available agents
* Providing a reusable tool system
* Managing tool permissions
* Defining agent configuration, context, results, and exceptions
* Supporting asynchronous agent execution
* Integrating AI and external service capabilities

## Project Structure

```text
agentforge-agents/
│
├── app/
│   ├── agents/
│   │   ├── base/
│   │   │   ├── agent.py
│   │   │   ├── config.py
│   │   │   ├── context.py
│   │   │   ├── exceptions.py
│   │   │   └── result.py
│   │   │
│   │   ├── built_in/
│   │   │   ├── automation_agent.py
│   │   │   ├── coding_agent.py
│   │   │   ├── data_agent.py
│   │   │   └── research_agent.py
│   │   │
│   │   ├── registry/
│   │   │   ├── loader.py
│   │   │   └── registry.py
│   │   │
│   │   └── tools/
│   │       ├── base.py
│   │       ├── permission.py
│   │       ├── registry.py
│   │       └── web_search.py
│   │
│   └── __init__.py
│
├── configs/
│   └── agents/
│       ├── automation_agent.yaml
│       ├── coding_agent.yaml
│       ├── data_agent.yaml
│       └── research_agent.yaml
│
├── tests/
│   └── unit/
│       ├── test_agent.py
│       └── test_registry.py
│
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

## Built-in Agents

The repository currently provides four configured built-in agents.

### Automation Agent

Designed for automation-oriented agent workflows and task execution.

Configuration:

```text
configs/agents/automation_agent.yaml
```

### Coding Agent

Designed for software development and coding-related tasks.

Configuration:

```text
configs/agents/coding_agent.yaml
```

### Data Agent

Designed for data-related processing and analysis workflows.

Configuration:

```text
configs/agents/data_agent.yaml
```

### Research Agent

Designed for research and information-gathering workflows.

Configuration:

```text
configs/agents/research_agent.yaml
```

## Agent Architecture

All agents are expected to derive from the common `BaseAgent` abstraction.

The basic architecture is:

```text
                 ┌──────────────────┐
                 │    BaseAgent     │
                 └────────┬─────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
 CodingAgent       DataAgent        ResearchAgent
        │                 │                 │
        └─────────────────┼─────────────────┘
                          │
                   AutomationAgent
```

The registry validates that loaded agent classes are subclasses of `BaseAgent` before registering them.

## Agent Configuration

Agents can be configured through YAML files located under:

```text
configs/agents/
```

The registry loader determines the agent module and class from the configuration and dynamically imports the required class.

The general loading flow is:

```text
YAML Configuration
        │
        ▼
   AgentLoader
        │
        ▼
 Dynamic Import
        │
        ▼
 Validate BaseAgent
        │
        ▼
 AgentRegistry
        │
        ▼
 Registered Agent
```

This allows agents to be added or modified without hard-coding every agent directly into the registry.

## Tool System

The repository contains a reusable tool system under:

```text
app/agents/tools/
```

The tool layer provides:

* Base tool abstractions
* Tool input/output definitions
* Tool registration
* Tool permissions
* Web-search capabilities

Important components include:

```text
BaseTool
ToolInput
ToolOutput
ToolRegistry
ToolPermissions
```

## Installation

### Requirements

* Python 3.9 or newer
* `pip`
* Recommended: Python virtual environment

### Create Virtual Environment

Windows PowerShell:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Install Dependencies

```powershell
python -m pip install -r requirements.txt
```

For development dependencies:

```powershell
python -m pip install -r requirements-dev.txt
```

### Editable Installation

The package can also be installed in editable mode:

```powershell
python -m pip install -e .
```

## Testing

Run the complete test suite:

```powershell
python -m pytest -v
```

The current repository test suite verifies agent execution and registry functionality.

## Compilation Check

To check all Python files for syntax and compilation errors:

```powershell
python -m compileall -q .
```

A successful command with no output indicates that no Python compilation errors were detected.

## Dependency Validation

Check for broken or incompatible installed dependencies:

```powershell
python -m pip check
```

Expected result:

```text
No broken requirements found.
```

## Agent Registry Validation

The registry can load configured agents dynamically through `AgentLoader`.

The configured agents are located in:

```text
configs/agents/
```

Currently configured agents:

```text
automation_agent
coding_agent
data_agent
research_agent
```

## Development Tools

The project uses the following development tools:

* **pytest** — testing
* **pytest-asyncio** — asynchronous test support
* **pytest-cov** — test coverage
* **Black** — code formatting
* **Flake8** — linting
* **MyPy** — static type checking

Run Black:

```powershell
black app tests
```

Run Flake8:

```powershell
flake8 app tests
```

Run MyPy:

```powershell
mypy app
```

## Configuration

The project uses `pyproject.toml` for package metadata and development-tool configuration.

The package uses explicit setuptools package discovery so that the Python `app` package is included while the YAML-based `configs` directory is excluded from Python package discovery.

```toml
[tool.setuptools.packages.find]
include = ["app*"]
exclude = ["configs*"]
```

## Dependencies

Core dependencies include:

* Pydantic
* Pydantic Settings
* PyYAML
* aiohttp
* Prometheus Client
* OpenTelemetry API
* OpenTelemetry SDK
* python-dotenv

Development dependencies include:

* pytest
* pytest-asyncio
* pytest-cov
* Black
* Flake8
* MyPy

## Verification Status

The repository has been verified with the following checks:

| Check                       | Status       |
| --------------------------- | ------------ |
| Python compilation          | ✅ Passed     |
| Package installation        | ✅ Passed     |
| Package import              | ✅ Passed     |
| AgentLoader import          | ✅ Passed     |
| ToolPermissions import      | ✅ Passed     |
| CodingAgent import          | ✅ Passed     |
| DataAgent import            | ✅ Passed     |
| Agent configuration loading | ✅ Passed     |
| All configured agents       | ✅ Passed     |
| Dependency validation       | ✅ Passed     |
| Unit tests                  | ✅ 2/2 Passed |

## License

This project is licensed under the MIT License.

## AgentForge

`agentforge-agents` is one component of the larger AgentForge platform and is intended to integrate with the other AgentForge repositories and services.

The repository focuses specifically on **agent definitions, execution abstractions, orchestration, configuration, registry management, and tools**.
