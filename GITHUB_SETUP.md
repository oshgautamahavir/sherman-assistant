# GitHub Setup Guide

## Step 1: Install Git

### Windows:
1. Download Git from: https://git-scm.com/download/win
2. Run the installer (use default options)
3. Restart your terminal/PowerShell

### Verify Installation:
```bash
git --version
```

## Step 2: Configure Git (First Time Only)

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

## Step 3: Initialize Repository

```bash
# Navigate to your project directory
cd "C:\coding stuff\sherman-assistant"

# Initialize git repository
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: Sherman Assistant API"
```

## Step 4: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `sherman-assistant` (or your preferred name)
3. Description: "Django API for scraping and vectorizing travel content"
4. Choose Public or Private
5. **DO NOT** initialize with README, .gitignore, or license (we already have these)
6. Click "Create repository"

## Step 5: Connect and Push

After creating the repo, GitHub will show you commands. Use these:

```bash
# Add remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/sherman-assistant.git

# Rename branch to main (if needed)
git branch -M main

# Push to GitHub
git push -u origin main
```

## Alternative: Using GitHub Desktop

If you prefer a GUI:

1. Download GitHub Desktop: https://desktop.github.com/
2. Sign in with your GitHub account
3. Click "File" → "Add Local Repository"
4. Browse to: `C:\coding stuff\sherman-assistant`
5. Click "Publish repository" button
6. Choose name and visibility
7. Click "Publish repository"

---

## Important Notes

- **Never commit `.env` file** - It contains your API keys!
- The `.gitignore` file I created will automatically exclude:
  - `.env` files
  - `venv/` folder
  - `__pycache__/` folders
  - `db.sqlite3` database
  - Other sensitive/unnecessary files

## Troubleshooting

### "git is not recognized"
- Git is not installed or not in PATH
- Restart terminal after installing Git
- Or use GitHub Desktop instead

### "Permission denied"
- Make sure you're authenticated with GitHub
- Use: `gh auth login` (if GitHub CLI is installed)
- Or use HTTPS with personal access token

### "Repository already exists"
- You might have already initialized git
- Check with: `git status`
- If it shows files, you're good to go!

