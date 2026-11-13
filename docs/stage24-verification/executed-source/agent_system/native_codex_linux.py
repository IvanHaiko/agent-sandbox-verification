"""Native Linux Codex process boundary; no model transport or OAuth code."""
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time

from .artifacts import snapshot, digest, changed_files, artifact_diff


def native_errors(stderr):
    """Keep explicit native error diagnostics, never arbitrary role prose or logs."""
    errors = []
    lines = stderr.splitlines()
    for index, line in enumerate(lines):
        if not re.match(r'^(?:ERROR:|Error:|error:|\S+\s+ERROR\s)', line):
            continue
        prefix, separator, tail = line.partition(':')
        if separator and tail.lstrip().startswith('{'):
            payload = '\n'.join([tail.lstrip(), *lines[index + 1:]])
            try:
                value, _ = json.JSONDecoder().raw_decode(payload)
                error = value.get('error', value)
                if not isinstance(error, dict) or not isinstance(error.get('message'), str):
                    errors.append(prefix + ': <unrecognized native JSON error>')
                    continue
                safe = {key: error[key] for key in ['message', 'type', 'code', 'param']
                        if key in error and isinstance(error[key], (str, int, type(None)))}
                line = prefix + ': ' + json.dumps(safe, ensure_ascii=True)
            except (ValueError, AttributeError):
                line = prefix + ': <incomplete native JSON error>'
        line = re.sub(r'(?i)Bearer\s+\S+', 'Bearer <redacted>', line)
        line = re.sub(r'\bsk-[A-Za-z0-9_-]+', '<redacted>', line)
        line = re.sub(r'(?i)((?:access_token|refresh_token|id_token|api_key|authorization)\s*[=:]\s*)\S+',
                      r'\1<redacted>', line)
        errors.append(line[:3000])
    return errors[-8:]


def environment():
    blocked = {'OPENAI_API_KEY', 'OPENAI_BASE_URL', 'OPENAI_ORG_ID', 'OPENAI_PROJECT_ID',
        'CODEX_API_KEY', 'CODEX_ACCESS_TOKEN', 'CODEX_THREAD_ID', 'CODEX_SESSION_ID',
        'CODEX_APP_TOOLS_PIPE_PATH', 'CODEX_PERMISSION_PROFILE',
        'CODEX_INTERNAL_ORIGINATOR_OVERRIDE'}
    return {key: value for key, value in os.environ.items() if key.upper() not in blocked}


