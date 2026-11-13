"""Observable documentation-tool behavior; no native CLI is needed."""
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    'project_docs', Path(__file__).resolve().parents[1] / 'scripts' / 'docs.py')
docs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(docs)


def guide(root, **changes):
    (root / 'src').mkdir(exist_ok=True)
    (root / 'src' / 'main.py').write_text('pass\n', encoding='utf-8')
    path = root / 'docs' / 'guides' / 'main.md'
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = dict(title='Main', summary='Main behavior', status='current',
                    related_files=['src/*.py'])
    metadata.update(changes)
    path.write_text('---\n' + json.dumps(metadata) + '\n---\n\n# Main\n', encoding='utf-8')
    return path


def test_build_is_repeatable_and_check_detects_stale_summary(tmp_path):
    guide(tmp_path)
    assert docs.main(['build'], tmp_path) == 0
    index = tmp_path / 'docs' / 'README.md'
    first = index.read_bytes()
    assert docs.main(['build'], tmp_path) == 0
    assert index.read_bytes() == first
    assert docs.main(['check'], tmp_path) == 0
    guide(tmp_path, summary='Changed behavior')
    assert docs.main(['check'], tmp_path) == 2
    assert index.read_bytes() == first  # check never repairs silently


def test_lookup_normalizes_windows_paths_and_accepts_deleted_paths(tmp_path):
    guide(tmp_path)
    records = docs.load(tmp_path)
    assert docs.lookup(records, ['src\\gone.py']) == {
        'src/gone.py': ['docs/guides/main.md']}


def test_unmapped_query_reports_failure_and_retains_other_matches(tmp_path, capsys):
    guide(tmp_path)
    assert docs.main(['for', 'src/main.py', 'other.py', '--json'], tmp_path) == 1
    result = json.loads(capsys.readouterr().out)
    assert result['src/main.py'] == ['docs/guides/main.md']
    assert result['other.py'] == []


@pytest.mark.parametrize('path', ['../private', '/tmp/private', 'C:\\private', '.'])
def test_query_cannot_escape_repository(tmp_path, path):
    guide(tmp_path)
    assert docs.main(['for', path], tmp_path) == 2


@pytest.mark.parametrize('changes', [
    {'related_files': ['missing/*.py']}, {'related_files': ['../private']},
    {'related_files': 'src/*.py'}, {'status': 'historical'}, {'summary': ''},
])
def test_bad_metadata_is_actionable_failure(tmp_path, changes, capsys):
    guide(tmp_path, **changes)
    assert docs.main(['build'], tmp_path) == 2
    assert capsys.readouterr().err
    assert not (tmp_path / 'docs' / 'README.md').exists()


def test_history_is_not_parsed_or_rewritten(tmp_path):
    guide(tmp_path)
    historical = tmp_path / 'docs' / 'history' / 'old.md'
    historical.parent.mkdir()
    historical.write_bytes(b'Unstructured historical evidence\r\n')
    original = historical.read_bytes()
    assert len(docs.load(tmp_path)) == 1
    assert docs.main(['build'], tmp_path) == 0
    assert historical.read_bytes() == original


def test_invalid_json_and_missing_guides_fail(tmp_path):
    assert docs.main(['build'], tmp_path) == 2
    path = guide(tmp_path)
    path.write_text('---\n{broken}\n---\n', encoding='utf-8')
    assert docs.main(['build'], tmp_path) == 2


def skill(root, name, body):
    path = root / '.agents' / 'skills' / name / 'SKILL.md'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return path


def test_build_mirrors_skills_for_claude_code_and_check_detects_drift(tmp_path, capsys):
    guide(tmp_path)
    skill(tmp_path, 'verify', b'---\nname: verify\n---\r\nBody\n')
    assert docs.main(['check'], tmp_path) == 2
    assert '.claude/skills/verify/SKILL.md' in capsys.readouterr().err
    assert docs.main(['build'], tmp_path) == 0
    mirror = tmp_path / '.claude' / 'skills' / 'verify' / 'SKILL.md'
    assert mirror.read_bytes() == b'---\nname: verify\n---\r\nBody\n'  # exact bytes
    assert docs.main(['check'], tmp_path) == 0
    mirror.write_bytes(b'edited copy\n')
    assert docs.main(['check'], tmp_path) == 2
    assert mirror.read_bytes() == b'edited copy\n'  # check never repairs silently
    assert docs.main(['build'], tmp_path) == 0
    assert docs.main(['check'], tmp_path) == 0


