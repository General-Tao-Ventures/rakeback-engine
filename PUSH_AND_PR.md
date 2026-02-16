# Push and open a PR to General-Tao-Ventures

The repo **https://github.com/General-Tao-Ventures/rakeback-engine** is created and `origin` points to it. Your local commit is ready; push from your machine (credentials required).

## 1. Push from your terminal

From the project root (e.g. `c:\Users\-_-\Downloads\Rakeback Engine`):

```powershell
# Push current branch (feature/on-chain-connections) and master
git push -u origin feature/on-chain-connections
git push origin master
```

If GitHub asks for login, use a [Personal Access Token](https://github.com/settings/tokens) or `gh auth login` and then run the same commands.

## 2. Open a Pull Request

1. Go to **https://github.com/General-Tao-Ventures/rakeback-engine**
2. If the default branch is `main` and you pushed `master`, either:
   - Use **Compare & pull request** for the branch you pushed, or
   - Create a PR: **Pull requests** → **New pull request** → base: `main` (or `master`), compare: `feature/on-chain-connections` (or `master`)
3. Add a title and description, then **Create pull request**.

If the repo is still empty (no default branch), the first push of `master` or `feature/on-chain-connections` will set that branch as default; you can then open a PR from the other branch if you want (e.g. `feature/on-chain-connections` → `master`).

## Summary

- **Repo:** https://github.com/General-Tao-Ventures/rakeback-engine  
- **Remote:** `origin` → `https://github.com/General-Tao-Ventures/rakeback-engine.git`  
- **Local:** 1 commit on `master` and `feature/on-chain-connections`  
- **You do:** Run `git push` (see above), then open the PR in the GitHub UI.
