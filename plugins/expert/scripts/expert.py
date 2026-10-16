#!/usr/bin/env python3
"""Vault helper for the expert plugin.

Standard library only. The knowledge base ("vault") is a git repo of Markdown
pages, cloned to ~/.expert/vault by default and synced to a private remote.

Config (first match wins):
  vault repo   EXPERT_VAULT_REPO, CLAUDE_PLUGIN_OPTION_VAULT_REPO, ~/.expert/config.json "repo"
  vault path   EXPERT_VAULT_PATH, CLAUDE_PLUGIN_OPTION_VAULT_PATH, ~/.expert/config.json "path",
               default ~/.expert/vault
The repo is "owner/name" (GitHub) or any git URL. Without a repo the vault is local only.

Usage:
  expert.py status [--repo DIR]      JSON: vault, project slug, pages, current repo HEAD, tools
  expert.py init <owner/name|url>    Save the vault repo and clone/create the vault
  expert.py ensure                   Clone or pull the vault, seed SCHEMA.md (quiet, never fails hard)
  expert.py scaffold [--repo DIR]    Create projects/<slug>/ with index.md and log.md if missing
  expert.py pages [--repo DIR]       JSON list of the project's pages with frontmatter
  expert.py commit <message>         Commit the vault, pull --rebase, push (queues if offline)
  expert.py lint [--repo DIR]        JSON report: stale pages, broken links, orphans, index gaps
  expert.py hook                     SessionStart hook: sync and print a short context block
"""
import datetime
import filecmp
import json
import os
import re
import shutil
import subprocess
import sys

HOME = os.path.expanduser("~/.expert")
CONFIG = os.path.join(HOME, "config.json")
PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES = os.path.join(PLUGIN_ROOT, "templates")
PULL_TIMEOUT = 15
MAX_PAGE_LINES = 150
SPECIAL_PAGES = {"index", "log"}


# ---------------------------------------------------------------- basics