def test_mirror_removes_only_extras_inside_mirrored_skills(tmp_path):
    guide(tmp_path)
    skill(tmp_path, 'verify', b'Body\n')
    extra = tmp_path / '.claude' / 'skills' / 'verify' / 'old.md'
    own = tmp_path / '.claude' / 'skills' / 'claude-only' / 'SKILL.md'
    for path in (extra, own):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'x\n')
    assert docs.main(['build'], tmp_path) == 0
    assert not extra.exists()
    assert own.read_bytes() == b'x\n'
    assert docs.main(['check'], tmp_path) == 0


def test_projects_without_skills_need_no_mirror(tmp_path):
    guide(tmp_path)
    assert docs.main(['build'], tmp_path) == 0
    assert docs.main(['check'], tmp_path) == 0
    assert not (tmp_path / '.claude').exists()


def test_bootstrap_allows_reference_to_generated_index(tmp_path):
    guide(tmp_path, related_files=['src/*.py', 'docs/README.md'])
    assert docs.main(['build'], tmp_path) == 0
    assert docs.main(['check'], tmp_path) == 0


def results(root, rows):
    path = root / 'docs' / 'stage34-verification' / 'summary.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows), encoding='utf-8')


ROWS = [{'run': 'final-codex-pass', 'vendor': 'codex', 'version': 'codex 1', 'negative_control': False,
         'verdict': 'PASS', 'failures': 0, 'watcher_events': 0},
        {'run': 'final-codex-negative', 'vendor': 'codex', 'version': 'codex 1', 'negative_control': True,
         'verdict': 'FAIL', 'failures': 9, 'watcher_events': 4},
        {'run': 'dev-1', 'vendor': 'codex', 'version': 'codex 1', 'negative_control': False,
         'verdict': 'INCONCLUSIVE', 'failures': 0, 'watcher_events': 0}]


def test_readme_results_are_generated_and_drift_is_detected(tmp_path):
    guide(tmp_path)
    results(tmp_path, ROWS)
    readme = tmp_path / 'README.md'
    readme.write_text(f'# Title\n\n{docs.RESULTS_START}\nstale\n{docs.RESULTS_END}\n\nAfter.\n', encoding='utf-8')
    assert docs.main(['check'], tmp_path) == 2
    assert docs.main(['build'], tmp_path) == 0
    text = readme.read_text(encoding='utf-8')
    assert '| codex 1 | restricted worker | PASS | PASS ✅ | 0 | 0 |' in text
    assert 'negative control (canaries exposed on purpose) | FAIL | FAIL ✅ | 9 | 4 |' in text
    assert '3 recorded runs in total. The 1 development runs' in text and text.endswith('After.\n')
    assert docs.main(['check'], tmp_path) == 0
    rows = [dict(ROWS[0], verdict='FAIL'), *ROWS[1:]]
    results(tmp_path, rows)
    assert docs.main(['check'], tmp_path) == 2  # evidence changed, table did not


def test_unexpected_verdict_is_marked(tmp_path):
    results(tmp_path, [dict(ROWS[1], verdict='PASS')])
    assert 'PASS ❌' in docs.render_results(tmp_path)


def test_broken_relative_links_fail_check(tmp_path):
    guide(tmp_path)
    (tmp_path / 'README.md').write_text('[ok](src/main.py) [web](https://x.y) [anchor](#a)\n'
                                        '```\n[ignored](missing-in-code.md)\n```\n', encoding='utf-8')
    assert docs.main(['build'], tmp_path) == 0
    assert docs.main(['check'], tmp_path) == 0
    (tmp_path / 'README.md').write_text('[gone](docs/missing.md)\n', encoding='utf-8')
    assert docs.main(['check'], tmp_path) == 2
