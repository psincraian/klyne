# SDK Publishing Guide

## Automatic Publishing

The Klyne SDK is automatically published to PyPI whenever changes are pushed to the `sdk/` directory on the main branch.

### How it works

1. **Trigger**: Any commit to the `main` branch that changes files in `sdk/` triggers the publish workflow
2. **Version**: Auto-generated based on the latest stable release tag (see Version Strategy below)
3. **Publishing**: Uses PyPI trusted publishing (no API tokens needed)
4. **Testing**: Automatically tests installation across Python 3.8-3.12

### Publishing a Stable Release

To publish a stable version (e.g., `0.1.95`):

1. **Create and push a git tag**:
   ```bash
   git tag sdk-v0.1.95
   git push origin sdk-v0.1.95
   ```

2. **Trigger manual workflow**:
   - Go to GitHub Actions → "Publish SDK to PyPI"
   - Click "Run workflow"
   - Enter the version: `0.1.95`

3. **Future auto-versions**: All subsequent auto-published versions will be based on this tag (e.g., `0.1.96a1`, `0.1.96a2`, etc.)

### Manual Publishing

You can also trigger a manual publish with any version:

1. Go to GitHub Actions → "Publish SDK to PyPI"
2. Click "Run workflow"
3. Enter the desired version (e.g., "1.0.0")

**Note**: For stable releases, remember to create a git tag so future auto-versions are calculated correctly!

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

The SDK uses **semantic versioning** with automatic alpha version generation:

- **Stable Releases** (manual): `0.1.95`, `1.0.0`, `1.1.0`
  - Manually triggered via GitHub Actions workflow
  - Should be tagged with `sdk-v{version}` format

- **Alpha Releases** (automatic): `0.1.96a1`, `0.1.96a2`, `0.1.96a3`
  - Auto-generated on every commit to `sdk/`
  - Format: `{next_patch}a{commits_since_tag}`
  - Based on latest stable release tag
  - Ensures versions are always incrementing correctly

**Example flow:**
1. You publish stable version `0.1.95` and tag it as `sdk-v0.1.95`
2. Next commit → auto-publishes as `0.1.96a1`
3. Another commit → auto-publishes as `0.1.96a2`
4. You publish stable version `0.1.96` and tag it as `sdk-v0.1.96`
5. Next commit → auto-publishes as `0.1.97a1`

This ensures every SDK change gets published while maintaining proper semantic versioning.