#!/usr/bin/env sh
set -e

# Local build script for easy-aws-login
# This script automates the local build process:
# 1. Updates dependency lock file
# 2. Syncs version from buildspec.yml
# 3. Syncs dependencies
# 4. Builds the package
# 5. Installs it locally

echo "🔒 Locking dependencies..."
uv lock

echo "📦 Syncing version from buildspec.yml..."
CODE_VERSION=$(grep "CODE_VERSION:" buildspec.yml | sed 's/.*CODE_VERSION: *//' | tr -d ' ')
if [ -z "$CODE_VERSION" ]; then
    echo "Error: Could not find CODE_VERSION in buildspec.yml"
    exit 1
fi
echo "__version__ = \"${CODE_VERSION}\"" > easy_aws_login/__version__.py
echo "   Version set to: ${CODE_VERSION}"

echo "📥 Syncing dependencies..."
uv sync

echo "🔨 Building package..."
uv build

echo "📦 Installing package locally..."
uv pip install dist/easy_aws_login-${CODE_VERSION}-py3-none-any.whl --force-reinstall

echo "✅ Build complete! Package installed locally."
echo "   Version: ${CODE_VERSION}"
echo "   Run 'easy-aws-login --version' to verify"

