"""Deterministic project and artifact lifecycle, Python stdlib only."""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import uuid

NAME = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')
VERSION = re.compile(r'\d+\.\d+\.\d+\Z')
REPOSITORY = re.compile(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z')
TOOL_ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, data):
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(data, indent=2) + '\n')
    os.replace(temporary, path)


def run(*args, cwd=None):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def configuration(repo):
    data = read_json(Path(repo) / 'skill-project.json')
    if data.get('schemaVersion') != 1 or not NAME.fullmatch(data.get('name', '')):
        raise ValueError('Invalid project schema/name')
    if not VERSION.fullmatch(data.get('version', '')) or not REPOSITORY.fullmatch(data.get('repository', '')):
        raise ValueError('Invalid version/repository')
    paths = data.get('artifactPaths')
    if not isinstance(paths, list) or not paths or len(paths) != len(set(paths)):
        raise ValueError('artifactPaths must be a nonempty unique list')
    for item in paths:
        if not isinstance(item, str) or not item or '\\' in item or PurePosixPath(item).is_absolute() or any(p in ('..', '.') for p in item.split('/')):
            raise ValueError('Unsafe artifact path')
    return data


def excluded(path):
    return any(p in ('.git', '.github', '.private', 'node_modules', '__pycache__', 'dist', 'tests', 'docs', '.setup') for p in path.parts) or path.name == 'AGENTS.md' or path.suffix == '.pyc' or path.name.startswith('.env')


def artifact_files(repo, data):
    result = set()
    for relative in data['artifactPaths']:
        candidate = repo / relative
        if not candidate.exists():
            raise ValueError('Missing artifact path: ' + relative)
        for path in ([candidate] if not candidate.is_dir() else [candidate, *candidate.rglob('*')]):
            rel = path.relative_to(repo)
            if excluded(rel):
                continue
            if path.is_symlink() or not path.resolve().is_relative_to(repo.resolve()):
                raise ValueError('Artifact links are not supported: ' + str(rel))
            if path.is_file():
                result.add(rel)
    return sorted(result)


def validate(repo, installed=False):
    repo = Path(repo).resolve()
    errors = []
    try:
        data = configuration(repo)
        files = artifact_files(repo, data)
        for required in ('SKILL.md', 'skill-project.json', 'setup/SKILL.md', 'release/SKILL.md', 'setup/scripts/manage_skill_installation.py'):
            if Path(required) not in files:
                errors.append('Required distribution resource missing: ' + required)
        entry = (repo / 'SKILL.md').read_text()
        if not entry.startswith('---\n') or not re.search(r'^name: ' + re.escape(data['name']) + r'\s*$', entry, re.M):
            errors.append('Root SKILL.md frontmatter name mismatch')
        for file in files:
            if file.name == 'SKILL.md':
                text = (repo / file).read_text()
                if not re.search(r'^description:\s*\S', text, re.M):
                    errors.append('Missing description: ' + str(file))
                if '/Users/' in text or '/home/' in text:
                    errors.append('Author-machine path in consumer instructions: ' + str(file))
                for link in re.findall(r'\]\(([^)]+)\)', text):
                    if '://' not in link and not link.startswith('#'):
                        linked = (repo / file.parent / link.split('#')[0]).resolve()
                        if not linked.is_relative_to(repo) or not linked.exists():
                            errors.append('Broken/local escape link: ' + str(file) + ': ' + link)
                if not installed and file.parent != Path('.') and not (repo / file.parent / 'AGENTS.md').exists():
                    errors.append('Module development guide missing: ' + str(file.parent))
            if file.suffix in ('.py', '.sh', '.mjs', '.ps1') and 'scripts' in file.parts and len(file.stem.split('_')) < 3:
                errors.append('Script name needs full action/object: ' + str(file))
        if not installed and not (repo / 'AGENTS.md').exists():
            errors.append('Root AGENTS.md missing')
    except (ValueError, OSError, KeyError, TypeError) as error:
        errors.append(str(error))
    return {'ready': not errors, 'errors': errors}


