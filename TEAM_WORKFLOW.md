# Team Workflow Instructions

## 🚀 Quick Setup for All Teammates

### Step 1: Clone the Repository
```bash
git clone https://github.com/Sashya-Vinodha/TruthLens.git
cd TruthLens
```

### Step 2: Create Python Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate   # Mac/Linux
# OR on Windows:
.venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 👤 TEAMMATE 1: Dataset Manager

### Your Responsibilities
- Edit ONLY: `truthlens/backend/data/docs.json`
- Run: `bash scripts/build_index.sh` after changes
- Push to: `feat/dataset` branch
- Create PR to: `dev` branch

### Workflow (Copy-Paste)

```bash
# 1. Switch to your branch
git checkout feat/dataset

# 2. Pull latest changes
git pull origin feat/dataset

# 3. Edit ONLY this file
nano truthlens/backend/data/docs.json

# 4. Build the index (important!)
bash scripts/build_index.sh

# 5. Check your changes
git status

# 6. Commit
git add truthlens/backend/data/docs.json
git commit -m "docs: update dataset with [describe changes]"

# 7. Push
git push origin feat/dataset

# 8. Create PR on GitHub
# Go to: https://github.com/Sashya-Vinodha/TruthLens/pulls
# Click "New Pull Request" → feat/dataset → dev
# Add description and submit
```

### ⚠️ DO NOT
- Touch any `.py` files
- Edit `truthlens/backend/app/`
- Edit `truthlens/frontend/`
- Modify `.faiss.index` or embeddings
- Commit directly to `dev` or `main`

### ✅ DO
- Edit `truthlens/backend/data/docs.json`
- Run `scripts/build_index.sh`
- Always create a PR, never direct commit

---

## 👤 TEAMMATE 2: Frontend UI Developer

### Your Responsibilities
- Edit ONLY: `truthlens/frontend/public/` folder
- NO backend Python code
- Push to: `feat/ui` branch
- Create PR to: `dev` branch

### Workflow (Copy-Paste)

```bash
# 1. Switch to your branch
git checkout feat/ui

# 2. Pull latest changes
git pull origin feat/ui

# 3. Edit frontend files
nano truthlens/frontend/public/index.html

# 4. Test locally (make sure backend is running)
# In another terminal:
# bash scripts/run_dev.sh
# Then open: http://localhost:8000/index.html

# 5. Check your changes
git status

# 6. Commit
git add truthlens/frontend/public/
git commit -m "ui: [describe your changes]"

# 7. Push
git push origin feat/ui

# 8. Create PR on GitHub
# Go to: https://github.com/Sashya-Vinodha/TruthLens/pulls
# Click "New Pull Request" → feat/ui → dev
# Add description and submit
```

### ⚠️ DO NOT
- Touch any Python files
- Edit `truthlens/backend/`
- Run pip install (use npm only if needed for frontend)
- Commit directly to `dev` or `main`

### ✅ DO
- Edit ONLY `truthlens/frontend/public/` (HTML/CSS/JS)
- Test locally before pushing
- Always create a PR, never direct commit

---

## 👤 BACKEND OWNER: Your Workflow

### Your Responsibilities
- Edit: `truthlens/backend/app/` folder
- Run tests: `bash scripts/run_dev.sh`
- Push to: `feat/backend` branch
- Create PR to: `dev` branch

### Workflow (Copy-Paste)

```bash
# 1. Switch to your branch
git checkout feat/backend

# 2. Pull latest changes
git pull origin feat/backend

# 3. Edit backend files
nano truthlens/backend/app/main.py

# 4. Test locally
bash scripts/run_dev.sh

# 5. Test API
curl -X POST "http://127.0.0.1:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"question":"Test question?","k":3}'

# 6. Check your changes
git status

# 7. Commit
git add truthlens/backend/app/
git commit -m "feat: [describe your changes]"

# 8. Push
git push origin feat/backend

# 9. Create PR on GitHub
# Go to: https://github.com/Sashya-Vinodha/TruthLens/pulls
# Click "New Pull Request" → feat/backend → dev
# Add description and submit
```

### ✅ DO
- Edit `truthlens/backend/app/`
- Run tests before pushing
- Always create a PR, never direct commit
- Review teammate PRs

---

## 🔄 Pulling Latest Changes

**Before starting work each day:**

```bash
# Fetch latest changes from remote
git fetch origin

# Pull from your branch
git pull origin YOUR-BRANCH-NAME

# Check what changed in dev
git log --oneline origin/dev -5
```

---

## 📋 Creating a Pull Request (PR)

### Step 1: After pushing, go to GitHub
https://github.com/Sashya-Vinodha/TruthLens/pulls

### Step 2: Click "New Pull Request"

### Step 3: Select branches
- **Base**: `dev` (where you want to merge)
- **Compare**: Your branch (e.g., `feat/backend`)

### Step 4: Add title and description
Example:
```
Title: Add health check endpoint

Description:
- Added /health GET endpoint
- Returns status and uptime
- Tested locally with curl
```

### Step 5: Submit PR
Wait for review and approval before merging.

---

## ⚠️ Resolving Merge Conflicts

If you see conflicts:

```bash
# Check conflict status
git status

# Open conflicted files and resolve manually
nano truthlens/backend/app/main.py

# Look for <<<<<<< HEAD ... ======= ... >>>>>>> markers
# Keep the code you want, delete conflict markers

# After resolving:
git add .
git commit -m "chore: resolve merge conflicts with dev"
git push origin YOUR-BRANCH-NAME
```

---

## 🚨 Important Rules

1. ❌ **NEVER commit directly to `main` or `dev`**
2. ❌ **NEVER merge your own PR** (wait for review)
3. ✅ **ALWAYS create PRs from feat/* → dev**
4. ✅ **ALWAYS pull before starting work**
5. ✅ **ALWAYS test locally before pushing**
6. ✅ **ALWAYS write clear commit messages**

---

## 📝 Commit Message Format

```
feat: add new feature
fix: fix a bug
docs: update documentation
chore: maintenance work (no code changes)
refactor: restructure existing code
test: add or update tests
```

Example:
```bash
git commit -m "feat: add query validation"
git commit -m "fix: handle edge case in indexer"
git commit -m "docs: update README"
```

---

## ❓ Questions?

If you encounter issues:
1. Check branch protection rules
2. Make sure you're on correct branch: `git status`
3. Pull latest: `git pull origin YOUR-BRANCH`
4. Check file permissions in `CODEOWNERS`
5. Ask Sashya (backend owner) for help

---

## 🎯 Final Checklist

- ✅ Clone repo
- ✅ Create venv
- ✅ Install deps
- ✅ Switch to your branch
- ✅ Edit files in your designated folder ONLY
- ✅ Test locally
- ✅ Commit with clear message
- ✅ Push to your branch
- ✅ Create PR to `dev`
- ✅ Wait for approval
- ✅ Done! 🚀
