#!/usr/bin/env sh
set -e

# Update version from CODE_VERSION environment variable (set by CodeBuild from buildspec.yml)
# Single source of truth: buildspec.yml -> CODE_VERSION env var -> __version__.py
if [ -z "$CODE_VERSION" ]; then
    echo "Error: CODE_VERSION environment variable not set. Ensure buildspec.yml contains CODE_VERSION."
    exit 1
fi

echo "__version__ = \"${CODE_VERSION}\"" > easy_aws_login/__version__.py

python -m build
cp -r dist /custom

twine upload --skip-existing --username ${TWINE_USERNAME} --password ${TWINE_PASSWORD} dist/*

# Note: post-release-data.py was removed - GitHub release creation disabled
# If needed, recreate post-release-data.py or use GitHub CLI/API directly
# curl --header "Content-Type: application/json" \
#   -u jeshan:${GITHUB_TOKEN} \
#   --request POST \
#   --data @data.json \
#   https://api.github.com/repos/jeshan/easy-aws-login/releases