def require_valid(repo, installed=False):
    result = validate(repo, installed)
    if not result['ready']:
        raise ValueError('; '.join(result['errors']))


def build(repo):
    repo = Path(repo).resolve()
    require_valid(repo)
    if run('git', 'status', '--porcelain', '--untracked-files=all', cwd=repo):
        raise ValueError('Commit a clean source tree before building')
    data = configuration(repo)
    commit = run('git', 'rev-parse', 'HEAD', cwd=repo)
    tag = subprocess.run(['git', 'rev-parse', '--verify', 'refs/tags/v' + data['version'] + '^{commit}'], cwd=repo, capture_output=True, text=True)
    if tag.returncode == 0 and tag.stdout.strip() != commit:
        raise ValueError('Version tag already identifies different source')
    dist = repo / 'dist'
    dist.mkdir(exist_ok=True)
    archive = dist / f"{data['name']}-{data['version']}.tgz"
    if archive.exists():
        prior = read_json(dist / f"{data['name']}-release.json")
        if prior.get('sourceCommit') != commit or prior.get('sha256') != hashlib.sha256(archive.read_bytes()).hexdigest():
            raise ValueError('Existing version artifact differs; increment version')
        return prior
    with tarfile.open(archive, 'w:gz') as bundle:
        for relative in artifact_files(repo, data):
            info = bundle.gettarinfo(str(repo / relative), arcname='package/' + relative.as_posix())
            info.uid = info.gid = 0
            info.uname = info.gname = ''
            info.mtime = 0
            with (repo / relative).open('rb') as stream:
                bundle.addfile(info, stream)
    manifest = {'schemaVersion': 1, 'name': data['name'], 'version': data['version'], 'repository': data['repository'], 'sourceCommit': commit, 'asset': archive.name, 'size': archive.stat().st_size, 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}
    write_json(dist / f"{data['name']}-release.json", manifest)
    return manifest


def verify_archive(archive, manifest):
    m = read_json(manifest)
    if m.get('schemaVersion') != 1 or not NAME.fullmatch(m.get('name', '')) or not VERSION.fullmatch(m.get('version', '')) or not REPOSITORY.fullmatch(m.get('repository', '')):
        raise ValueError('Invalid manifest identity')
    if not re.fullmatch(r'[a-f0-9]{40}', m.get('sourceCommit', '')) or not re.fullmatch(r'[a-f0-9]{64}', m.get('sha256', '')):
        raise ValueError('Invalid manifest digest/commit')
    if m.get('asset') != f"{m['name']}-{m['version']}.tgz" or not isinstance(m.get('size'), int) or not 0 < m['size'] <= 100_000_000:
        raise ValueError('Invalid archive size/name')
    path = Path(archive)
    if path.stat().st_size != m['size'] or hashlib.sha256(path.read_bytes()).hexdigest() != m['sha256']:
        raise ValueError('Archive size/SHA-256 mismatch')
    return m


def extract_archive(archive, destination):
    # Preflight every entry before writing anything; no links, devices or traversal.
    with tarfile.open(archive, 'r:gz') as bundle:
        names = set()
        total = 0
        members = bundle.getmembers()
        if len(members) > 10000:
            raise ValueError('Too many archive members')
        for member in members:
            parts = member.name.split('/')
            if '\\' in member.name or parts[0] != 'package' or '..' in parts or not (member.isfile() or member.isdir()) or member.name in names:
                raise ValueError('Unsafe archive member')
            names.add(member.name)
            total += member.size
            if total > 200_000_000:
                raise ValueError('Expanded archive exceeds limit')
        for member in members:
            output = destination / member.name
            if not output.resolve().is_relative_to(destination.resolve()):
                raise ValueError('Archive path escapes staging')
            if member.isdir():
                output.mkdir(parents=True, exist_ok=True)
            else:
                output.parent.mkdir(parents=True, exist_ok=True)
                with bundle.extractfile(member) as stream, output.open('wb') as sink:
                    shutil.copyfileobj(stream, sink)
                output.chmod(0o755 if member.mode & 0o111 else 0o644)


