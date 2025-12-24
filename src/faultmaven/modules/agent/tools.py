"""
Agent tools registry.

Defines available tools (functions) that the AI agent can call.
Each tool has a Python implementation and an OpenAI function schema.
"""

import json
import subprocess
from typing import Any, Callable
from datetime import datetime


# --- Tool Implementations ---

async def check_system_health(service_name: str) -> dict[str, Any]:
    """
    Check the health of a system service.

    Args:
        service_name: Name of the service to check (e.g., 'database', 'redis', 'api')

    Returns:
        Health status information
    """
    # Simple mock implementation - in production, this would check actual services
    health_map = {
        "database": {"status": "healthy", "latency_ms": 12, "connections": 5},
        "redis": {"status": "healthy", "latency_ms": 3, "memory_used_mb": 128},
        "api": {"status": "healthy", "uptime_seconds": 86400, "requests_per_second": 45},
        "celery": {"status": "healthy", "workers": 4, "pending_tasks": 2},
    }

    result = health_map.get(service_name.lower(), {
        "status": "unknown",
        "error": f"Service '{service_name}' not found"
    })

    return {
        "service": service_name,
        "timestamp": datetime.utcnow().isoformat(),
        **result
    }


async def query_logs(search_term: str, limit: int = 10) -> dict[str, Any]:
    """
    Search application logs for a specific term.

    Args:
        search_term: Term to search for in logs
        limit: Maximum number of log entries to return

    Returns:
        Matching log entries
    """
    # Mock implementation - in production, this would query actual logs
    mock_logs = [
        {
            "timestamp": "2025-12-21T00:15:23Z",
            "level": "ERROR",
            "message": f"Database connection timeout while executing query: {search_term}",
            "service": "api-gateway"
        },
        {
            "timestamp": "2025-12-21T00:14:12Z",
            "level": "WARN",
            "message": f"Slow query detected: {search_term} took 3.2s",
            "service": "database"
        },
        {
            "timestamp": "2025-12-21T00:12:45Z",
            "level": "INFO",
            "message": f"Successfully processed request containing: {search_term}",
            "service": "worker"
        },
    ]

    return {
        "search_term": search_term,
        "total_results": len(mock_logs),
        "limit": limit,
        "logs": mock_logs[:limit]
    }


async def get_case_status(case_id: str) -> dict[str, Any]:
    """
    Get the current status and metadata of a case.

    Args:
        case_id: ID of the case to check

    Returns:
        Case status information
    """
    # This would integrate with the CaseService in production
    return {
        "case_id": case_id,
        "status": "active",
        "priority": "high",
        "message_count": 15,
        "evidence_count": 3,
        "created_at": "2025-12-20T10:30:00Z",
        "last_updated": "2025-12-21T00:05:00Z"
    }


async def search_knowledge_base(query: str, limit: int = 5) -> dict[str, Any]:
    """
    Search the knowledge base for relevant documents.

    Args:
        query: Search query
        limit: Maximum number of results

    Returns:
        Search results with relevance scores
    """
    # This would integrate with the KnowledgeService in production
    return {
        "query": query,
        "results": [
            {
                "title": "Database Connection Troubleshooting",
                "relevance": 0.92,
                "snippet": "Common database connection issues and how to resolve them..."
            },
            {
                "title": "API Rate Limiting Guide",
                "relevance": 0.78,
                "snippet": "Understanding and configuring API rate limits..."
            }
        ],
        "total_found": 2
    }


async def execute_diagnostic_command(command: str) -> dict[str, Any]:
    """
    Execute a safe diagnostic command (VERY restricted for security).

    Args:
        command: Diagnostic command to execute (must be in allowlist)

    Returns:
        Command output
    """
    # SECURITY: Only allow specific safe commands
    allowed_commands = {
        "disk_usage": "df -h",
        "memory_usage": "free -h",
        "process_count": "ps aux | wc -l",
        "uptime": "uptime",
    }

    if command not in allowed_commands:
        return {
            "success": False,
            "error": f"Command '{command}' not allowed. Available: {list(allowed_commands.keys())}"
        }

    try:
        result = subprocess.run(
            allowed_commands[command],
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )

        return {
            "success": True,
            "command": command,
            "output": result.stdout,
            "exit_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Command timed out after 5 seconds"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# --- Tool Registry ---

class ToolRegistry:
    """
    Registry of available tools for the AI agent.

    Maps tool names to their implementations and OpenAI function schemas.
    """

    def __init__(self):
        """Initialize the tool registry."""
        self.tools: dict[str, Callable] = {
            "check_system_health": check_system_health,
            "query_logs": query_logs,
            "get_case_status": get_case_status,
            "search_knowledge_base": search_knowledge_base,
            "execute_diagnostic_command": execute_diagnostic_command,
        }

    def get_tool(self, name: str) -> Callable | None:
        """
        Get a tool by name.

        Args:
            name: Tool name

        Returns:
            Tool function or None if not found
        """
        return self.tools.get(name)

    def get_openai_tools(self) -> list[dict[str, Any]]:
        """
        Get OpenAI function calling schemas for all tools.

        Returns:
            List of tool schemas in OpenAI format
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "check_system_health",
                    "description": "Check the health status of a system service (database, redis, api, celery)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "service_name": {
                                "type": "string",
                                "description": "Name of the service to check (e.g., 'database', 'redis', 'api')",
                                "enum": ["database", "redis", "api", "celery"]
                            }
                        },
                        "required": ["service_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "query_logs",
                    "description": "Search application logs for specific terms or patterns",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "search_term": {
                                "type": "string",
                                "description": "Term or pattern to search for in logs"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of log entries to return",
                                "default": 10
                            }
                        },
                        "required": ["search_term"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_case_status",
                    "description": "Get the current status and metadata of a debugging case",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "case_id": {
                                "type": "string",
                                "description": "ID of the case to check"
                            }
                        },
                        "required": ["case_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_knowledge_base",
                    "description": "Search the knowledge base for relevant documentation and guides",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_diagnostic_command",
                    "description": "Execute a safe diagnostic command to check system resources",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "Diagnostic command to execute",
                                "enum": ["disk_usage", "memory_usage", "process_count", "uptime"]
                            }
                        },
                        "required": ["command"]
                    }
                }
            }
        ]

    async def execute_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """
        Execute a tool with the given arguments.

        Args:
            name: Tool name
            arguments: Tool arguments as a dictionary

        Returns:
            Tool execution result

        Raises:
            ValueError: If tool not found
        """
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found")

        return await tool(**arguments)


# Global tool registry instance
tool_registry = ToolRegistry()
