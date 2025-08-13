# SDK Publishing Guide

## Automatic Publishing

The Klyne SDK is automatically published to PyPI whenever changes are pushed to the `sdk/` directory on the main branch.

### How it works

1. **Trigger**: Any commit to the `main` branch that changes files in `sdk/` triggers the publish workflow
2. **Version**: Auto-generated as `{major}.{minor}.{commit_count}` where commit_count is the number of commits affecting the SDK
3. **Publishing**: Uses PyPI trusted publishing (no API tokens needed)
4. **Testing**: Automatically tests installation across Python 3.7-3.12

### Manual Publishing

You can also trigger a manual publish with a specific version:

1. Go to GitHub Actions → "Publish SDK to PyPI"
2. Click "Run workflow"
3. Enter the desired version (e.g., "1.0.0")

### Setup Requirements

To use this publishing pipeline, you need to:

1. **Configure PyPI Trusted Publishing**:
   - Go to [PyPI](https://pypi.org) → Your account → Publishing
   - Add a new trusted publisher with:
     - Owner: `psincraian`
     - Repository: `klyne` 
     - Workflow: `publish-sdk.yml`

2. **Repository Secrets**: None needed! Trusted publishing handles authentication.

### Version Strategy

- **Development**: Automatic versioning based on commit count (e.g., 0.1.15, 0.1.16)
- **Releases**: Manual versioning for major releases (e.g., 1.0.0, 1.1.0)

This ensures every SDK change gets published while allowing controlled major releases.