@contextlib.contextmanager
def installation_lock(store):
    lock = store / '.installation-lock'
    try:
        lock.mkdir()
    except FileExistsError:
        raise ValueError('Installation lock exists; inspect running installer before removing stale lock')
    try:
        yield
    finally:
        lock.rmdir()


def check_owner(target, store, name):
    receipt_path = store / 'receipt.json'
    receipt = read_json(receipt_path) if receipt_path.exists() else None
    if receipt and (not re.fullmatch(r'versions/[0-9.]+-[a-f0-9]{64}', receipt.get('active', '')) or (receipt.get('previous') is not None and not re.fullmatch(r'versions/[0-9.]+-[a-f0-9]{64}', receipt['previous']))):
        raise ValueError('Invalid receipt version path')
    if receipt and (receipt.get('target') != str(target) or receipt.get('name') != name):
        raise ValueError('Store belongs to a different target/product')
    if target.exists() or target.is_symlink():
        if not receipt or not target.is_symlink() or target.resolve() != (store / receipt['active']).resolve():
            raise ValueError('Refusing to replace unmanaged target')
    return receipt


def activate_link(target, version):
    target.parent.mkdir(parents=True, exist_ok=True)
    # Unique sibling for atomic replacement, without deleting unknown files.
    temporary = target.parent / ('.' + target.name + '-activation-' + uuid.uuid4().hex)
    try:
        temporary.symlink_to(version, target_is_directory=True)
        os.replace(temporary, target)
    finally:
        if temporary.is_symlink():
            temporary.unlink()


def install(archive, manifest, target, store):
    if os.name != 'posix':
        raise ValueError('Managed activation currently supports macOS/Linux only')
    target = Path(os.path.abspath(os.path.expanduser(str(target))))
    store = Path(store).expanduser().resolve()
    m = verify_archive(archive, manifest)
    if target.name != m['name'] or store == target or store.is_relative_to(target) or target.is_relative_to(store):
        raise ValueError('Target name must match product; store must be outside target')
    store.mkdir(parents=True, exist_ok=True)
    with installation_lock(store):
        prior = check_owner(target, store, m['name'])
        version_relative = f"versions/{m['version']}-{m['sha256']}"
        version = store / version_relative
        with tempfile.TemporaryDirectory(prefix='staging-', dir=store) as tmp:
            stage = Path(tmp)
            extract_archive(archive, stage)
            package = stage / 'package'
            require_valid(package, installed=True)
            data = configuration(package)
            if any(data[key] != m[key] for key in ('name', 'version', 'repository')):
                raise ValueError('Package and manifest identity differ')
            if version.exists():
                # Existing immutable directory must still match every packaged byte.
                expected = {p.relative_to(package): p.read_bytes() for p in package.rglob('*') if p.is_file()}
                actual = {p.relative_to(version): p.read_bytes() for p in version.rglob('*') if p.is_file() and not p.is_symlink()}
                if expected != actual or any(p.is_symlink() for p in version.rglob('*')):
                    raise ValueError('Existing immutable installation was modified')
            else:
                version.parent.mkdir(exist_ok=True)
                os.replace(package, version)
        # Keep receipt/link consistent on synchronous failures; check reports interruptions.
        receipt = {'schemaVersion': 1, 'name': m['name'], 'target': str(target), 'active': version_relative, 'previous': prior.get('active') if prior and prior.get('active') != version_relative else prior.get('previous') if prior else None, 'manifest': m}
        activate_link(target, version)
        try:
            write_json(store / 'receipt.json', receipt)
        except BaseException:
            if prior:
                activate_link(target, store / prior['active'])
            else:
                target.unlink()
            raise
        return {'installed': True, 'version': m['version'], 'target': str(target), 'sha256': m['sha256']}


