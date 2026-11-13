"""Narrow Linux CLI permissions and owned process lifetime; no role scheduling."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess


def environment():
    blocked = {'OPENAI_API_KEY', 'OPENAI_BASE_URL', 'OPENAI_ORG_ID', 'OPENAI_PROJECT_ID',
               'CODEX_API_KEY', 'CODEX_ACCESS_TOKEN', 'CODEX_THREAD_ID', 'CODEX_SESSION_ID',
               'CODEX_APP_TOOLS_PIPE_PATH', 'CODEX_PERMISSION_PROFILE',
               'CODEX_INTERNAL_ORIGINATOR_OVERRIDE', 'PYTHONPATH', 'PYTHONHOME',
               # A Claude Code parent must not pass its own credentials or routing to workers.
               'ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'ANTHROPIC_BASE_URL',
               'CLAUDE_CODE_OAUTH_TOKEN'}
    return {k: v for k, v in os.environ.items() if k.upper() not in blocked}


# Agent workers start from an empty environment plus these names (allow-list), so
# parent credentials, cloud keys, SSH agents and WSL interop handles never reach them.
WORKER_ENV = ('PATH', 'HOME', 'USER', 'LOGNAME', 'SHELL', 'LANG', 'LANGUAGE', 'LC_ALL',
              'LC_CTYPE', 'TERM', 'TZ')


def worker_env(**extra):
    """`env -i NAME=value ...` prefix for a worker launch; extra values are set verbatim."""
    values = {k: os.environ[k] for k in WORKER_ENV if k in os.environ}
    values.update(extra)
    return ['/usr/bin/env', '-i', *(f'{k}={v}' for k, v in values.items())]


def process(argv, workspace, *, prompt='', timeout=180):
    """Capture actual exit/timeout and kill descendants in this owned process group."""
    if os.name != 'posix':
        raise RuntimeError('Restricted execution requires Linux/WSL')
    child = subprocess.Popen([str(a) for a in argv], cwd=workspace, env=environment(),
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, encoding='utf-8', errors='replace', start_new_session=True)
    timed_out = False
    forced = False
    try:
        try:
            stdout, stderr = child.communicate(prompt, timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(child.pid, signal.SIGTERM)
            try:
                stdout, stderr = child.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                stdout, stderr = child.communicate(timeout=5)
        try:
            os.killpg(child.pid, 0)
        except ProcessLookupError:
            ended = True
        else:
            os.killpg(child.pid, signal.SIGKILL)
            forced, ended = True, False
        return {'exit_code': child.returncode, 'timed_out': timed_out,
                'owned_process_group_ended': ended, 'descendants_killed': forced,
                'stdout': stdout, 'stderr': stderr}
    finally:
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait(timeout=5)


def permissions(*, writable=(), read_paths=(), database_socket=None):
    """Installed native named profile. Probe it before launching strict roles."""
    executable = shutil.which('codex')
    if not executable or os.name != 'posix':
        raise RuntimeError('Installed Linux Codex required; no fallback')
    runtime = Path(executable).resolve().parent.parent
    access = {'.': 'read'}
    for name in writable:
        p = Path(name)
        if p.is_absolute() or '..' in p.parts or name in ('', '.'):
            raise ValueError('Writable access must name a bounded subtree')
        access[p.as_posix()] = 'write'
    reads = {':minimal': 'read', str(runtime): 'read'}
    for path in read_paths:
        reads[str(Path(path).resolve(strict=True))] = 'read'
    network = 'enabled=false'
    if database_socket is not None:
        socket = Path(database_socket).resolve(strict=True)
        if (not socket.is_dir() or socket.name != 'socket' or
                socket.parent.parent != Path.home().resolve() or
                not (socket.parent / '.codex-owned').is_file()):
            raise ValueError('Database socket must be in an owned private workspace')
        reads[str(socket)] = 'read'
        # CLI 0.160.1 needs AF_UNIX creation enabled. A separate network namespace
        # prevents TCP access; filesystem policy exposes only this socket path.
        network = 'enabled=true,mode="limited",domains={},dangerously_allow_all_unix_sockets=true'
    entries = ','.join(json.dumps(k) + '=' + json.dumps(v) for k, v in reads.items())
    scoped = ','.join(json.dumps(k) + '=' + json.dumps(v) for k, v in access.items())
    profile = ('{filesystem={' + entries + ',":workspace_roots"={' + scoped +
               '},":tmpdir"="deny",":slash_tmp"="deny"},network={' + network + '}}')
    args = ['-c', 'default_permissions="bounded"', '-c', 'permissions.bounded=' + profile]
    if database_socket is not None:
        args += ['-c', 'features.network_proxy=true']
    return args


def sandbox(workspace, argv, *, writable=(), read_paths=(), database_socket=None, timeout=180):
    namespace = ['/usr/bin/unshare', '--user', '--map-root-user', '--net'] if database_socket else []
    return process([*worker_env(), *namespace, shutil.which('codex'),
                    *permissions(writable=writable, read_paths=read_paths, database_socket=database_socket),
                    'sandbox', '--permission-profile', 'bounded', '--cd', str(workspace), *argv],
                   workspace, timeout=timeout)


def command(workspace, *, writable=(), read_paths=(), output=None, model=None):
    """Native exec owns auth/model/settings and structured events, never a wrapper role."""
    argv = [*worker_env(), shutil.which('codex'), '--no-daemon', '-a', 'never', 'exec',
            '--ignore-user-config',
            '--ephemeral', '--json', '--color', 'never', '--skip-git-repo-check', '--cd', str(workspace),
            '-c', 'shell_environment_policy.inherit="core"', '-c', 'features.multi_agent=false',
            '-c', 'web_search="disabled"', *permissions(writable=writable, read_paths=read_paths)]
    if model is not None:
        argv += ['--model', str(model)]
    if output is not None:
        output = Path(output).absolute()
        if output.exists() or output.is_relative_to(Path(workspace).resolve()):
            raise ValueError('Last-message output must be fresh and outside worker inputs')
        argv += ['--output-last-message', str(output)]
    return [*argv, '-']


def _bounded(workspace, writable):
    root = Path(workspace).resolve(strict=True)
    paths = []
    for name in writable:
        p = Path(name)
        if (p.is_absolute() or p.drive or name.startswith(('/', '\\'))
                or '..' in p.parts or name in ('', '.')):
            raise ValueError('Writable access must name a bounded subtree')
        path = root / p
        if path.is_symlink() or (path.exists() and not path.is_dir()):
            raise ValueError('Writable subtree must be a real directory, not a link or file')
        paths.append(path)
    return root, paths


# Claude Code's sandbox mounts over these names in the working directory. With a
# read-only workspace root, bwrap cannot create the mount points itself, so every
# Bash call fails (closed). Observed with 2.1.323; a newer list fails the same way.
CLAUDE_PLACEHOLDERS = ('.gitconfig', '.gitmodules', '.bashrc', '.bash_profile', '.zshrc',
                       '.zprofile', '.profile', '.ripgreprc', '.vscode', '.idea')


def claude_prepare(workspace):
    """Create empty placeholders; call before taking the acceptance baseline."""
    root = Path(workspace).resolve(strict=True)
    for name in CLAUDE_PLACEHOLDERS:
        path = root / name
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ValueError(f'Placeholder path is not a regular file: {name}')
        if not path.exists():
            path.write_bytes(b'')
    return [name for name in CLAUDE_PLACEHOLDERS]


def claude_settings(workspace, *, writable=(), read_paths=()):
    """Session-only Claude Code settings: OS sandbox for shell commands, rules for file tools.

    File tools run outside the OS sandbox, so they are confined by --restricted and
    dontAsk (anything not allowed here is denied without a prompt). Denies in launcher
    settings cannot be loosened by project files a worker might write.
    """
    root, writes = _bounded(workspace, writable)
    home = Path.home().resolve()
    reads = [root, *(Path(p).resolve(strict=True) for p in read_paths)]
    rule = lambda tool, path, tail='/**': f'{tool}(/{path.as_posix()}{tail})'
    # No bare Glob/Grep allow: Read rules scope them, and anything else is denied by dontAsk.
    allow = ['Bash', *(rule('Read', p) for p in reads)]
    allow += [rule('Edit', path) for path in writes]  # Edit rules also govern Write
    protected = [home / '.claude', home / '.codex', root / '.claude', root / '.codex', Path('/mnt')]
    deny = [rule(t, p) for p in protected for t in ('Read', 'Edit')]
    deny += [rule(t, home / '.claude.json', '') for t in ('Read', 'Edit')]
    return {
        'permissions': {'defaultMode': 'dontAsk', 'allow': allow, 'deny': deny,
                        'blockReadsOutsideWorkingDirectories': True,
                        'disableBypassPermissionsMode': 'disable'},
        'sandbox': {
            'enabled': True, 'failIfUnavailable': True, 'allowUnsandboxedCommands': False,
            'autoAllowBashIfSandboxed': True, 'excludedCommands': [],
            'network': {'allowedDomains': [], 'allowUnixSockets': [], 'allowAllUnixSockets': False},
            # /mnt holds WSL's Windows drives (Windows-side credentials, interop binaries).
            # No denyWrite on the root: it would mount over allowWrite subtrees. The outer
            # fence (claude_fence) makes the root read-only and only the subtrees writable.
            'filesystem': {'denyRead': [str(home), '/tmp', '/mnt'], 'allowRead': [str(p) for p in reads],
                           'allowWrite': [str(p) for p in writes]},
        },
    }


def claude_fence(workspace, *, writable=(), read_paths=()):
    """Outer bubblewrap mount namespace around the whole Claude Code process.

    Claude's file tools run outside its own sandbox, so the kernel boundary must
    enclose the process itself: everything read-only, $HOME replaced by an empty
    tmpfs except the login state and the binary, the workspace read-only with only
    the writable subtrees bound read-write, private /tmp, no /mnt (WSL Windows
    drives) or WSL interop/user sockets, and a separate PID namespace.
    """
    bwrap = shutil.which('bwrap')
    executable = shutil.which('claude')
    if not bwrap or not executable or os.name != 'posix':
        raise RuntimeError('Linux bubblewrap and Claude Code required; no fallback')
    root, writes = _bounded(workspace, writable)
    home = Path.home().resolve()
    binary = Path(executable).resolve(strict=True)
    argv = [bwrap, '--die-with-parent', '--unshare-pid', '--ro-bind', '/', '/', '--dev', '/dev',
            '--proc', '/proc', '--tmpfs', '/tmp', '--tmpfs', str(home)]
    hidden = [path for path in ('/mnt', '/run/WSL', '/run/user') if Path(path).is_dir()]
    for path in hidden:
        argv += ['--tmpfs', path]
    # WSL links /etc/resolv.conf into /mnt/wsl; restore only that file, read-only.
    resolver = Path('/etc/resolv.conf').resolve()
    if resolver.is_file() and any(resolver.is_relative_to(path) for path in hidden):
        argv += ['--ro-bind', str(resolver), str(resolver)]
    state = [home / '.claude', home / '.claude.json']
    argv += [arg for path in state if path.exists() for arg in ('--bind', str(path), str(path))]
    argv += ['--ro-bind', str(binary), str(binary), '--ro-bind', str(root), str(root)]
    for path in read_paths:
        real = str(Path(path).resolve(strict=True))
        argv += ['--ro-bind', real, real]
    for path in writes:
        argv += ['--bind', str(path), str(path)]
    return [*argv, '--chdir', str(root), '--', str(binary)]


def claude_command(workspace, *, writable=(), read_paths=(), model=None):
    """Headless Claude Code worker; the prompt is read from stdin. Linux/WSL only.

    The CLI's own stored login authenticates it; the worker gets only WORKER_ENV.
    """
    executable = shutil.which('claude')
    if not executable or os.name != 'posix':
        raise RuntimeError('Installed Linux Claude Code required; no fallback')
    root = Path(workspace).resolve(strict=True)
    missing = [n for n in CLAUDE_PLACEHOLDERS if not (root / n).is_file() or (root / n).is_symlink()]
    if missing:
        raise ValueError('Call claude_prepare(workspace) before the baseline; missing ' + repr(missing))
    tools = ['Read', 'Glob', 'Grep', 'Bash'] + (['Write', 'Edit'] if writable else [])
    settings = claude_settings(workspace, writable=writable, read_paths=read_paths)
    fence = claude_fence(workspace, writable=writable, read_paths=read_paths)
    argv = [*worker_env(CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC='1'), *fence, '-p',
            '--restricted', '--tools', ','.join(tools), '--strict-mcp-config',
            '--settings', json.dumps(settings), '--permission-mode', 'dontAsk',
            '--permission-prompts', 'none', '--no-session-persistence', '--disable-slash-commands',
            '--output-format', 'stream-json', '--verbose']
    for path in read_paths:
        argv += ['--add-dir', str(Path(path).resolve(strict=True))]
    if model is not None:
        argv += ['--model', str(model)]
    return argv
