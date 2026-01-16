# Poetry Setup Guide

This project now uses **Poetry** for Python dependency management instead of `requirements.txt`.

## Why Poetry?

✅ **Better dependency resolution** - No more version conflicts  
✅ **Reproducible builds** - Lock file ensures same versions everywhere  
✅ **Easier dependency management** - Simple commands to add/remove packages  
✅ **Modern Python standard** - Industry best practice for 2024+  

---

## Initial Setup (One-Time)

### 1. Install Poetry

**macOS/Linux:**
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

**Windows (PowerShell):**
```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
```

**Verify installation:**
```bash
poetry --version
```

### 2. Generate Lock File

The `poetry.lock` file ensures everyone uses the same dependency versions:

```bash
# In project root directory
poetry lock
```

This will:
- Resolve all dependencies
- Generate `poetry.lock` file
- Take 1-2 minutes to complete

### 3. Install Dependencies

```bash
poetry install
```

This installs all dependencies in a virtual environment.

---

## Docker Build (Automatic)

The Docker build now uses Poetry automatically:

```bash
# Just build normally - Poetry is handled inside Dockerfile
docker-compose build

# Or start everything
docker-compose up -d
```

No manual steps needed! The Dockerfile:
1. Installs Poetry
2. Copies `pyproject.toml` and `poetry.lock`
3. Installs all dependencies
4. Builds the image

---

## Daily Workflow

### Add a New Dependency

```bash
# Production dependency
poetry add fastapi-users

# Development dependency
poetry add --group dev pytest-mock

# Specific version
poetry add "sqlalchemy>=2.0,<3.0"
```

### Remove a Dependency

```bash
poetry remove package-name
```

### Update Dependencies

```bash
# Update all to latest compatible versions
poetry update

# Update specific package
poetry update fastapi

# Show outdated packages
poetry show --outdated
```

### Run Commands

```bash
# Activate virtual environment
poetry shell

# Run command without activating
poetry run python script.py
poetry run uvicorn sentinel.saas.server:app --reload
poetry run pytest tests/
```

### Export to requirements.txt (If Needed)

```bash
# For legacy tools that need requirements.txt
poetry export -f requirements.txt --output requirements.txt --without-hashes

# Include dev dependencies
poetry export -f requirements.txt --output requirements-dev.txt --with dev --without-hashes
```

---

## Common Commands Reference

| Task | Command |
|------|---------|
| Install dependencies | `poetry install` |
| Add dependency | `poetry add package` |
| Remove dependency | `poetry remove package` |
| Update dependencies | `poetry update` |
| Show dependencies | `poetry show` |
| Activate virtualenv | `poetry shell` |
| Run command | `poetry run <command>` |
| Export to requirements.txt | `poetry export -f requirements.txt` |
| Check lock file is up to date | `poetry check` |

---

## Migration Complete ✅

The project has been migrated from `requirements.txt` to Poetry:

**Before:**
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

**After:**
```bash
poetry install
poetry run python -m spacy download en_core_web_sm
```

**Benefits:**
- ✅ Deterministic builds (lock file)
- ✅ Better dependency resolution
- ✅ Easier to manage dependencies
- ✅ Virtual environment managed automatically
- ✅ Separate dev and production dependencies

---

## Files Changed

1. **Created:**
   - `pyproject.toml` - Poetry configuration and dependencies
   - `poetry.lock` - Lock file (to be generated)

2. **Modified:**
   - `docker/Dockerfile` - Now uses Poetry
   - `DOCKER_QUICK_START.md` - Updated with Poetry instructions

3. **Kept (for compatibility):**
   - `requirements.txt` - Can still be generated with `poetry export`
   - `setup.py` - Kept for reference, but Poetry handles this now

---

## Troubleshooting

### Poetry command not found
Add Poetry to PATH:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Lock file out of date
```bash
poetry lock --no-update
```

### Clear cache and reinstall
```bash
poetry cache clear pypi --all
rm -rf poetry.lock
poetry install
```

### Dependency conflicts
```bash
# Show dependency tree
poetry show --tree

# Force update resolver
poetry update --lock
```

---

## Next Steps

1. **Generate lock file:** `poetry lock`
2. **Install dependencies:** `poetry install`
3. **Build Docker:** `docker-compose build`
4. **Start platform:** `docker-compose up -d`

🎉 **Poetry setup complete!** All dependencies are now managed with Poetry.