def out(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def git(args, cwd, timeout=60, check=False):
    try:
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                           timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        if check:
            raise RuntimeError(f"git {' '.join(args)}: {e}")
        return 1, "", str(e)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def git_error(err):
    lines = [l.strip() for l in (err or "").splitlines() if l.strip()]
    for l in lines:
        if l.startswith(("fatal:", "error:")):
            return l
    return lines[0] if lines else "unknown error"


def read_config():
    try:
        with open(CONFIG, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def write_config(cfg):
    os.makedirs(HOME, exist_ok=True)
    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def setting(key, default=""):
    env = os.environ.get(f"EXPERT_VAULT_{key.upper()}") \
        or os.environ.get(f"CLAUDE_PLUGIN_OPTION_VAULT_{key.upper()}")
    return (env or read_config().get(key) or default).strip()


def vault_path():
    return os.path.expanduser(setting("path", os.path.join(HOME, "vault")))


def remote_url(repo):
    if not repo:
        return ""
    if re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
        return f"https://github.com/{repo}.git"
    return repo


def has_remote(vault):
    return git(["remote"], vault)[1] != ""


# ---------------------------------------------------------------- project

def repo_root(start):
    code, top, _ = git(["rev-parse", "--show-toplevel"], start or os.getcwd())
    return top if code == 0 else ""


def slug_for(root):
    """owner-name from the origin URL (any host or proxy), else the folder name."""
    code, url, _ = git(["remote", "get-url", "origin"], root)
    parts = []
    if code == 0 and url:
        path = re.sub(r"\.git/?$", "", url.rstrip("/"))
        path = re.sub(r"^[\w+.-]+://[^/]+/", "", path)   # scheme://host/
        path = re.sub(r"^[^@/]+@[^:/]+:", "", path)       # git@host:
        parts = [p for p in path.split("/") if p][-2:]
    if not parts:
        parts = [os.path.basename(root)]
    slug = "-".join(parts).lower()
    return re.sub(r"[^a-z0-9._-]+", "-", slug).strip("-") or "project"


def project_dir(vault, slug):
    return os.path.join(vault, "projects", slug)


# ---------------------------------------------------------------- frontmatter

def parse_frontmatter(text):
    """Tiny YAML subset: `key: value`, `key: [a, b]` and `key:` followed by `- item` lines."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    meta, key = {}, None
    for line in text[3:end].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = re.match(r"^\s+-\s+(.*)$", line)
        if item and key:
            if not isinstance(meta.get(key), list):
                meta[key] = []
            meta[key].append(item.group(1).strip().strip("'\""))
            continue
        kv = re.match(r"^([\w-]+):\s*(.*)$", line)
        if kv:
            key, val = kv.group(1), kv.group(2).strip()
            if val.startswith("[") and val.endswith("]"):
                meta[key] = [v.strip().strip("'\"") for v in val[1:-1].split(",") if v.strip()]
            else:
                meta[key] = val.strip("'\"")
    body = text[end + 4:].lstrip("\n")
    return meta, body


def as_list(value):
    if isinstance(value, list):
        return value
    return [value] if value else []


def iter_pages(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for name in sorted(filenames):
            if name.endswith(".md"):
                yield os.path.join(dirpath, name)


def load_page(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    meta, body = parse_frontmatter(text)
    return {"meta": meta, "body": body, "lines": text.count("\n") + 1}


WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")


NON_CONTENT = re.compile(r"<!--.*?-->|```.*?```|`[^`\n]*`", re.S)


def links_in(body):
    """Wikilink targets, ignoring comments and code (templates and examples live there)."""
    return WIKILINK.findall(NON_CONTENT.sub("", body))


def link_key(target):
    return os.path.splitext(os.path.basename(target.strip()))[0].lower()


# ---------------------------------------------------------------- vault ops

def seed(vault):
    for name in ("SCHEMA.md", "README.md"):
        dest = os.path.join(vault, name)
        src = os.path.join(TEMPLATES, "vault-" + name)
        if not os.path.exists(dest) and os.path.exists(src):
            shutil.copyfile(src, dest)
    for sub in ("projects", "concepts"):
        os.makedirs(os.path.join(vault, sub), exist_ok=True)


def remote_branch(vault):
    """origin's default branch as 'origin/<name>', or '' when the remote has no branches."""
    head = git(["symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD"], vault)[1]
    if head:
        return head
    for name in ("main", "master"):
        if git(["rev-parse", "-q", "--verify", f"origin/{name}"], vault)[0] == 0:
            return f"origin/{name}"
    return ""


def adopt_remote(vault, info):
    """The vault has a remote but no upstream (a vault created before the repo was set).

    Empty remote: nothing to do; the first commit pushes and sets the upstream.
    No local commits: check out the remote branch, dropping untouched seed files that would block it.
    Local commits: rename the branch to match and replay those commits on top of the remote.
    """
    if git(["fetch", "-q", "origin"], vault, timeout=PULL_TIMEOUT)[0] != 0:
        info["action"] = "offline"
        return
    upstream = remote_branch(vault)
    if not upstream:
        return
    branch = upstream.split("/", 1)[1]
    if git(["rev-parse", "-q", "--verify", "HEAD"], vault)[0] != 0:
        for name in ("SCHEMA.md", "README.md"):
            dest, src = os.path.join(vault, name), os.path.join(TEMPLATES, "vault-" + name)
            if os.path.isfile(dest) and os.path.isfile(src) and filecmp.cmp(dest, src, shallow=False):
                os.remove(dest)
        code, _, err = git(["checkout", "-q", "-B", branch, "--track", upstream], vault)
        if code == 0:
            info["action"] = "adopted-remote"
        else:
            info["warning"] = f"could not check out {upstream} ({git_error(err)}); move the local files away and retry"
        return
    git(["branch", "-q", "-M", branch], vault)
    git(["branch", "-q", "--set-upstream-to", upstream], vault)
    code, _, err = git(["pull", "--rebase", "--autostash", "-q"], vault, timeout=PULL_TIMEOUT)
    if code == 0:
        info["action"] = "rebased-onto-remote"
    else:
        git(["rebase", "--abort"], vault)
        info["warning"] = f"could not replay local notes onto {upstream} ({git_error(err)}); resolve in {vault}"


def ensure():
    """Make the vault exist and be up to date. Returns a dict describing what happened."""
    vault, repo = vault_path(), setting("repo")
    info = {"vault": vault, "repo": repo or None, "action": "none"}
    if not os.path.isdir(os.path.join(vault, ".git")):
        if os.path.isdir(vault) and os.listdir(vault):
            info["error"] = f"{vault} exists and is not a git repo"
            return info
        parent = os.path.dirname(vault)
        os.makedirs(parent, exist_ok=True)
        if repo:
            code, _, err = git(["clone", "-q", remote_url(repo), vault], parent, timeout=120)
            if code != 0:
                info["warning"] = f"clone failed ({git_error(err)}); using a local vault"
                git(["init", "-q", vault], parent)
                git(["remote", "add", "origin", remote_url(repo)], vault)
                info["action"] = "init-local"
            else:
                info["action"] = "cloned"
        else:
            git(["init", "-q", vault], parent)
            info["action"] = "init-local"
    else:
        if repo and not has_remote(vault):
            git(["remote", "add", "origin", remote_url(repo)], vault)
        elif repo and git(["remote", "get-url", "origin"], vault)[1] != remote_url(repo):
            git(["remote", "set-url", "origin", remote_url(repo)], vault)
        if has_remote(vault) and git(["rev-parse", "--abbrev-ref", "@{u}"], vault)[0] != 0:
            adopt_remote(vault, info)
        elif has_remote(vault):
            code, _, err = git(["pull", "--rebase", "--autostash", "-q"], vault, timeout=PULL_TIMEOUT)
            info["action"] = "pulled" if code == 0 else "offline"
            if code != 0:
                git(["rebase", "--abort"], vault)
                info["warning"] = "pull failed: " + git_error(err)
    seed(vault)
    return info


def vault_state(vault):
    state = {"exists": os.path.isdir(os.path.join(vault, ".git"))}
    if not state["exists"]:
        return state
    state["remote"] = git(["remote", "get-url", "origin"], vault)[1] or None
    state["dirty"] = bool(git(["status", "--porcelain"], vault)[1])
    code, ahead, _ = git(["rev-list", "--count", "@{u}..HEAD"], vault)
    state["unpushed_commits"] = int(ahead) if code == 0 and ahead.isdigit() else None
    state["last_commit"] = git(["log", "-1", "--format=%cs %s"], vault)[1] or None
    return state


def project_pages(pdir):
    pages = []
    if not os.path.isdir(pdir):
        return pages
    for path in iter_pages(pdir):
        page = load_page(path)
        meta = page["meta"]
        pages.append({
            "page": os.path.relpath(path, pdir),
            "title": meta.get("title") or os.path.splitext(os.path.basename(path))[0],
            "type": meta.get("type"),
            "updated": meta.get("updated"),
            "verified_commit": meta.get("verified_commit"),
            "lines": page["lines"],
        })
    return pages


# ---------------------------------------------------------------- commands

def cmd_status(start):
    vault = vault_path()
    root = repo_root(start)
    info = {"vault": {"path": vault, "repo": setting("repo") or None, **vault_state(vault)},
            "repo": None, "project": None,
            "tools": {"codebase_memory_mcp": bool(shutil.which("codebase-memory-mcp")),
                      "obsidian_hint": "Open the vault folder in Obsidian for graph view."}}
    if root:
        slug = slug_for(root)
        pdir = project_dir(vault, slug)
        info["repo"] = {"root": root,
                        "head": git(["rev-parse", "--short", "HEAD"], root)[1] or None,
                        "branch": git(["branch", "--show-current"], root)[1] or None,
                        "origin": git(["remote", "get-url", "origin"], root)[1] or None}
        pages = project_pages(pdir)
        info["project"] = {"slug": slug, "dir": pdir, "exists": os.path.isdir(pdir),
                           "page_count": len(pages)}
    out(info)


def cmd_init(repo):
    cfg = read_config()
    cfg["repo"] = repo
    write_config(cfg)
    out(ensure())


def cmd_scaffold(start):
    root = repo_root(start)
    if not root:
        raise ValueError("not inside a git repository")
    vault = vault_path()
    ensure()
    slug = slug_for(root)
    pdir = project_dir(vault, slug)
    created = []
    for sub in ("topics", "maps"):
        os.makedirs(os.path.join(pdir, sub), exist_ok=True)
    origin = git(["remote", "get-url", "origin"], root)[1]
    today = datetime.date.today().isoformat()
    for name in ("index.md", "log.md"):
        dest = os.path.join(pdir, name)
        if os.path.exists(dest):
            continue
        with open(os.path.join(TEMPLATES, "project-" + name), encoding="utf-8") as f:
            text = f.read()
        text = text.replace("{{slug}}", slug).replace("{{origin}}", origin or "(no remote)") \
                   .replace("{{date}}", today)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(text)
        created.append(os.path.relpath(dest, vault))
    out({"slug": slug, "dir": pdir, "created": created})


def cmd_pages(start):
    root = repo_root(start)
    if not root:
        raise ValueError("not inside a git repository")
    pdir = project_dir(vault_path(), slug_for(root))
    out({"dir": pdir, "pages": project_pages(pdir)})


def cmd_commit(message):
    vault = vault_path()
    if not os.path.isdir(os.path.join(vault, ".git")):
        raise ValueError("vault not initialised; run: expert.py ensure")
    git(["add", "-A"], vault, check=True)
    committed = git(["diff", "--cached", "--quiet"], vault)[0] != 0
    if committed:
        code, _, err = git(["commit", "-q", "-m", message], vault)
        if code != 0:
            # No identity configured on this machine: commit with a local one.
            git(["-c", "user.name=expert", "-c", "user.email=expert@localhost",
                 "commit", "-q", "-m", message], vault, check=True)
    result = {"committed": committed, "pushed": False}
    if not has_remote(vault):
        result["note"] = "local vault (no remote); run: expert.py init <owner/name>"
        out(result)
        return
    tracked = git(["rev-parse", "--abbrev-ref", "@{u}"], vault)[0] == 0
    code, err = 0, ""
    if tracked:
        code, _, err = git(["pull", "--rebase", "--autostash", "-q"], vault, timeout=PULL_TIMEOUT)
    if code != 0:
        conflict = bool(git(["diff", "--name-only", "--diff-filter=U"], vault)[1])
        git(["rebase", "--abort"], vault)
        if conflict:
            result["error"] = "merge conflict while pulling; resolve manually in " + vault
            out(result)
            sys.exit(1)
        result["queued"] = True
        result["note"] = "offline: commit kept locally, pushed on the next commit"
        out(result)
        return
    branch = git(["branch", "--show-current"], vault)[1] or "main"
    code, _, err = git(["push", "-q", "-u", "origin", branch], vault, timeout=60)
    result["pushed"] = code == 0
    if code != 0:
        result["queued"] = True
        result["note"] = "push failed: " + git_error(err)
    out(result)


def changed_lines(root, commit, paths):
    code, stat, _ = git(["diff", "--numstat", f"{commit}..HEAD", "--", *paths], root)
    if code != 0:
        return None, []
    total, files = 0, []
    for line in stat.splitlines():
        added, removed, name = (line.split("\t") + ["", "", ""])[:3]
        n = (int(added) if added.isdigit() else 0) + (int(removed) if removed.isdigit() else 0)
        total += n
        files.append(name)
    return total, files


def cmd_lint(start):
    root = repo_root(start)
    if not root:
        raise ValueError("not inside a git repository")
    vault = vault_path()
    pdir = project_dir(vault, slug_for(root))
    if not os.path.isdir(pdir):
        raise ValueError(f"no knowledge base for this project yet ({pdir}); run /expert:onboard")

    # Every page in the vault can be a link target (Obsidian resolves by file name).
    targets = {link_key(p) for p in iter_pages(vault)}
    pages = {p: load_page(p) for p in iter_pages(pdir)}
    index_path = os.path.join(pdir, "index.md")
    index_links = set()
    if index_path in pages:
        index_links = {link_key(t) for t in links_in(pages[index_path]["body"])}

    inbound = {}
    report = {"project": pdir, "stale": [], "unverifiable": [], "missing_sources": [],
              "broken_links": [], "orphans": [], "not_in_index": [], "oversized": [],
              "no_frontmatter": []}
    for path, page in pages.items():
        rel = os.path.relpath(path, pdir)
        key = link_key(path)
        for target in links_in(page["body"]):
            tkey = link_key(target)
            if tkey not in targets:
                report["broken_links"].append({"page": rel, "link": target.strip()})
            elif tkey != key:
                inbound[tkey] = inbound.get(tkey, 0) + 1
        if key in SPECIAL_PAGES:
            continue
        meta = page["meta"]
        if not meta:
            report["no_frontmatter"].append(rel)
        if key not in index_links:
            report["not_in_index"].append(rel)
        if page["lines"] > MAX_PAGE_LINES:
            report["oversized"].append({"page": rel, "lines": page["lines"]})

        sources = [s.split("#")[0].strip() for s in as_list(meta.get("sources"))]
        # Repo paths only; URLs and free-text sources ("git shortlog -sn") are not checked.
        local = [s for s in sources if s and "://" not in s and not re.search(r"\s", s)]
        missing = [s for s in local if not os.path.exists(os.path.join(root, s))]
        if missing:
            report["missing_sources"].append({"page": rel, "paths": missing})
        commit = meta.get("verified_commit")
        present = [s for s in local if s not in missing]
        if not present:
            continue
        if not commit:
            report["unverifiable"].append({"page": rel, "reason": "no verified_commit"})
            continue
        n, files = changed_lines(root, commit, present)
        if n is None:
            report["unverifiable"].append({"page": rel, "reason": f"commit {commit} not in this clone"})
        elif files:
            report["stale"].append({"page": rel, "verified_commit": commit,
                                    "changed_lines": n, "files": files})

    for path in pages:
        key = link_key(path)
        if key not in SPECIAL_PAGES and not inbound.get(key) and key not in index_links:
            report["orphans"].append(os.path.relpath(path, pdir))
    report["stale"].sort(key=lambda s: -s["changed_lines"])
    report["summary"] = {k: len(v) for k, v in report.items() if isinstance(v, list)}
    report["head"] = git(["rev-parse", "--short", "HEAD"], root)[1]
    out(report)


def cmd_hook():
    """SessionStart: print a short context block. Never fails the session."""
    try:
        for key in ("repo", "path"):
            value = os.environ.get(f"CLAUDE_PLUGIN_OPTION_VAULT_{key.upper()}", "").strip()
            cfg = read_config()
            if value and cfg.get(key) != value:
                cfg[key] = value
                write_config(cfg)
        start = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        root = repo_root(start)
        if not root:
            return
        info = ensure()
        vault = info["vault"]
        slug = slug_for(root)
        pdir = project_dir(vault, slug)
        lines = ["## expert plugin", f"Project slug: `{slug}` · vault: `{vault}`"
                 + ("" if setting("repo") else " (local only; set a repo with /expert:onboard)")]
        if info.get("warning"):
            lines.append(f"Vault sync: {info['warning']}")
        index = os.path.join(pdir, "index.md")
        if os.path.exists(index):
            with open(index, encoding="utf-8") as f:
                head = parse_frontmatter(f.read())[1].splitlines()[:60]
            lines.append(f"Knowledge base exists for this project. Before investigating a project question, "
                         f"read the relevant pages in `{pdir}` (use /expert:ask). Index:")
            lines.append("")
            lines.extend(head)
        else:
            lines.append("No knowledge base for this project yet. Suggest /expert:onboard when the user "
                         "starts learning this codebase.")
        print("\n".join(lines))
    except Exception as e:  # noqa: BLE001 - the hook must never break a session
        print(f"expert plugin: context unavailable ({e})")


def take_repo(args):
    if "--repo" in args:
        i = args.index("--repo")
        if i + 1 < len(args):
            return args[i + 1]
    return os.getcwd()


def without_repo(args):
    """Drop a stray `--repo DIR` so it doesn't end up in a commit message."""
    if "--repo" in args:
        i = args.index("--repo")
        return args[:i] + args[i + 2:]
    return args


def main(argv):
    cmd, args = (argv[1] if len(argv) > 1 else "status"), argv[2:]
    try:
        if cmd == "status":
            cmd_status(take_repo(args))
        elif cmd == "init" and args:
            cmd_init(args[0])
        elif cmd == "ensure":
            out(ensure())
        elif cmd == "scaffold":
            cmd_scaffold(take_repo(args))
        elif cmd == "pages":
            cmd_pages(take_repo(args))
        elif cmd == "commit" and without_repo(args):
            cmd_commit(" ".join(without_repo(args)))
        elif cmd == "lint":
            cmd_lint(take_repo(args))
        elif cmd == "hook":
            cmd_hook()
        else:
            print(__doc__)
            return 2
    except (RuntimeError, ValueError, OSError) as e:
        out({"error": str(e)})
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
