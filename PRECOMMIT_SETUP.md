# Pre-commit Setup - 2025-07-05

✅ **Pre-commit hooks successfully configured!**

## What's Installed

### Code Quality Hooks
- **Ruff**: Fast Python linting and auto-fixing
- **Ruff Format**: Code formatting (primary)
- **Black**: Backup code formatting (line-length=100)

### File Quality Hooks
- **Trailing whitespace**: Removes trailing spaces
- **End of file fixer**: Ensures files end with newline
- **YAML/TOML/JSON check**: Validates config files
- **Merge conflict check**: Prevents committing conflict markers
- **Large file check**: Blocks files > 1MB
- **Line ending fix**: Enforces LF endings

### Python-specific Hooks
- **Docstring check**: Ensures docstrings come first
- **Debug statements**: Prevents committing debug code
- **Test naming**: Enforces `*_test.py` pattern

## Configuration

### Hooks run on:
- **Pre-commit**: All quality checks
- **Pre-push**: Additional validation

### Global Setup
Following PROJECT_RULES.md section 6.1:
```bash
✅ uv add --dev pre-commit
✅ uv run pre-commit install
✅ uv run pre-commit init-templatedir ~/.git-template
✅ git config --global init.templateDir ~/.git-template
```

## Usage

```bash
# Manual run on all files
uv run pre-commit run --all-files

# Manual run on specific files
uv run pre-commit run --files src/gateway/websocket.py

# Skip hooks for emergency commits
git commit --no-verify -m "Emergency fix"
```

The hooks will automatically run on every git commit and push!