def rollback(target, store):
    target = Path(os.path.abspath(os.path.expanduser(str(target))))
    store = Path(store).expanduser().resolve()
    with installation_lock(store):
        receipt = read_json(store / 'receipt.json')
        check_owner(target, store, receipt['name'])
        previous = receipt.get('previous')
        if not previous or not (store / previous).is_dir():
            raise ValueError('No prior installed version')
        require_valid(store / previous, installed=True)
        original = dict(receipt)
        receipt['active'], receipt['previous'] = previous, receipt['active']
        receipt['manifest'] = None  # Current version resolved from installed configuration.
        activate_link(target, store / previous)
        try:
            write_json(store / 'receipt.json', receipt)
        except BaseException:
            activate_link(target, store / original['active'])
            raise
        return {'rolledBack': True, 'version': configuration(target)['version']}


def fetch(url, output, binary=False):
    args = ['curl', '--fail', '--location', '--silent', '--show-error', '--retry', '2', '--connect-timeout', '15', '--max-time', '60', '--max-filesize', '100000000', '--proto', '=https', '--proto-redir', '=https', '-H', 'Accept: ' + ('application/octet-stream' if binary else 'application/vnd.github+json'), '-H', 'User-Agent: awesome-skill-maker', url, '-o', str(output)]
    subprocess.run(args, check=True)


def upgrade(repository, target, store):
    if not REPOSITORY.fullmatch(repository):
        raise ValueError('Invalid repository')
    name = Path(target).name
    with tempfile.TemporaryDirectory(prefix='skill-github-') as tmp:
        tmp = Path(tmp)
        base = 'https://api.github.com/repos/' + repository
        fetch(base + '/releases/latest', tmp / 'release.json')
        release = read_json(tmp / 'release.json')
        tag = release['tag_name']
        if not re.fullmatch(r'v\d+\.\d+\.\d+', tag):
            raise ValueError('Invalid release tag')
        def asset_url(filename):
            matches = [a for a in release['assets'] if a['name'] == filename]
            if len(matches) != 1 or not re.fullmatch(re.escape(base) + r'/releases/assets/\d+', matches[0]['url']):
                raise ValueError('Missing or unexpected release asset')
            return matches[0]['url']
        fetch(asset_url(name + '-release.json'), tmp / 'manifest.json', True)
        manifest = read_json(tmp / 'manifest.json')
        if manifest.get('repository') != repository or manifest.get('name') != name or manifest.get('version') != tag[1:]:
            raise ValueError('Release identity mismatch')
        fetch(base + '/git/ref/tags/' + tag, tmp / 'tag.json')
        obj = read_json(tmp / 'tag.json')['object']
        for depth in range(4):
            if obj['type'] == 'commit':
                break
            if obj['type'] != 'tag' or not re.fullmatch(r'[a-f0-9]{40}', obj['sha']):
                raise ValueError('Unsupported tag object')
            fetch(base + '/git/tags/' + obj['sha'], tmp / 'tag-object.json')
            obj = read_json(tmp / 'tag-object.json')['object']
        if obj['type'] != 'commit' or obj['sha'] != manifest.get('sourceCommit'):
            raise ValueError('Release source commit mismatch')
        if Path(target).exists():
            current = configuration(Path(target))
            if current['repository'] != repository:
                raise ValueError('Installed repository mismatch')
            if tuple(map(int, manifest['version'].split('.'))) <= tuple(map(int, current['version'].split('.'))):
                return {'updated': False, 'version': current['version']}
        fetch(asset_url(f"{name}-{tag[1:]}.tgz"), tmp / 'release.tgz', True)
        return install(tmp / 'release.tgz', tmp / 'manifest.json', target, store)


