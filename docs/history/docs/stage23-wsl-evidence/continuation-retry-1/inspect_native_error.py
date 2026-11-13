"""Read-only diagnostic metadata; never opens authentication or rollout files."""
import sqlite3
import json
import re
from pathlib import Path

connection = sqlite3.connect('file:/home/ivan/.codex/logs_2.sqlite?mode=ro', uri=True)
thread = '01a11698-9739-7733-866d-f9f471b63c58'
receipt = Path(__file__).parent / 'architect/architect-1/architect-execution.json'
ended = receipt.stat().st_mtime
rows = connection.execute('SELECT ts, level, target, feedback_log_body FROM logs '
                          'WHERE (thread_id=? OR (thread_id IS NULL AND ts BETWEEN ? AND ?)) '
                          'AND level IN (?,?) ORDER BY id',
                          (thread, int(ended)-10, int(ended)+2, 'ERROR', 'WARN')).fetchall()
messages = []
for ts, level, target, body in rows:
    for match in re.finditer(r'"message"\s*:\s*("(?:[^"\\]|\\.)*")', body or ''):
        message = json.loads(match.group(1))
        if message.startswith('Invalid schema') and len(message) <= 3000:
            messages.append({'timestamp': ts, 'level': level, 'target': target, 'message': message})
result = {'thread_id': thread, 'diagnostic_rows_checked': len(rows), 'schema_errors': messages,
          'source': 'Native bounded diagnostic store, read-only, exact thread and WARN/ERROR filter',
          'credentials_or_rollout_files_read': False}
Path(__file__).with_name('recovered-native-error.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
