# FaultMaven Operational Scripts

This directory contains operational scripts for managing the FaultMaven modular monolith. These scripts have been adapted from the legacy FaultMaven-Mono repository and updated to work with the current pyproject.toml-based structure.

## Quick Reference

| Script | Purpose | Common Usage |
|--------|---------|--------------|
| `start.sh` | Start FaultMaven server | `./scripts/start.sh` |
| `stop.sh` | Stop running server | `./scripts/stop.sh` |
| `logs.sh` | Monitor server logs | `./scripts/logs.sh -f` |
| `test.sh` | Run pytest tests | `./scripts/test.sh -c` |

## Scripts Overview

### 🚀 start.sh - Server Start Script

Start the FaultMaven server with process management and health monitoring.

**Features:**
- Detects and manages existing running instances
- Port conflict detection and resolution
- Virtual environment auto-activation
- Docker environment detection
- Background or foreground execution
- Health check monitoring
- PID file management

**Basic Usage:**
```bash
# Start in foreground (Ctrl+C to stop)
./scripts/start.sh

# Start in background
./scripts/start.sh --background

# Start with custom configuration
HOST=127.0.0.1 PORT=8080 ./scripts/start.sh
```

**Environment Variables:**
- `HOST` - Server host address (default: 0.0.0.0)
- `PORT` - Server port (default: 8000)
- `LOG_FILE` - Log file path (default: /tmp/faultmaven-server.log)
- `PID_FILE` - PID file path (default: /tmp/faultmaven-server.pid)

**What Changed from FaultMaven-Mono:**
- Changed from `python -m faultmaven.main` to `uvicorn faultmaven.app:app --reload`
- Updated for pyproject.toml-based project structure
- Added support for uv package manager
- Improved health check monitoring
- Better Docker environment detection

---

### 🛑 stop.sh - Server Stop Script

Gracefully stop running FaultMaven server instances.

**Features:**
- Graceful shutdown with SIGTERM
- Force kill fallback for stuck processes
- PID file cleanup
- Port status verification
- Multiple instance detection

**Basic Usage:**
```bash
# Stop running server
./scripts/stop.sh
```

**Shutdown Process:**
1. Reads PID from PID file
2. Sends SIGTERM for graceful shutdown (10 second timeout)
3. Force kills with SIGKILL if necessary
4. Cleans up remaining processes
5. Verifies port is released

---

### 📄 logs.sh - Log Monitoring Script

Real-time log viewer with filtering and formatting options.

**Features:**
- Real-time log following
- Colorized output (ERROR in red, WARNING in yellow, etc.)
- Pattern-based filtering
- Log level filtering
- Configurable line count
- Log file clearing

**Basic Usage:**
```bash
# Show last 50 lines
./scripts/logs.sh

# Follow logs in real-time
./scripts/logs.sh -f

# Show only errors
./scripts/logs.sh -e

# Filter by pattern
./scripts/logs.sh -g "LLM"

# Show last 100 warnings and above
./scripts/logs.sh -n 100 -w

# Clear log file
./scripts/logs.sh --clear
```

**Options:**
- `-f, --follow` - Follow log file (live tail)
- `-n, --lines N` - Show last N lines (default: 50)
- `-e, --errors` - Show only ERROR and CRITICAL logs
- `-w, --warnings` - Show only WARNING, ERROR, and CRITICAL logs
- `-g, --grep PATTERN` - Filter logs by pattern
- `-l, --level LEVEL` - Filter by log level
- `-c, --color` - Force colored output
- `--clear` - Clear the log file
- `--path PATH` - Use custom log file path

**Environment Variables:**
- `LOG_FILE` - Log file path (default: /tmp/faultmaven-server.log)
- `LINES` - Default number of lines to show

**Color Coding:**
- 🔴 RED: ERROR, CRITICAL
- 🟡 YELLOW: WARNING
- 🟢 GREEN: INFO
- 🔵 CYAN: DEBUG
- 🟣 MAGENTA: Module names

---

### 🧪 test.sh - Test Runner Script

Comprehensive test runner with coverage, filtering, and reporting options.

**Features:**
- Coverage reporting with HTML output
- Test marker filtering (unit, integration, api, e2e)
- Keyword-based test selection
- Parallel test execution
- Service dependency checking
- Fail-fast mode
- Virtual environment auto-activation