def initialize(destination, name, repository, description):
    if not NAME.fullmatch(name) or len(name) > 64 or not REPOSITORY.fullmatch(repository) or not description.strip() or '\n' in description:
        raise ValueError('Provide valid name, repository and one-line description')
    destination = Path(destination).expanduser().absolute()
    if destination.exists():
        raise ValueError('Destination already exists; existing projects need explicit adaptation')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='skill-project-', dir=destination.parent) as tmp:
        stage = Path(tmp) / 'project'
        stage.mkdir()
        for relative in ['setup', 'release', 'utils']:
            shutil.copytree(TOOL_ROOT / relative, stage / relative, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'AGENTS.md'))
        for relative in ['LICENSE']:
            shutil.copy2(TOOL_ROOT / relative, stage / relative)
        (stage / 'SKILL.md').write_text('---\nname: ' + name + '\ndescription: ' + json.dumps(description, ensure_ascii=False) + '\n---\n# ' + name + '\n\n' + description + '\n\n首次使用或环境故障读取 [setup/SKILL.md](setup/SKILL.md)；构建分发读取 [release/SKILL.md](release/SKILL.md)。\n\n本骨架当前只实现安装与分发，业务模块需实现并验证后再加入导航。\n')
        (stage / 'README.md').write_text('# ' + name + '\n\n源码使用 GitHub ' + repository + '；消费使用对应 Release 制品。当前骨架只实现 setup/release，业务模块待开发。\n\n构建：`python3 release/scripts/build_skill_artifact.py --repo .`（先提交干净 Git HEAD）。\n\n安装：从同一 Release 取得 tgz 与 manifest，执行 `python3 setup/bootstrap_skill_installation.py --archive <archive> --manifest <manifest> --target <agent-skills>/' + name + ' --store <external-store>`。bootstrap 必须来自可信 tag。\n\n验证：`python3 -m unittest discover -s tests`。\n')
        (stage / 'AGENTS.md').write_text('# Development\n\nRead docs/skill-authoring.md. Keep consumer SKILL.md and development AGENTS.md separate. Add actual business modules and verification before advertising capabilities. Installed tools must never import this checkout. Source and releases use GitHub. For ongoing Skill engineering, use the independently installed Awesome Skill Maker release artifact and read its SKILL.md; never import its development checkout. Acquire verified artifacts from https://github.com/kwgjjeffrey/awesome-skill-maker/releases when unavailable.\n')
        for module in ['setup', 'release']:
            module_skill = stage / module / 'SKILL.md'
            module_skill.write_text(module_skill.read_text().replace('name: awesome-skill-maker-', 'name: ' + name + '-'))
            (stage / module / 'AGENTS.md').write_text('# Module development\n\nFollow root AGENTS.md. Lifecycle logic is shared through utils. Verify staged artifacts and preserve external state.\n')
        (stage / 'docs').mkdir()
        # Authoring conventions are embedded in the artifact so scaffolding is checkout-independent.
        shutil.copy2(TOOL_ROOT / 'project' / 'skill-authoring.md', stage / 'docs' / 'skill-authoring.md')
        (stage / '.gitignore').write_text('dist/\n__pycache__/\n*.pyc\n.private/\n')
        write_json(stage / 'skill-project.json', {'schemaVersion': 1, 'name': name, 'version': '0.1.0', 'repository': repository, 'artifactPaths': ['SKILL.md', 'skill-project.json', 'LICENSE', 'setup', 'release', 'utils']})
        (stage / 'tests').mkdir()
        (stage / 'tests' / 'test_artifact_lifecycle.py').write_text((TOOL_ROOT / 'project' / 'test_artifact_lifecycle_template.py').read_text())
        workflows = stage / '.github' / 'workflows'
        workflows.mkdir(parents=True)
        (workflows / 'validate-skill-project.yml').write_text('name: Validate skill project\non: [push, pull_request]\njobs:\n  validate:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-python@v5\n        with:\n          python-version: "3.10"\n      - run: python3 -m unittest discover -s tests\n')
        require_valid(stage)
        os.replace(stage, destination)
    return {'created': str(destination), 'name': name, 'businessModulesImplemented': False}


