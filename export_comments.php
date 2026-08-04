<?php
/**
 * Export published comments attached to published nodes.
 *
 * Comment bodies go through the same filter-format pipeline as node
 * bodies, so we render each through check_markup() rather than trusting
 * the raw stored value.
 *
 * Run with:
 *   drush php-script export_comments.php > comments.json
 */

$sql = "
  SELECT c.cid, c.pid, c.nid, c.uid, c.name, c.subject, c.created,
         cb.comment_body_value, cb.comment_body_format
  FROM {comment} c
  INNER JOIN {node} n ON n.nid = c.nid
  LEFT JOIN {field_data_comment_body} cb ON cb.entity_id = c.cid
  WHERE c.status = 1
  AND n.status = 1
  ORDER BY c.nid, c.thread
";

$result = db_query($sql);

$comments = array();

foreach ($result as $row) {
  // Anonymous commenters have their name in comment.name; registered
  // users have uid set and need a lookup.
  $author = trim($row->name);
  if ($author === '' && $row->uid > 0) {
    $account = user_load($row->uid);
    $author = $account ? $account->name : 'Anonymous';
  }
  if ($author === '') {
    $author = 'Anonymous';
  }

  $body_html = '';
  if ($row->comment_body_value !== NULL) {
    $body_html = check_markup($row->comment_body_value, $row->comment_body_format);
    $body_html = str_replace('<!--break-->', '', $body_html);
  }

  $comments[] = array(
    'cid'       => (int) $row->cid,
    'pid'       => $row->pid ? (int) $row->pid : NULL, // parent comment, for threading
    'nid'       => (int) $row->nid,
    'author'    => $author,
    'subject'   => $row->subject,
    'created'   => (int) $row->created,
    'body_html' => $body_html,
  );
}

echo json_encode($comments, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
echo "\n";

fwrite(STDERR, "Exported " . count($comments) . " comments\n");