**Basic Usage:**
```bash
# Run all tests
./scripts/test.sh

# Run with coverage
./scripts/test.sh -c

# Run only unit tests
./scripts/test.sh -m unit

# Run specific test by keyword
./scripts/test.sh -k test_auth

# Generate HTML coverage report
./scripts/test.sh -c --html

# Run tests in parallel (4 workers)
./scripts/test.sh -n 4

# Verbose mode with fail-fast
./scripts/test.sh -v -x

# Run integration tests with live services
./scripts/test.sh -m integration -s
```

**Options:**
- `-c, --coverage` - Enable coverage reporting
- `-v, --verbose` - Enable verbose output
- `-s, --with-services` - Run tests with live services (default: skip)
- `-m, --marker MARKER` - Run tests with specific marker
- `-k, --keyword PATTERN` - Run tests matching keyword pattern
- `-x, --fail-fast` - Stop on first failure
- `-n, --parallel N` - Run tests in parallel with N workers
- `--html` - Generate HTML coverage report

**Test Markers:**
- `unit` - Fast unit tests (no external dependencies)
- `integration` - Integration tests (may require services)
- `api` - API endpoint tests
- `e2e` - End-to-end tests

**Environment Variables:**
- `SKIP_SERVICE_CHECKS` - Set to 'false' to require live services (default: true)
- `PYTEST_ARGS` - Additional pytest arguments

**Examples:**
```bash
# Run only auth module tests with coverage
./scripts/test.sh -c tests/modules/auth/

# Run all integration tests with services running
./scripts/test.sh -m integration -s -v

# Quick unit test run
./scripts/test.sh -m unit -x

# Full test suite with HTML report
./scripts/test.sh -c --html

# Parallel execution for faster tests
./scripts/test.sh -n auto
```

**What Changed from FaultMaven-Mono:**
- Updated test paths for new module structure
- Added support for pytest markers from pyproject.toml
- Improved service dependency checking
- Added parallel test execution support
- Better error reporting and progress tracking

---

## Python Utility Scripts

The `scripts/` directory also contains Python utility scripts:

### generate_api_docs.py
Generate comprehensive API documentation from OpenAPI spec.

**Usage:**
```bash
python scripts/generate_api_docs.py
```

**Output:**
- `docs/api/openapi.json` - Machine-readable OpenAPI spec
- `docs/api/openapi.yaml` - YAML format OpenAPI spec
- `docs/api/README.md` - Human-readable API reference

### generate_openapi_spec.py
Generate OpenAPI specification from FastAPI application.

**Usage:**
```bash
python scripts/generate_openapi_spec.py
```

---

## Common Workflows

### Local Development

```bash
# 1. Start the server
./scripts/start.sh --background

# 2. Monitor logs
./scripts/logs.sh -f

# 3. Run tests (in another terminal)
./scripts/test.sh -m unit

# 4. Stop the server when done
./scripts/stop.sh
```

### Testing Workflow

```bash
# Run quick unit tests during development
./scripts/test.sh -m unit -x

# Full test suite before commit
./scripts/test.sh -c --html

# Check coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Debugging Issues

```bash
# Check if server is running
curl http://localhost:8000/health

# View recent logs
./scripts/logs.sh -n 100

# View only errors
./scripts/logs.sh -e

# Follow logs with specific pattern
./scripts/logs.sh -f -g "ERROR"

# Stop and restart server
./scripts/stop.sh && sleep 2 && ./scripts/start.sh
```

### Production-like Testing

```bash
# Start server in background
./scripts/start.sh --background

# Run integration tests with services
./scripts/test.sh -m integration -s -c

# Check logs for errors
./scripts/logs.sh -e

# Stop server
./scripts/stop.sh
```

---

## Docker Environment

All scripts detect if running inside Docker and adjust behavior accordingly:

- Skip virtual environment activation in Docker
- Use appropriate health check endpoints
- Adjust log file paths if needed

**Docker Usage:**
```bash
# Inside Docker container
docker exec -it faultmaven-container ./scripts/start.sh
docker exec -it faultmaven-container ./scripts/test.sh -m unit
docker exec -it faultmaven-container ./scripts/logs.sh -f
```

---

## Troubleshooting

### Port Already in Use

```bash
# Check what's using the port
lsof -i :8000

