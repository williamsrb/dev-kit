---
id: how-to-stop-graft-writing-repo-ignore-files
when_skills: [graft]
inputs: [graft CLI (@nanonets/graft 0.18.0), ~/.gitignore_global, ~/.xsessionrc, ~/.config/environment.d]
outputs: [no graft block in repo .gitignore, no repo .ignore]
stop_if: [repo tracks graft/ on purpose]
read: whole
prose: caveman-lite
---

# Stop graft writing repo ignore files

Every `graft build` (CLI, hook, or the MCP server's refresh before a query) appends a `/graft/` block to the repo's `.gitignore` and creates a root `.ignore` that re-admits `graft/` to ripgrep. Source: `dist/context/node-file.js`, `ensureGitignored` and `ensureSearchable`. The patterns belong in the global git ignore instead.

## Procedure

1. Opt out with the built-in switches: `GRAFT_NO_GITIGNORE=1` skips `.gitignore`, `GRAFT_NO_IGNORE=1` skips `.ignore`. Any non-empty value other than `0` or `false` counts.
2. Set them where the desktop session reads its environment. This machine is XFCE under lightdm (X11): `~/.xsessionrc` exports both, because `/etc/X11/Xsession` sources it and every app inherits from there. `~/.config/environment.d/90-graft.conf` also sets them, but that reaches only services the systemd user manager starts, not XFCE apps.
3. devkit profiles get them from every wrapper in `templates/shell/` and from `auth.bind_profile_env` for desktop launches.
4. Keep the patterns in the global ignore (`git config --global core.excludesFile`, here `~/.gitignore_global`). devkit's `globalignore.ensure` writes the same block.
5. Log out and back in. Restarting an app is not enough: it inherits the old session environment. Check the process that runs graft, not the window: `tr '\0' '\n' < /proc/$(pgrep -f cursor-agent-worker | head -1)/environ | grep '^GRAFT_NO'`. Cursor's main process (`pgrep -x cursor`) never carries them and does not need to.
6. Verify in a scratch repo: `git init`, add one source file, `graft build`, and no `.gitignore` or `.ignore` appears.

## Pitfalls

- A graft MCP server started before the variables existed keeps its old environment and writes the block again on its next refresh. The re-write shows up staged if you `git add -A`.
- `systemctl --user show-environment` listing the variables proves nothing about GUI apps. On XFCE/lightdm they come from `/etc/X11/Xsession`; on GNOME they come from the systemd user environment. Check the app's own `/proc/<pid>/environ`.
- In the global ignore, `!**/skills/graft` and `!**/hooks/graft` only work after the `graft` line. Write the whole block in order. Appending only the missing lines can re-ignore the kit's `skills/graft/`.
- Without `.ignore`, ripgrep and the Grep tool skip `graft/` cards, because the global ignore hides them. Use `graft grep` or `rg -uu` to search cards.
- Repos that already committed graft's block keep it. Remove it per repo only when that repo's owner asks.
