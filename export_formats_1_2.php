<?php
/**
 * Export nodes using body_format 1 (Filtered HTML) or 2 (Full HTML).
 *
 * These formats include filter_autop (line breaks -> <p>/<br>), filter_url
 * (auto-link bare URLs), and filter_htmlcorrector (tag balancing), so we
 * run each body through Drupal's own check_markup() to get exactly what
 * the live site renders today, rather than guessing at the transforms.
 *
 * Run with:
 *   drush php-script export_formats_1_2.php > formats_1_2.json
 */

$sql = "
  SELECT n.nid, n.type, n.title, n.created, b.body_value, b.body_format
  FROM {node} n
  INNER JOIN {field_data_body} b ON b.entity_id = n.nid
  WHERE b.body_format IN ('1', '2')
  AND n.status = 1
  ORDER BY n.nid
";

$result = db_query($sql);

$nodes = array();

foreach ($result as $row) {
  $nid = (int) $row->nid;

  // Render exactly as Drupal would (applies autop, url, htmlcorrector, etc.
  // per the node's actual format).
  $rendered = check_markup($row->body_value, $row->body_format);

  // Drupal's teaser-break marker is an HTML comment -- invisible either way,
  // but strip it for a clean source file.
  $rendered = str_replace('<!--break-->', '', $rendered);

  // Path alias, if one exists.
  $alias = drupal_get_path_alias('node/' . $nid);
  if ($alias === 'node/' . $nid) {
    $alias = NULL; // no alias was set
  }

  // Tags (vocabulary_2), if any.
  $tags = array();
  $tag_result = db_query(
    "SELECT t.name
     FROM {field_data_taxonomy_vocabulary_2} f
     INNER JOIN {taxonomy_term_data} t ON t.tid = f.taxonomy_vocabulary_2_tid
     WHERE f.entity_id = :nid",
    array(':nid' => $nid)
  );
  foreach ($tag_result as $tag_row) {
    $tags[] = $tag_row->name;
  }

  $nodes[] = array(
    'nid'       => $nid,
    'type'      => $row->type,
    'title'     => $row->title,
    'created'   => (int) $row->created,
    'alias'     => $alias,
    'tags'      => $tags,
    'body_html' => $rendered,
  );
}

echo json_encode($nodes, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
echo "\n";

fwrite(STDERR, "Exported " . count($nodes) . " nodes (formats 1 & 2)\n");
