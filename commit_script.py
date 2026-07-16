import os
import subprocess
from pathlib import Path

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def get_files():
    status = run_cmd("git status -s")
    files = []
    for line in status.split('\n'):
        if line:
            # Handle possible rename format or just get the last token as filepath
            filepath = line[3:].strip()
            # If it's a directory (ends with /), list its files
            if filepath.endswith('/'):
                for root, _, f_names in os.walk(filepath):
                    for f in f_names:
                        files.append(os.path.join(root, f))
            else:
                files.append(filepath)
    return files

def commit_file(filepath):
    # Determine category and name
    path = Path(filepath)
    name = path.stem.replace('_', ' ')
    
    category = "file"
    if "middlewares" in filepath:
        category = "middleware"
    elif "services" in filepath:
        category = "service"
    elif "routes" in filepath:
        category = "route file"
    elif "utils" in filepath:
        category = "util"
    elif "schemas" in filepath:
        category = "schema"
    elif "workers" in filepath:
        category = "worker"
    elif "tests" in filepath:
        category = "test"
    elif "migrations" in filepath:
        category = "migration"
    elif filepath in ["README.md", ".gitignore", "ci.yml", "Jenkinsfile", "main.py", "Dockerfile", "pyproject.toml", "requirements.txt", "requirements-dev.txt", ".env.example", "alembic.ini"]:
        category = "config file"
    
    # User's format: feat: add <category> to the robot service: <name>
    msg = f"feat: add {category} to the robot service: {name}"
    
    print(f"Committing {filepath} with message: {msg}")
    run_cmd(f"git add {filepath}")
    run_cmd(f'git commit -m "{msg}"')

files = get_files()

# Order: middlewares, services, routes, utils, others
order_categories = ["middlewares", "services", "routes", "utils"]

for cat in order_categories:
    cat_files = [f for f in files if cat in f]
    for f in cat_files:
        commit_file(f)

# others
other_files = [f for f in files if not any(cat in f for cat in order_categories)]
for f in other_files:
    commit_file(f)