# Force stop and cleanup
./scripts/stop.sh

# Wait a moment
sleep 2

# Start again
./scripts/start.sh
```

### Server Won't Start

```bash
# Check logs for errors
./scripts/logs.sh -e

# Common issues:
# 1. Redis not running
# 2. Database not accessible
# 3. Missing environment variables

# Check .env file exists
ls -la .env

# If not, copy from example
cp .env.example .env
```

### Tests Failing

```bash
# Run tests with verbose output
./scripts/test.sh -v -x

# Skip service checks for unit tests
SKIP_SERVICE_CHECKS=true ./scripts/test.sh -m unit

# Run specific failing test
./scripts/test.sh -k test_name -v
```

### Logs Not Showing

```bash
# Check log file exists
ls -la /tmp/faultmaven-server.log

# Check if server is running
./scripts/stop.sh  # Will show status

# Specify custom log path
LOG_FILE=/custom/path/server.log ./scripts/logs.sh
```

---

## Configuration Files

Scripts respect these configuration sources (in order of precedence):

1. **Environment variables** - Directly exported or passed inline
2. **.env file** - Project root environment configuration
3. **.env.example** - Default values and documentation
4. **pyproject.toml** - Test configuration and markers
5. **Script defaults** - Built-in fallback values

---

## Migration Notes from FaultMaven-Mono

These scripts have been adapted from the original FaultMaven-Mono repository:

### Key Changes:

1. **Server Command:**
   - Old: `python -m faultmaven.main`
   - New: `uvicorn faultmaven.app:app --reload`

2. **Project Structure:**
   - Old: Flat structure with `requirements.txt`
   - New: pyproject.toml with `src/faultmaven/` layout

3. **Process Detection:**
   - Old: Search for `faultmaven.main`
   - New: Search for `uvicorn.*faultmaven.app:app`

4. **Test Configuration:**
   - Old: pytest.ini or setup.cfg
   - New: pyproject.toml `[tool.pytest.ini_options]`

5. **Package Management:**
   - Old: pip + requirements.txt
   - New: pip + pyproject.toml (with optional uv support)

### Original Scripts Adapted:

- ✅ `run_faultmaven.sh` → `start.sh` (enhanced with background mode)
- ✅ `test_integration_logging.sh` → `test.sh` (generalized for all tests)
- ✅ Added `stop.sh` (new, based on FaultMaven-Mono process management)
- ✅ Added `logs.sh` (new, enhanced log monitoring)

### Scripts Not Yet Migrated:

Additional FaultMaven-Mono scripts available for future migration:
- `local_llm_service.sh` - Local LLM Docker service management
- `create_builtin_accounts.py` - User account creation
- `verify_vector_storage.py` - ChromaDB verification
- `test_rbac.py` - RBAC testing
- `cleanup_corrupt_cases.py` - Database cleanup utilities

These can be adapted if needed for the current monolith structure.

---

## Best Practices

1. **Always use scripts for server management** - Don't run uvicorn directly
2. **Monitor logs during development** - Use `logs.sh -f` in a separate terminal
3. **Run tests before commits** - Use `test.sh -c` to ensure coverage
4. **Use markers for targeted testing** - Faster iteration with `-m unit`
5. **Check health endpoint** - `curl http://localhost:8000/health`
6. **Clean shutdown** - Always use `stop.sh` instead of kill commands
7. **Review coverage reports** - Open `htmlcov/index.html` after `test.sh --html`

---

## Contributing

When adding new scripts:

1. Make them executable: `chmod +x scripts/new_script.sh`
2. Add usage documentation in script header
3. Update this README with new script details
4. Follow existing error handling patterns
5. Support both Docker and local environments
6. Add color-coded output for better UX

---

## Support

For issues with these scripts:

1. Check script help: `./scripts/script_name.sh --help`
2. Review logs: `./scripts/logs.sh -e`
3. Verify environment: Check `.env` file exists and is configured
4. Check services: Ensure Redis, database are running if needed
5. Review pyproject.toml: Ensure test configuration is correct

---

**Last Updated:** December 27, 2024
**Adapted From:** FaultMaven-Mono operational scripts
**Current Version:** FaultMaven 2.0.0 Modular Monolith
