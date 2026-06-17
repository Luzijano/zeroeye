# Pre-Commit Hook

## Overview

The pre-commit hook automates diagnostic generation before every commit, ensuring that build diagnostics are always up-to-date without manual intervention.

## Installation

```bash
make install-hooks
```

This symlinks `tools/pre-commit` into `.git/hooks/pre-commit` and makes it executable.

## How It Works

1. **Runs `python3 build.py`** before each commit
2. **Stages diagnostic artifacts** (`diagnostic/build-*.logd` and `diagnostic/build-*.json`)
3. **Aborts the commit** if the build fails, with a clear error message
4. **Skips rebuild** if diagnostics haven't changed since the last commit (uses file hashes)
5. **Displays an elapsed-time counter** while the build runs

## Cache Mechanism

The hook stores SHA-256 hashes of diagnostic files in `.git/pre-commit-hashes`. On subsequent commits, it compares current file hashes against stored ones. If they match, the build is skipped entirely.

To force a rebuild:

```bash
rm .git/pre-commit-hashes
```

## Manual Usage

You can also run the hook manually:

```bash
python3 tools/pre-commit
```

## Troubleshooting

**Hook not running?** Ensure it's installed and executable:

```bash
ls -la .git/hooks/pre-commit
chmod +x tools/pre-commit
```

**Build fails?** The hook will print the full build output. Fix the errors and retry.

**Want to bypass?** Use `git commit --no-verify` to skip the hook.
