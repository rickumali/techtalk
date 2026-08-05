#!/usr/bin/env python3
"""
Merge format3.json, formats_1_2.json, and comments.json into an Eleventy
(11ty) project structure:

    posts/NNN-slug.html   -- one file per published node, YAML front matter
                             + raw body HTML as the template content
    _data/comments.json   -- comments grouped by nid, for lookup in templates

Usage:
    python3 merge_and_generate.py \
        --format3 format3.json \
        --formats12 formats_1_2.json \
        --comments comments.json \
        --out ./site
"""

import argparse
import json
import os
import re
from datetime import datetime, timezone
from html import unescape


def strip_tags(html_str):
    text = re.sub(r"<[^>]+>", " ", html_str)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def make_excerpt(body_html, max_len=220):
    """Pull a preview snippet: prefer the first <p>...</p>, falling back to
    the first bit of plain text if a node has no paragraph tags at all
    (some format-3/GeSHi nodes don't use filter_autop -- see the migration
    notes). Code blocks are excluded either way so a snippet never opens
    mid-source-code."""
    no_code = re.sub(r"<pre>.*?</pre>", " ", body_html, flags=re.DOTALL)

    match = re.search(r"<p[^>]*>(.*?)</p>", no_code, re.DOTALL)
    text = strip_tags(match.group(1)) if match else strip_tags(no_code)

    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0].rstrip(",.;:") + "…"
    return text


def yaml_str(value):
    """A JSON string literal is also a valid YAML double-quoted scalar,
    so this safely handles titles with quotes, colons, apostrophes, etc.
    without needing a YAML library."""
    return json.dumps(value, ensure_ascii=False)


def yaml_list(values):
    return "[" + ", ".join(yaml_str(v) for v in values) + "]"


def slug_from_alias(alias, nid):
    """Derive a filesystem-safe slug from the Drupal path alias, falling
    back to the raw nid if no alias exists."""
    if alias:
        last_segment = alias.rstrip("/").rsplit("/", 1)[-1]
        return last_segment
    return f"node-{nid}"


def to_date_string(created_ts):
    if not created_ts:
        return None
    dt = datetime.fromtimestamp(created_ts, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d")


def build_front_matter(node):
    date_str = to_date_string(node.get("created"))
    lines = ["---"]
    lines.append(f"title: {yaml_str(node['title'])}")
    if date_str:
        lines.append(f"date: {date_str}")
    if node.get("tags"):
        lines.append(f"tags: {yaml_list(node['tags'])}")
    if node.get("alias"):
        # Preserve the exact old URL as the output path.
        lines.append(f"permalink: \"/{node['alias']}/index.html\"")
    lines.append(f"excerpt: {yaml_str(make_excerpt(node.get('body_html') or ''))}")
    lines.append(f"nid: {node['nid']}")
    lines.append(f"nodeType: {yaml_str(node['type'])}")
    lines.append("layout: post.njk")
    lines.append("---")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--format3", required=True)
    ap.add_argument("--formats12", required=True)
    ap.add_argument("--comments", required=True)
    ap.add_argument("--out", default="./site")
    args = ap.parse_args()

    with open(args.format3, encoding="utf-8") as f:
        nodes_f3 = json.load(f)
    with open(args.formats12, encoding="utf-8") as f:
        nodes_f12 = json.load(f)
    with open(args.comments, encoding="utf-8") as f:
        comments = json.load(f)

    all_nodes = nodes_f3 + nodes_f12
    all_nodes.sort(key=lambda n: n.get("created") or 0)

    posts_dir = os.path.join(args.out, "posts")
    data_dir = os.path.join(args.out, "_data")
    os.makedirs(posts_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)

    seen_slugs = set()
    written = 0

    for node in all_nodes:
        nid = node["nid"]
        slug = slug_from_alias(node.get("alias"), nid)

        # Filename just needs to be unique on disk; the real URL comes
        # from the `permalink` front matter above, which uses the alias.
        filename = f"{nid:03d}-{slug}.html"
        if filename in seen_slugs:
            filename = f"{nid:03d}-{slug}-{nid}.html"
        seen_slugs.add(filename)

        front_matter = build_front_matter(node)
        content = front_matter + "\n" + (node.get("body_html") or "") + "\n"

        with open(os.path.join(posts_dir, filename), "w", encoding="utf-8") as f:
            f.write(content)
        written += 1

    # Group comments by nid (string keys, since Eleventy data files come
    # back as plain JSON and templates will look up by node's `nid`).
    comments_by_nid = {}
    for c in comments:
        comments_by_nid.setdefault(str(c["nid"]), []).append(c)

    # Keep each node's comments in creation order.
    for nid_key in comments_by_nid:
        comments_by_nid[nid_key].sort(key=lambda c: c.get("created") or 0)

    with open(os.path.join(data_dir, "comments.json"), "w", encoding="utf-8") as f:
        json.dump(comments_by_nid, f, indent=2, ensure_ascii=False)

    print(f"Wrote {written} post files to {posts_dir}")
    print(f"Wrote comments for {len(comments_by_nid)} nodes to {data_dir}/comments.json")
    print(f"Total nodes: {len(all_nodes)} | Total comments: {len(comments)}")


if __name__ == "__main__":
    main()
