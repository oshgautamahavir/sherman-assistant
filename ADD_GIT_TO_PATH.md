# Adding Git to Windows PATH

Git is installed at: `C:\Program Files\Git\cmd\`

## Option 1: Add to PATH Permanently (Recommended)

### Using GUI (Easiest):

1. Press `Windows Key + X` and select **"System"**
2. Click **"Advanced system settings"** (on the right)
3. Click **"Environment Variables"** button
4. Under **"User variables"** (top section), find and select **"Path"**
5. Click **"Edit"**
6. Click **"New"**
7. Add: `C:\Program Files\Git\cmd`
8. Click **"OK"** on all dialogs
9. **Close and reopen** your terminal/PowerShell

### Using PowerShell (Run as Administrator):

```powershell
# Add to User PATH
[Environment]::SetEnvironmentVariable(
    "Path",
    [Environment]::GetEnvironmentVariable("Path", "User") + ";C:\Program Files\Git\cmd",
    "User"
)
```

Then restart your terminal.

## Option 2: Temporary (Current Session Only)

I've already added it to your current PowerShell session. You can now use git commands, but you'll need to add it permanently (Option 1) for it to work in new terminals.

## Verify It Works

After adding to PATH, open a **new** terminal and run:

```bash
git --version
```

You should see something like: `git version 2.x.x`

## Next Steps

Once Git is in your PATH, you can proceed with the GitHub setup:

```bash
cd "C:\coding stuff\sherman-assistant"
git init
git add .
git commit -m "Initial commit"
```

Then follow the rest of `GITHUB_SETUP.md` to connect to GitHub and push.