class NativeLinuxCodexRunner:
    def __init__(self):
        if os.name == 'nt':
            raise RuntimeError('This backend runs inside Linux/WSL')
        self.executable = shutil.which('codex')
        if not self.executable:
            raise RuntimeError('Native Linux Codex unavailable')
        self.runtime = Path(self.executable).resolve().parent.parent
        self.version = subprocess.run([self.executable, '--version'], capture_output=True,
            text=True, timeout=15, check=True).stdout.strip()
        login = subprocess.run([self.executable, 'login', 'status'], capture_output=True,
            text=True, timeout=15)
        if login.returncode:
            raise RuntimeError('Native Linux login required')

    def permissions(self, writable_directory=None):
        access = {'.': 'read'}
        if writable_directory:
            if Path(writable_directory).is_absolute() or '..' in Path(writable_directory).parts:
                raise RuntimeError('Invalid writable subtree')
            access[writable_directory] = 'write'
        scoped = ','.join(json.dumps(k) + '=' + json.dumps(v) for k, v in access.items())
        profile = ('{filesystem={":minimal"="read",' + json.dumps(str(self.runtime))
            + '="read",":workspace_roots"={' + scoped
            + '},":tmpdir"="deny",":slash_tmp"="deny"},network={enabled=false}}')
        return ['-c', 'default_permissions="role_workspace"', '-c', 'permissions.role_workspace=' + profile]

    def sandbox(self, workspace, command, *, writable_directory=None, timeout=30):
        argv = [self.executable, *self.permissions(writable_directory), 'sandbox',
            '--permission-profile', 'role_workspace', '--cd', str(workspace), *command]
        return self._process(argv, workspace, '', timeout)

    def _process(self, argv, workspace, prompt, timeout):
        process = subprocess.Popen(argv, cwd=workspace, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8',
            env=environment(), start_new_session=True)
        timed_out = False
        try:
            try:
                stdout, stderr = process.communicate(prompt, timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    stdout, stderr = process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    stdout, stderr = process.communicate(timeout=5)
            # A still-live descendant must not survive the launcher boundary.
            try:
                os.killpg(process.pid, 0)
            except ProcessLookupError:
                group_ended = True
            else:
                os.killpg(process.pid, signal.SIGKILL)
                group_ended = False
            return {'exit_code': process.returncode, 'stdout': stdout, 'stderr': stderr,
                    'timed_out': timed_out, 'owned_process_group_ended': group_ended}
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)

    def run(self, *, trial_id, role, workspace, target, prompt, verify,
            forbidden_reads=(), model='gpt-6.1-sol', effort='medium', timeout=240):
        workspace = Path(workspace).resolve()
        if Path(target).is_absolute() or '..' in Path(target).parts or len(Path(target).parts) < 2:
            raise RuntimeError('Artifact must be in a bounded workspace subtree')
        writable = Path(target).parent.as_posix()
        before = snapshot(workspace)
        if target not in before:
            raise RuntimeError('Controller must prepare the artifact stub')
        record = {'trial_id': trial_id, 'role': role, 'model': model, 'reasoning': effort,
            'codex_version': self.version, 'invocation_mode': 'native Linux CLI exec',
            'workspace': str(workspace), 'workspace_identity': digest(str(workspace).encode()),
            'initial_files': sorted(before), 'baseline_hashes': {k: digest(v) for k, v in before.items()},
            'prompt_sha256': digest(prompt.encode()), 'fresh_context': True, 'ephemeral': True,
            'conversation_history_inherited': False, 'thread_id': None, 'resolved_model': None,
            'execution_status': 'unrecoverable', 'failure_category': None,
            'candidate_status': 'unusable', 'permitted_artifact': target}
        probe = '''import os
from pathlib import Path
os.close(os.open(TARGET, os.O_WRONLY))
for path in ['role-input.md', 'TASK.json', '.git/config']:
    try: fd = os.open(path, os.O_WRONLY)
    except OSError: continue
    os.close(fd)
    raise RuntimeError('Read-only input unexpectedly writable')
for path in FORBIDDEN:
    try: fd = os.open(path, os.O_RDONLY)
    except OSError: continue
    os.close(fd)
    raise RuntimeError('Other role artifact unexpectedly readable')
print(Path.cwd())
'''.replace('TARGET', repr(target)).replace('FORBIDDEN', repr([str(p) for p in forbidden_reads]))
        preflight = self.sandbox(workspace, ['/usr/bin/python3', '-I', '-B', '-c', probe],
                                 writable_directory=writable)
        record['sandbox_preflight_passed'] = (preflight['exit_code'] == 0
            and preflight['stdout'].strip() == str(workspace)
            and preflight['owned_process_group_ended'] and snapshot(workspace) == before)
        if not record['sandbox_preflight_passed']:
            record['failure_category'] = 'native_sandbox_preflight'
            record['sandbox_error'] = preflight['stderr'][:1500]
            return record
        argv = self.command(workspace, model, effort, writable)
        record['command'] = argv
        started = time.monotonic()
        print(trial_id + ': ' + role + ' ' + model + '/' + effort, flush=True)
        outcome = self._process(argv, workspace, prompt, timeout)
        record.update(elapsed_seconds=round(time.monotonic() - started, 3),
            process_exit_code=outcome['exit_code'], timed_out=outcome['timed_out'],
            shutdown_confirmed=outcome['owned_process_group_ended'])
        self.metadata(record, outcome)
        # Never persist native narration, reasoning, raw tool output or auth data.
        after = snapshot(workspace)
        changed = changed_files(before, after)
        record['changed_files'] = changed
        record['mutation_scope_valid'] = changed == [target]
        record['artifact_hashes'] = {p: digest(after[p]) for p in changed if p in after}
        valid = False
        if record['mutation_scope_valid']:
            try:
                record['artifact_check'] = verify(after[target])
                valid = record['artifact_check'].get('valid') is True
            except Exception as error:
                record['artifact_check'] = {'valid': False, 'failure_type': type(error).__name__,
                                            'reason': str(error)[:500]}
        if (outcome['exit_code'] == 0 and not outcome['timed_out'] and record['shutdown_confirmed']
                and record['thread_id'] and record['resolved_model'] == model and valid):
            record['execution_status'] = 'completed'
            record['candidate_status'] = 'unaccepted' if role == 'implementer' else 'design_validated'
            record['diff'] = artifact_diff(before[target], after[target], target)
        else:
            record['failure_category'] = ('native_timeout' if outcome['timed_out'] else
                'native_execution_or_artifact_validation')
        print(trial_id + ': ' + role + ' ' + record['execution_status'], flush=True)
        return record

    def run_read_only(self, *, trial_id, role, workspace, output, prompt, verify, timeout=240):
        """Native schema-constrained semantic output; the whole role repo is read-only.

        Codex's supported --output-last-message writes Controller-owned output;
        model tools get no writable subtree, including for result files.
        """
        workspace, output = Path(workspace).resolve(), Path(output).resolve()
        if output.exists() or output.is_relative_to(workspace):
            raise RuntimeError('Read-only result must be a fresh Controller artifact')
        before = snapshot(workspace)
        record = {'trial_id': trial_id, 'role': role, 'model': 'gpt-6.1-sol', 'reasoning': 'medium',
            'codex_version': self.version, 'workspace': str(workspace),
            'workspace_identity': digest(str(workspace).encode()), 'prompt_sha256': digest(prompt.encode()),
            'fresh_context': True, 'ephemeral': True, 'conversation_history_inherited': False,
            'invocation_mode': 'native CLI exec; output-schema; output-last-message',
            'execution_status': 'unrecoverable', 'thread_id': None, 'resolved_model': None,
            'baseline_hashes': {k: digest(v) for k, v in before.items()}, 'read_only': True}
        probe = '''import os
from pathlib import Path
for path in ['role-input.md', 'TASK.json', '.git/config', 'schema.json']:
    try: fd = os.open(path, os.O_WRONLY)
    except OSError: continue
    os.close(fd)
    raise RuntimeError('Read-only role input unexpectedly writable')
print(Path.cwd())
'''
        preflight = self.sandbox(workspace, ['/usr/bin/python3', '-I', '-B', '-c', probe])
        record['sandbox_preflight_passed'] = (preflight['exit_code'] == 0 and
            preflight['stdout'].strip() == str(workspace) and preflight['owned_process_group_ended']
            and snapshot(workspace) == before)
        if not record['sandbox_preflight_passed']:
            record['failure_category'] = 'read_only_sandbox_preflight'
            return record
        argv = self.command(workspace, 'gpt-6.1-sol', 'medium')[:-1] + [
            '--output-schema', str(workspace / 'schema.json'), '--output-last-message', str(output), '-']
        record['command'] = argv
        print(trial_id + ': ' + role + ' gpt-6.1-sol/medium (read-only)', flush=True)
        started = time.monotonic()
        outcome = self._process(argv, workspace, prompt, timeout)
        record.update(elapsed_seconds=round(time.monotonic() - started, 3),
            process_exit_code=outcome['exit_code'], timed_out=outcome['timed_out'],
            shutdown_confirmed=outcome['owned_process_group_ended'])
        self.metadata(record, outcome)
        after = snapshot(workspace)
        record['changed_files'] = changed_files(before, after)
        record['mutation_scope_valid'] = not record['changed_files']
        valid = False
        if output.is_file() and not output.is_symlink() and output.stat().st_nlink == 1:
            record['artifact_sha256'] = digest(output.read_bytes())
            try:
                record['artifact_check'] = verify(output.read_bytes())
                valid = record['artifact_check'].get('valid') is True
            except Exception as error:
                record['artifact_check'] = {'valid': False, 'reason': str(error)[:500]}
        if (outcome['exit_code'] == 0 and not outcome['timed_out'] and record['shutdown_confirmed']
                and record['thread_id'] and record['resolved_model'] == 'gpt-6.1-sol'
                and record['mutation_scope_valid'] and valid):
            record['execution_status'] = 'completed'
        else:
            record['failure_category'] = 'read_only_native_execution_or_artifact_failed'
        print(trial_id + ': ' + role + ' ' + record['execution_status'], flush=True)
        return record

    def command(self, workspace, model, effort, writable=None):
        return [self.executable, '--no-daemon', '-a', 'never', 'exec', '--ignore-user-config',
            '--ephemeral', '--color', 'never', '--cd', str(workspace), '--model', model,
            '-c', 'model_reasoning_effort=' + json.dumps(effort),
            '-c', 'shell_environment_policy.inherit="core"', '-c', 'features.multi_agent=false',
            '-c', 'web_search="disabled"', *self.permissions(writable), '-']

    @staticmethod
    def metadata(record, outcome):
        if outcome['exit_code'] != 0:
            record['native_error_diagnostics'] = native_errors(outcome['stderr'])
        for name, key in (('model', 'resolved_model'), ('session id', 'thread_id'),
                          ('provider', 'provider'), ('sandbox', 'sandbox_banner')):
            match = re.search(r'^' + re.escape(name) + r':\s*(.+)$', outcome['stderr'], re.MULTILINE)
            if match:
                record[key] = match.group(1).strip()
