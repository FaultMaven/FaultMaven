#!/usr/bin/env python3
"""
FaultMaven Development Helper

A CLI tool for common FaultMaven development tasks.

Usage:
    python fm_dev.py <command> [options]

Commands:
    health          Check all service health
    logs <service>  View service logs
    rebuild <svc>   Rebuild a specific service
    shell <service> Open shell in service container
    db-shell        Open SQLite shell
    redis-cli       Open Redis CLI
    test <service>  Run tests for a service
    lint <service>  Run linting for a service
    env             Show environment configuration
    services        List all services and ports

Examples:
    python fm_dev.py health
    python fm_dev.py logs agent-service
    python fm_dev.py rebuild knowledge-service
    python fm_dev.py test auth-service
"""

import argparse
import subprocess
import sys
import json
import os
from typing import Optional

# Service configuration
SERVICES = {
    "api-gateway": {"port": 8090, "repo": "fm-api-gateway"},
    "auth-service": {"port": 8001, "repo": "fm-auth-service"},
    "session-service": {"port": 8002, "repo": "fm-session-service"},
    "case-service": {"port": 8003, "repo": "fm-case-service"},
    "knowledge-service": {"port": 8004, "repo": "fm-knowledge-service"},
    "evidence-service": {"port": 8005, "repo": "fm-evidence-service"},
    "agent-service": {"port": 8006, "repo": "fm-agent-service"},
    "job-worker": {"port": None, "repo": "fm-job-worker"},
}

# Docker compose file location (adjust as needed)
COMPOSE_FILE = os.environ.get("FM_COMPOSE_FILE", "docker-compose.yml")
DEPLOY_DIR = os.environ.get("FM_DEPLOY_DIR", "../faultmaven-deploy")


def run_cmd(cmd: list, capture: bool = False, check: bool = True) -> Optional[str]:
    """Run a shell command."""
    try:
        if capture:
            result = subprocess.run(cmd, capture_output=True, text=True, check=check)
            return result.stdout
        else:
            subprocess.run(cmd, check=check)
            return None
    except subprocess.CalledProcessError as e:
        print(f"Error: Command failed with exit code {e.returncode}")
        if capture:
            print(f"stderr: {e.stderr}")
        return None
    except FileNotFoundError:
        print(f"Error: Command not found: {cmd[0]}")
        return None


def docker_compose(*args):
    """Run docker-compose command."""
    compose_path = os.path.join(DEPLOY_DIR, COMPOSE_FILE)
    if os.path.exists(compose_path):
        cmd = ["docker-compose", "-f", compose_path] + list(args)
    else:
        cmd = ["docker-compose"] + list(args)
    run_cmd(cmd)


def cmd_health(args):
    """Check health of all services."""
    import urllib.request
    import urllib.error

    base_url = args.url or "http://localhost:8000"

    print("=" * 50)
    print("  FaultMaven Service Health Check")
    print("=" * 50)
    print(f"Base URL: {base_url}\n")

    endpoints = {
        "API Gateway": "/health",
        "Auth Service": "/v1/auth/health",
        "Case Service": "/v1/cases/health",
        "Knowledge Service": "/v1/knowledge/health",
        "Agent Service": "/v1/agent/health",
    }

    healthy = 0
    for name, endpoint in endpoints.items():
        try:
            url = f"{base_url}{endpoint}"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    print(f"  \033[92m✓\033[0m {name}: healthy")
                    healthy += 1
                else:
                    print(f"  \033[93m!\033[0m {name}: HTTP {resp.status}")
        except urllib.error.URLError:
            print(f"  \033[91m✗\033[0m {name}: unreachable")
        except Exception as e:
            print(f"  \033[91m✗\033[0m {name}: {str(e)}")

    print(f"\nSummary: {healthy}/{len(endpoints)} services healthy")


def cmd_logs(args):
    """View logs for a service."""
    service = args.service
    if service not in SERVICES and service != "all":
        print(f"Unknown service: {service}")
        print(f"Available: {', '.join(SERVICES.keys())}")
        return

    tail = args.tail or "100"
    if service == "all":
        docker_compose("logs", "-f", "--tail", tail)
    else:
        docker_compose("logs", "-f", "--tail", tail, service)


def cmd_rebuild(args):
    """Rebuild and restart a service."""
    service = args.service
    if service not in SERVICES:
        print(f"Unknown service: {service}")
        print(f"Available: {', '.join(SERVICES.keys())}")
        return

    print(f"Rebuilding {service}...")
    docker_compose("up", "-d", "--build", service)
    print(f"\n{service} rebuilt and restarted.")


def cmd_shell(args):
    """Open shell in a service container."""
    service = args.service
    if service not in SERVICES:
        print(f"Unknown service: {service}")
        return

    docker_compose("exec", service, "/bin/sh")


def cmd_db_shell(args):
    """Open SQLite shell for a service."""
    service = args.service or "case-service"
    db_path = f"/app/data/{service}.db"

    print(f"Opening SQLite shell for {service}...")
    docker_compose("exec", service, "sqlite3", db_path)


