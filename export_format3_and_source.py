#!/usr/bin/env python3
"""
Export format-3 (GeSHi) nodes and source_code nodes directly from the
Drupal 7 database.

Format 3 has no filter_autop -- the stored body_value already matches
what's rendered, except for GeSHi's own <code type="LANG">...</code>
markup, which we rewrite here into plain <pre><code class="language-LANG">
blocks for a modern client-side highlighter (Prism.js) instead of
depending on Drupal's legacy GeSHi PHP module.

source_code nodes have no body_value row at all -- their content lives
entirely in field_data_field_source.field_source_sourcecode.

Requires: pip install pymysql --break-system-packages

Usage:
    python3 export_format3_and_source.py > format3_and_source.json
"""

import html
import json
import re
import sys

import pymysql

DB_CONFIG = dict(
    host="localhost",
    user="CHANGE_ME",
    password="CHANGE_ME",
    database="drupal",
    charset="utf8mb4",
    cursorclass=pymysql.cursors.Cursor,
)

# Map file extensions (from source_code node titles like "trianglefan.cpp")
# to Prism language classes.
EXT_TO_LANG = {
    "cpp": "cpp", "cc": "cpp", "c": "c", "h": "cpp",
    "php": "php", "pl": "perl", "pm": "perl",
    "py": "python", "js": "javascript", "java": "java",
    "sh": "bash", "rb": "ruby",
}

CODE_TAG_RE = re.compile(
    r'<code\s+type="([^"]+)">(.*?)</code>', re.DOTALL | re.IGNORECASE
)


def geshi_to_pre(body):
    """Rewrite <code type="lang">...</code> into <pre><code class="language-lang">."""

    def repl(match):
        lang = match.group(1).strip().lower()
        raw_code = match.group(2)
        # The stored content may already contain HTML entities; normalize
        # to plain text then re-escape safely for embedding.
        text = html.unescape(raw_code)
        escaped = html.escape(text)
        return f'<pre><code class="language-{lang}">{escaped}</code></pre>'

    return CODE_TAG_RE.sub(repl, body)


def clean_body(body):
    body = body.replace("<!--break-->", "")
    body = geshi_to_pre(body)
    return body


def get_tags(cursor, nid):
    cursor.execute(
        """
        SELECT t.name
        FROM field_data_taxonomy_vocabulary_2 f
        INNER JOIN taxonomy_term_data t ON t.tid = f.taxonomy_vocabulary_2_tid
        WHERE f.entity_id = %s
        """,
        (nid,),
    )
    return [row[0] for row in cursor.fetchall()]


def get_alias(cursor, nid):
    cursor.execute(
        "SELECT alias FROM url_alias WHERE source = %s ORDER BY pid DESC LIMIT 1",
        (f"node/{nid}",),
    )
    row = cursor.fetchone()
    return row[0] if row else None


def guess_lang(title):
    ext = title.rsplit(".", 1)[-1].lower() if "." in title else ""
    return EXT_TO_LANG.get(ext, "")


def main():
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    nodes = []

    # --- format-3 (GeSHi) nodes ---
    cursor.execute(
        """
        SELECT n.nid, n.type, n.title, n.created, b.body_value
        FROM node n
        INNER JOIN field_data_body b ON b.entity_id = n.nid
        WHERE b.body_format = '3'
        AND n.status = 1
        ORDER BY n.nid
        """
    )
    for nid, ntype, title, created, body in cursor.fetchall():
        nodes.append(
            {
                "nid": nid,
                "type": ntype,
                "title": title,
                "created": created,
                "alias": get_alias(cursor, nid),
                "tags": get_tags(cursor, nid),
                "body_html": clean_body(body or ""),
            }
        )

    # --- source_code nodes (no body row; content in field_source_sourcecode) ---
    cursor.execute(
        """
        SELECT n.nid, n.title, n.created, s.field_source_sourcecode
        FROM node n
        INNER JOIN field_data_field_source s ON s.entity_id = n.nid
        WHERE n.type = 'source_code'
        AND n.status = 1
        ORDER BY n.nid
        """
    )
    for nid, title, created, code in cursor.fetchall():
        lang = guess_lang(title)
        escaped = html.escape(code or "")
        body_html = f'<pre><code class="language-{lang}">{escaped}</code></pre>'
        nodes.append(
            {
                "nid": nid,
                "type": "source_code",
                "title": title,
                "created": created,
                "alias": get_alias(cursor, nid),
                "tags": get_tags(cursor, nid),
                "body_html": body_html,
            }
        )

    json.dump(nodes, sys.stdout, indent=2, ensure_ascii=False)
    print(file=sys.stderr)
    print(f"Exported {len(nodes)} nodes (format 3 + source_code)", file=sys.stderr)


if __name__ == "__main__":
    main()
