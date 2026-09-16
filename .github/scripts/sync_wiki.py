#!/usr/bin/env python3
"""
Mirror the repo's Markdown files into a GitHub wiki checkout.

GitHub wikis (gollum) use a flat page namespace: a page's URL is just its
filename, with no folders. So every source file gets a unique flat slug
(e.g. Geography/Cities.md -> Geography-Cities.md, Geography/README.md ->
Geography.md, root README.md -> Home.md), and every relative Markdown
link is rewritten to point at the resolved file's slug instead of its
original relative path.
"""
import os
import re
import shutil
import sys

EXCLUDE_DIRS = {".git", ".github", ".obsidian", "wiki"}
LINK_RE = re.compile(r"(\[[^\]]*\]\()([^)\s]+)(\))")


def find_md_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for f in filenames:
            if f.endswith(".md"):
                full = os.path.join(dirpath, f)
                rel = os.path.relpath(full, root)
                yield rel.replace(os.sep, "/")


def slug_for(relpath):
    if relpath == "README.md":
        return "Home"
    stem = relpath[:-3]
    parts = stem.split("/")
    if parts[-1] == "README":
        parts = parts[:-1]
    return "-".join(parts)


def resolve_link(current_rel, target):
    if target.startswith(("http://", "https://", "mailto:", "#")):
        return None
    path, anchor = (target.split("#", 1) + [""])[:2]
    if not path.endswith(".md"):
        return None
    current_dir = os.path.dirname(current_rel)
    resolved = os.path.normpath(os.path.join(current_dir, path)).replace(os.sep, "/")
    return resolved, ("#" + anchor if anchor else "")


def main():
    repo_root = sys.argv[1] if len(sys.argv) > 1 else "."
    wiki_root = sys.argv[2] if len(sys.argv) > 2 else "wiki"

    rels = sorted(find_md_files(repo_root))
    slug_map = {rel: slug_for(rel) for rel in rels}

    def rewrite(current_rel, content):
        def repl(m):
            prefix, target, suffix = m.groups()
            result = resolve_link(current_rel, target)
            if result is None:
                return m.group(0)
            resolved, anchor = result
            slug = slug_map.get(resolved)
            if slug is None:
                return m.group(0)
            return f"{prefix}{slug}{anchor}{suffix}"

        return LINK_RE.sub(repl, content)

    os.makedirs(wiki_root, exist_ok=True)
    for name in os.listdir(wiki_root):
        if name == ".git":
            continue
        path = os.path.join(wiki_root, name)
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)

    for rel in rels:
        with open(os.path.join(repo_root, rel), encoding="utf-8") as fh:
            content = fh.read()
        new_content = rewrite(rel, content)
        slug = slug_map[rel]
        out_path = os.path.join(wiki_root, slug + ".md")
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(new_content)
        print(f"{rel} -> {slug}.md")


if __name__ == "__main__":
    main()
