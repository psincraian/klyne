#!/bin/bash

# Release script for Klyne SDK
# Usage: ./scripts/release.sh <version>
# Example: ./scripts/release.sh 1.0.0

set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 <version>"
    echo "Example: $0 1.0.0"
    exit 1
fi

VERSION=$1

# Validate version format (basic check)
if ! [[ $VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+([a-zA-Z0-9\-\.]*)?$ ]]; then
    echo "Error: Invalid version format. Use semantic versioning (e.g., 1.0.0)"
    exit 1
fi

echo "Preparing release for version $VERSION"

# Check if we're on main branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "Error: Must be on main branch to create a release"
    exit 1
fi

# Check if working directory is clean
if ! git diff-index --quiet HEAD --; then
    echo "Error: Working directory is not clean. Please commit or stash changes."
    exit 1
fi

# Update version in pyproject.toml
echo "Updating version in sdk/pyproject.toml..."
sed -i.bak "s/version = \".*\"/version = \"$VERSION\"/" sdk/pyproject.toml
rm sdk/pyproject.toml.bak

# Create a commit for the version bump
git add sdk/pyproject.toml
git commit -m "chore: bump SDK version to $VERSION"

# Create and push tag
TAG="v$VERSION"
echo "Creating tag $TAG..."
git tag -a "$TAG" -m "Release $VERSION"

echo "Pushing changes and tag..."
git push origin main
git push origin "$TAG"

echo "✅ Release $VERSION has been created!"
echo "🚀 GitHub Actions will automatically publish to PyPI"
echo "📦 Monitor the workflow at: https://github.com/psincraian/klyne/actions"