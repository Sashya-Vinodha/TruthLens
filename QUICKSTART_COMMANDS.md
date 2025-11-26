# TruthLens - Quick Start Commands

## 🚀 FOR YOU (Backend Owner - Sashya)

### First Time Setup
```bash
cd /Users/sashya/Documents/All-Projects/TruthLens
source .venv/bin/activate
pip install -r requirements.txt
```

### Daily Workflow
```bash
# Start your day
git fetch origin
git pull origin feat/backend

# Work on backend
nano truthlens/backend/app/main.py

# Test locally
bash scripts/run_dev.sh

# Commit and push
git add .
git commit -m "feat: describe your changes"
git push origin feat/backend

# Create PR on GitHub
# https://github.com/Sashya-Vinodha/TruthLens/pulls
```

### Review & Merge PRs from Teammates
```bash
# Checkout teammate's branch to test
git fetch origin
git checkout feat/dataset
git pull origin feat/dataset

# Test it works
bash scripts/run_dev.sh

# If good, approve on GitHub and merge
# If conflicts, resolve locally and push
```

---

## 👤 FOR TEAMMATE 1 (Dataset Manager)

### First Time Setup
```bash
git clone https://github.com/Sashya-Vinodha/TruthLens.git
cd TruthLens
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Daily Workflow
```bash
# Start your day
git checkout feat/dataset
git pull origin feat/dataset

# Edit ONLY docs.json
nano truthlens/backend/data/docs.json

# Build index
bash scripts/build_index.sh

# Commit and push
git add truthlens/backend/data/docs.json
git commit -m "docs: update dataset [describe changes]"
git push origin feat/dataset

# Create PR: https://github.com/Sashya-Vinodha/TruthLens/pulls
```

### ⚠️ Remember
- Edit ONLY: `truthlens/backend/data/docs.json`
- DO NOT touch any `.py` files
- Always run `bash scripts/build_index.sh`
- Always create PR, never direct commit

---

## 👤 FOR TEAMMATE 2 (Frontend UI Developer)

### First Time Setup
```bash
git clone https://github.com/Sashya-Vinodha/TruthLens.git
cd TruthLens
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Daily Workflow
```bash
# Start your day
git checkout feat/ui
git pull origin feat/ui

# Edit frontend
nano truthlens/frontend/public/index.html

# Test locally (backend must be running)
# In one terminal:
# bash scripts/run_dev.sh
# Open: http://localhost:8000/index.html

# Commit and push
git add truthlens/frontend/public/
git commit -m "ui: [describe changes]"
git push origin feat/ui

# Create PR: https://github.com/Sashya-Vinodha/TruthLens/pulls
```

### ⚠️ Remember
- Edit ONLY: `truthlens/frontend/public/`
- DO NOT touch any Python files
- DO NOT edit backend
- Always create PR, never direct commit

---

## 🔄 Pulling Changes (For Everyone)

```bash
# Before starting work
git fetch origin
git pull origin YOUR-BRANCH-NAME

# Check what's new in dev
git log --oneline origin/dev -5
```

---

## 📋 GitHub URLs

- **Repository**: https://github.com/Sashya-Vinodha/TruthLens
- **Create PR**: https://github.com/Sashya-Vinodha/TruthLens/pulls
- **Branch Settings**: https://github.com/Sashya-Vinodha/TruthLens/settings/branches
- **Issues**: https://github.com/Sashya-Vinodha/TruthLens/issues

---

## ✅ PR Review Checklist (For Backend Owner)

When reviewing teammate PRs:

1. ✅ Checkout their branch: `git checkout feat/dataset`
2. ✅ Pull: `git pull origin feat/dataset`
3. ✅ Test: `bash scripts/run_dev.sh`
4. ✅ Review code: Check only files they should edit
5. ✅ Approve on GitHub
6. ✅ Merge to dev
7. ✅ Delete branch (optional)

---

## 🚨 Branch Protection Rules (Active)

- ✅ `main` - Requires 1 approval before merge
- ✅ `dev` - Requires 1 approval before merge
- ✅ All PRs must come from `feat/*` branches

---

## 📊 File Structure & Permissions

```
truthlens/
├── backend/
│   ├── app/              ← Backend owner ONLY
│   └── data/
│       └── docs.json     ← Dataset teammate ONLY
└── frontend/
    └── public/           ← UI teammate ONLY
```

---

## 🆘 If Something Goes Wrong

### Merge Conflict?
```bash
git status  # See conflicts
nano conflicted_file.py  # Fix manually
git add .
git commit -m "chore: resolve conflicts"
git push origin YOUR-BRANCH
```

### Wrong Branch?
```bash
git checkout correct-branch
```

### Want to Undo Last Commit?
```bash
git reset HEAD~1
# Changes are unstaged, edit again if needed
```

### Lost Changes?
```bash
git reflog  # See all actions
git checkout HASH  # Go back to specific commit
```

---

## 🎯 Merging to Main (When Project is Complete)

1. Merge all `feat/*` branches → `dev`
2. Test everything on `dev`
3. Create PR: `dev` → `main`
4. Merge with 1 approval
5. Tag release: `git tag v1.0.0 && git push origin v1.0.0`

---

## 📝 Useful Commands

```bash
# See current branch
git branch

# See all branches (local + remote)
git branch -a

# See commit history
git log --oneline -10

# See what changed in a file
git diff truthlens/backend/app/main.py

# See unstaged changes
git status

# Stash work temporarily
git stash
git stash pop

# Delete local branch
git branch -d feat/old-feature

# Rename branch
git branch -m old-name new-name
```

---

## 📞 Contact

- **Backend Issues**: Ask Sashya (backend owner)
- **Dataset Issues**: Ask Teammate 1
- **UI Issues**: Ask Teammate 2
- **General Questions**: Create GitHub Issue
