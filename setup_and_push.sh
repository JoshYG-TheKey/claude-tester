#!/bin/bash

echo "Setting up Git repository and pushing code..."

# Initialize git if not already initialized
if [ ! -d .git ]; then
    echo "Initializing Git repository..."
    git init
fi

# Add the remote repository if it doesn't exist
if ! git remote | grep -q "origin"; then
    echo "Adding remote repository..."
    git remote add origin git@github.com:ortoo/claude-testing-streamlit.git
fi

# Create .gitignore if it doesn't exist
if [ ! -f .gitignore ]; then
    echo "Creating .gitignore..."
    cat > .gitignore << EOL
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
.env
.venv
venv/
ENV/
.idea/
.vscode/
*.db
*.sqlite3
.DS_Store
node_modules/
EOL
fi

# Add all files
echo "Adding files to Git..."
git add .

# Commit changes
echo "Committing changes..."
git commit -m "Initial commit: Claude Testing Streamlit Application

- Added Streamlit application for testing Claude responses
- Implemented database persistence with Cloud Storage
- Added deployment scripts for GCP Cloud Run
- Set up in London region (europe-west2)
- Configured automatic scaling (1-10 instances)"

# Push to main branch
echo "Pushing to repository..."
git push -u origin main

echo "✅ Code has been pushed to the repository!"
echo "🌐 Repository URL: https://github.com/ortoo/claude-testing-streamlit" 