def publish(repo):
    repo = Path(repo).resolve()
    data = configuration(repo)
    origin = run('git', 'remote', 'get-url', 'origin', cwd=repo)
    if origin not in ('https://github.com/' + data['repository'] + '.git', 'git@github.com:' + data['repository'] + '.git', 'https://github.com/' + data['repository']):
        raise ValueError('origin does not match configured GitHub repository')
    subprocess.run(['gh', 'auth', 'status'], check=True, stdout=subprocess.DEVNULL)
    m = build(repo)
    remote = json.loads(run('gh', 'api', 'repos/' + data['repository'] + '/git/ref/heads/main'))
    if remote['object']['sha'] != m['sourceCommit']:
        raise ValueError('Push source to origin/main before publishing')
    tag = 'v' + m['version']
    existing = subprocess.run(['gh', 'release', 'view', tag, '--repo', data['repository']], capture_output=True)
    if existing.returncode == 0:
        raise ValueError('Release already exists; never overwrite a version')
    dist = repo / 'dist'
    subprocess.run(['gh', 'release', 'create', tag, '--repo', data['repository'], '--target', m['sourceCommit'], '--draft', '--title', tag, '--notes', 'Modular Skill artifact; manifest binds source commit, size and SHA-256.', str(dist / m['asset']), str(dist / (m['name'] + '-release.json'))], check=True)
    with tempfile.TemporaryDirectory(prefix='skill-release-readback-') as tmp:
        subprocess.run(['gh', 'release', 'download', tag, '--repo', data['repository'], '--dir', tmp], check=True)
        if read_json(Path(tmp) / (m['name'] + '-release.json')) != m:
            raise ValueError('Published manifest differs; draft retained')
        verify_archive(Path(tmp) / m['asset'], Path(tmp) / (m['name'] + '-release.json'))
    subprocess.run(['gh', 'release', 'edit', tag, '--repo', data['repository'], '--draft=false'], check=True)
    return {'published': 'https://github.com/' + data['repository'] + '/releases/tag/' + tag}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    init = commands.add_parser('initialize')
    for key in ('destination', 'name', 'repository', 'description'):
        init.add_argument('--' + key, required=True)
    for command in ('validate', 'build', 'publish'):
        commands.add_parser(command).add_argument('--repo', required=True)
    setup = commands.add_parser('setup').add_subparsers(dest='action', required=True)
    check = setup.add_parser('check')
    check.add_argument('--target')
    for action in ('install', 'upgrade', 'rollback'):
        sub = setup.add_parser(action)
        sub.add_argument('--target', required=True)
        sub.add_argument('--store', required=True)
        if action == 'install':
            sub.add_argument('--archive', required=True)
            sub.add_argument('--manifest', required=True)
        if action == 'upgrade':
            sub.add_argument('--repository', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'initialize':
            result = initialize(args.destination, args.name, args.repository, args.description)
        elif args.command == 'validate':
            result = validate(args.repo)
        elif args.command == 'build':
            result = build(args.repo)
        elif args.command == 'publish':
            result = publish(args.repo)
        elif args.action == 'install':
            result = install(args.archive, args.manifest, args.target, args.store)
        elif args.action == 'rollback':
            result = rollback(args.target, args.store)
        elif args.action == 'upgrade':
            result = upgrade(args.repository, args.target, args.store)
        else:
            result = {'ready': sys.version_info >= (3, 9) and os.name == 'posix' and shutil.which('curl') is not None, 'python': sys.version.split()[0], 'platform': sys.platform, 'curl': bool(shutil.which('curl'))}
            if args.target:
                require_valid(args.target, installed=True)
                target = Path(args.target).expanduser()
                if not target.is_symlink() or target.resolve().parent.name != 'versions':
                    raise ValueError('Target is not a managed installed link')
                store = target.resolve().parent.parent
                receipt = check_owner(Path(os.path.abspath(target)), store, configuration(target)['name'])
                result.update(version=configuration(target)['version'], receipt=receipt)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if result.get('ready') is False:
            sys.exit(1)
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError, tarfile.TarError) as error:
        print(json.dumps({'ready': False, 'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
