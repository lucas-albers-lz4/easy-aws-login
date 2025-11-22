# Building and Installing easy-aws-login

This document covers the steps to build, install, and develop `easy-aws-login` using `uv`, a fast Python package installer and resolver.

## Prerequisites

- Python 3.10 or later
- `uv` package manager

Install `uv`:

```bash
pip install uv
```

Or using the official installer:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Installation

### Install for Development

```bash
# Clone the repository
git clone <repository-url>
cd easy-aws-login

# Create virtual environment and install all dependencies
uv sync

# Install with dev dependencies (linting, formatting, etc.)
uv sync --extra dev
```

This will:
- Create a virtual environment (`.venv/`)
- Install all project dependencies
- Install the package in editable mode
- Generate/update `uv.lock` file

### Install from Source

```bash
# Build the package (creates both wheel and source distribution)
uv build

# Install from built wheel
uv pip install dist/easy_aws_login-*.whl
```

## Development Setup

### Install Development Dependencies

Development dependencies include linting and formatting tools:

```bash
uv sync --extra dev
```

This installs:
- **ruff**: Fast Python linter and formatter
- **isort**: Import statement sorter
- **bandit**: Security linter
- **pre-commit**: Git hooks framework

### Running Development Tools

```bash
# Run ruff linter
ruff check .

# Run ruff formatter
ruff format .

# Run isort
isort .

# Run bandit security checks
bandit -r easy_aws_login/

# Install pre-commit hooks
pre-commit install
```

## Building the Package

### Quick Build (Recommended)

Use the `build.sh` script for a complete local build:

```bash
./build.sh
```

This script automates:
1. Locking dependencies (`uv lock`)
2. Syncing version from `buildspec.yml`
3. Syncing dependencies (`uv sync`)
4. Building the package (`uv build`)
5. Installing the built package locally

### Manual Build

**Important:** The version is managed in `buildspec.yml` as the single source of truth. Before building locally, sync the version:

```bash
# Option 1: Set CODE_VERSION and update __version__.py
CODE_VERSION=$(grep "CODE_VERSION:" buildspec.yml | sed 's/.*CODE_VERSION: *//') && \
  echo "__version__ = \"${CODE_VERSION}\"" > easy_aws_login/__version__.py

# Option 2: Manually edit easy_aws_login/__version__.py (it's just one line)
# Edit: __version__ = "0.4.3"

# Then build
uv build

# Output will be in dist/ directory:
# - easy_aws_login-<version>-py3-none-any.whl
# - easy_aws_login-<version>.tar.gz
```

## Project Structure

```
easy-aws-login/
├── pyproject.toml      # Project configuration and dependencies
├── uv.lock             # Locked dependency versions (managed by uv)
├── easy_aws_login/     # Main package directory
│   ├── __init__.py
│   ├── __version__.py  # Version source of truth
│   └── index.py        # Main entry point
├── BUILD.md            # This file
└── README.md           # Project documentation
```

## Version Management

**Single Source of Truth:** The project version is defined in `buildspec.yml` under `env.variables.CODE_VERSION`.

The version flow:
1. **Source:** `buildspec.yml` → `CODE_VERSION: 0.4.2`
2. **CI/CD:** CodeBuild sets `CODE_VERSION` env var, `release.sh` updates `__version__.py` automatically
3. **Local:** Sync version manually (see Building section) or edit `__version__.py` directly
4. **Build:** `pyproject.toml` reads version from `__version__.py` using setuptools' `attr:` directive

**For CI/CD builds:** Automatic - CodeBuild sets `CODE_VERSION` from `buildspec.yml`, `release.sh` syncs it.

**For local builds:** Either sync from `buildspec.yml` using the one-liner command, or manually edit `easy_aws_login/__version__.py` (it's just one line).

## Common Commands

### Check Version

```bash
easy-aws-login --version
```

### Run the Application

```bash
# Use default profile
easy-aws-login

# Use specific profile
easy-aws-login my-profile

# Use profile with custom duration (in seconds)
easy-aws-login my-profile 7200

# Enable debug mode
easy-aws-login my-profile --debug
```

### Update Dependencies

```bash
# Update lock file with latest compatible versions
uv lock

# Sync dependencies (install/update based on lock file)
uv sync

# Upgrade all dependencies to latest versions
uv lock --upgrade
uv sync
```

### Add New Dependencies

```bash
# Add a production dependency
uv add <package-name>

# Add a development dependency
uv add --dev <package-name>

# Add with version constraint
uv add "requests>=2.31.0"
```

## CI/CD Build Process

The project uses AWS CodeBuild for automated builds. The build process:

1. Installs `build` and `twine` tools
2. Copies necessary files (`pyproject.toml`, `LICENCE.txt`, `README.md`, etc.) to a temporary directory
3. Runs `python -m build` to create distributions
4. Uploads to PyPI using `twine`

See `buildspec.yml` and `release.sh` for details.

**Note:** The CI/CD pipeline uses `python -m build` (which works with `pyproject.toml`). For local development, you can use `uv build` which is equivalent.

## Troubleshooting

### Import Errors

If you encounter import errors after installation:

```bash
# Verify installation
uv pip show easy-aws-login

# Reinstall in editable mode
uv pip install -e . --force-reinstall
```

### Version Conflicts

If you have version conflicts:

```bash
# Update lock file and sync dependencies
uv lock --upgrade
uv sync
```

### Build Errors

If build fails:

```bash
# Clean build artifacts
rm -rf build/ dist/ *.egg-info/

# Rebuild using uv
uv build
```

### Virtual Environment Issues

```bash
# Remove existing virtual environment
rm -rf .venv/

# Recreate and sync dependencies
uv sync
```

## Additional Resources

- [uv Documentation](https://github.com/astral-sh/uv)
- [uv GitHub Repository](https://github.com/astral-sh/uv)
- [Python Packaging User Guide](https://packaging.python.org/)
- [PEP 621 - Project Metadata](https://peps.python.org/pep-0621/)