def cmd_redis_cli(args):
    """Open Redis CLI."""
    print("Opening Redis CLI...")
    docker_compose("exec", "redis", "redis-cli")


def cmd_test(args):
    """Run tests for a service."""
    service = args.service
    if service not in SERVICES:
        print(f"Unknown service: {service}")
        return

    print(f"Running tests for {service}...")
    docker_compose("exec", service, "python", "-m", "pytest", "tests/", "-v")


def cmd_lint(args):
    """Run linting for a service."""
    service = args.service
    if service not in SERVICES:
        print(f"Unknown service: {service}")
        return

    print(f"Running linter for {service}...")
    docker_compose("exec", service, "python", "-m", "flake8", "src/")


def cmd_env(args):
    """Show environment configuration."""
    print("=" * 50)
    print("  FaultMaven Environment Configuration")
    print("=" * 50)

    env_vars = [
        "FM_DEPLOY_DIR",
        "FM_COMPOSE_FILE",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "FIREWORKS_API_KEY",
        "FM_JWT_SECRET",
        "FM_DATABASE_URL",
        "FM_REDIS_URL",
        "FM_CHROMA_HOST",
    ]

    for var in env_vars:
        value = os.environ.get(var, "")
        if value:
            # Mask sensitive values
            if "KEY" in var or "SECRET" in var:
                display = value[:8] + "..." if len(value) > 8 else "***"
            else:
                display = value
            print(f"  {var}: {display}")
        else:
            print(f"  {var}: (not set)")


def cmd_services(args):
    """List all services and their ports."""
    print("=" * 50)
    print("  FaultMaven Services")
    print("=" * 50)
    print(f"{'Service':<20} {'Port':<8} {'Repository'}")
    print("-" * 50)

    for name, info in SERVICES.items():
        port = str(info["port"]) if info["port"] else "N/A"
        print(f"{name:<20} {port:<8} {info['repo']}")

    print("\nDirect access URLs (local development):")
    print("-" * 50)
    for name, info in SERVICES.items():
        if info["port"]:
            print(f"  {name}: http://localhost:{info['port']}")


def cmd_status(args):
    """Show status of all containers."""
    print("Container Status:")
    print("-" * 50)
    docker_compose("ps")


def cmd_up(args):
    """Start all services."""
    print("Starting FaultMaven services...")
    if args.build:
        docker_compose("up", "-d", "--build")
    else:
        docker_compose("up", "-d")
    print("\nServices started. Run 'fm_dev.py health' to verify.")


def cmd_down(args):
    """Stop all services."""
    print("Stopping FaultMaven services...")
    if args.volumes:
        docker_compose("down", "-v")
    else:
        docker_compose("down")
    print("Services stopped.")


def main():
    parser = argparse.ArgumentParser(
        description="FaultMaven Development Helper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # health command
    health_parser = subparsers.add_parser("health", help="Check service health")
    health_parser.add_argument("--url", help="Base URL (default: http://localhost:8000)")

    # logs command
    logs_parser = subparsers.add_parser("logs", help="View service logs")
    logs_parser.add_argument("service", help="Service name or 'all'")
    logs_parser.add_argument("--tail", help="Number of lines (default: 100)")

    # rebuild command
    rebuild_parser = subparsers.add_parser("rebuild", help="Rebuild a service")
    rebuild_parser.add_argument("service", help="Service name")

    # shell command
    shell_parser = subparsers.add_parser("shell", help="Open shell in container")
    shell_parser.add_argument("service", help="Service name")

    # db-shell command
    db_parser = subparsers.add_parser("db-shell", help="Open SQLite shell")
    db_parser.add_argument("--service", help="Service name (default: case-service)")

    # redis-cli command
    subparsers.add_parser("redis-cli", help="Open Redis CLI")

    # test command
    test_parser = subparsers.add_parser("test", help="Run tests")
    test_parser.add_argument("service", help="Service name")

    # lint command
    lint_parser = subparsers.add_parser("lint", help="Run linting")
    lint_parser.add_argument("service", help="Service name")

    # env command
    subparsers.add_parser("env", help="Show environment config")

    # services command
    subparsers.add_parser("services", help="List all services")

    # status command
    subparsers.add_parser("status", help="Show container status")

    # up command
    up_parser = subparsers.add_parser("up", help="Start all services")
    up_parser.add_argument("--build", action="store_true", help="Rebuild images")

    # down command
    down_parser = subparsers.add_parser("down", help="Stop all services")
    down_parser.add_argument("-v", "--volumes", action="store_true", help="Remove volumes")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    commands = {
        "health": cmd_health,
        "logs": cmd_logs,
        "rebuild": cmd_rebuild,
        "shell": cmd_shell,
        "db-shell": cmd_db_shell,
        "redis-cli": cmd_redis_cli,
        "test": cmd_test,
        "lint": cmd_lint,
        "env": cmd_env,
        "services": cmd_services,
        "status": cmd_status,
        "up": cmd_up,
        "down": cmd_down,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        print(f"Unknown command: {args.command}")
        parser.print_help()


if __name__ == "__main__":
    main()
