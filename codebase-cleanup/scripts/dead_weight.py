#!/usr/bin/env python3
"""List dead-weight candidates in a git repo. Read-only; every hit is a lead to prove, not a verdict.

  dead_weight.py [REPO]            human-readable report
  dead_weight.py [REPO] --json     same, as JSON

Checks:
  empty-dir          folders that are empty or hold only placeholders (.gitkeep, .DS_Store, empty __init__.py)
  empty-file         tracked files with no content beyond whitespace and comments
  orphan-file        tracked source files whose name no other tracked file mentions
  noop-function      functions whose body does nothing (Python via ast; JS/TS by pattern)
  missing-path       paths in package.json scripts and backticked paths in Markdown that don't exist

Orphan and no-op hits are noisy by design: entry points, plugins and deliberate no-op defaults show
up too. Prove each one dead (references/dead-weight.md) before removing it.
"""
import ast, json, os, re, subprocess, sys

SKIP_DIRS = {'.git', 'node_modules', '.venv', 'venv', '__pycache__', 'dist', 'build', '.next',
             'coverage', 'target', '.turbo', '.cache', 'vendor', '.idea', '.vscode'}
PLACEHOLDERS = {'.gitkeep', '.keep', '.DS_Store', '.gitignore'}
SOURCE_EXT = {'.py', '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs', '.go', '.rb', '.rs', '.java',
              '.kt', '.cs', '.php', '.css', '.scss', '.sh'}
ENTRY_STEMS = {'index', 'main', '__init__', '__main__', 'app', 'server', 'setup', 'conftest',
               'manage', 'wsgi', 'asgi', 'cli', 'mod', 'lib', 'build', 'vite.config', 'jest.config',
               'vitest.config', 'playwright.config', 'eslint.config', 'tailwind.config', 'postcss.config'}
TEXT_EXT = SOURCE_EXT | {'.md', '.json', '.yaml', '.yml', '.toml', '.html', '.txt', '.cfg', '.ini',
                         '.mdx', '.vue', '.svelte', '.sql', '.xml', '.tf', '.env', '.example'}
COMMENT_LINE = re.compile(r'^\s*(#|//|/\*|\*|\*/|<!--|-->|--|;)')
JS_NOOP = re.compile(
    r'(?:function\s*\*?\s*([A-Za-z_$][\w$]*)\s*\([^)]*\)|'
    r'(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>|'
    r'^\s*(?:async\s+)?([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*(?::\s*[\w<>\[\]| ]+)?)\s*\{\s*(?:return\s*;?\s*)?\}',
    re.M)
JS_KEYWORDS = {'if', 'for', 'while', 'switch', 'catch', 'function', 'return', 'constructor'}


def tracked(repo):
    out = subprocess.run(['git', '-C', repo, 'ls-files', '-z'], capture_output=True, text=True, check=True)
    return [p for p in out.stdout.split('\0') if p]


def read(repo, rel):
    try:
        with open(os.path.join(repo, rel), encoding='utf-8') as f:
            return f.read()
    except (UnicodeDecodeError, OSError):
        return None


def empty_dirs(repo):
    hits = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        if root == repo:
            continue
        real = [f for f in files if f not in PLACEHOLDERS
                and not (f == '__init__.py' and os.path.getsize(os.path.join(root, f)) == 0)]
        if not real and not dirs:
            hits.append({'path': os.path.relpath(root, repo),
                         'detail': 'empty' if not files else 'only ' + ', '.join(sorted(files))})
    return hits


def empty_files(repo, files):
    hits = []
    for rel in files:
        if os.path.basename(rel) in PLACEHOLDERS or os.path.basename(rel) == '__init__.py':
            continue
        text = read(repo, rel)
        if text is None:
            continue
        if all(not line.strip() or COMMENT_LINE.match(line) for line in text.splitlines()):
            hits.append({'path': rel, 'detail': 'blank' if not text.strip() else 'comments only'})
    return hits


def orphan_files(repo, files):
    corpus = {rel: read(repo, rel) or '' for rel in files if os.path.splitext(rel)[1] in TEXT_EXT
              or os.path.basename(rel).startswith(('Dockerfile', 'Makefile', 'Procfile'))}
    hits = []
    for rel in files:
        stem, ext = os.path.splitext(os.path.basename(rel))
        if ext not in SOURCE_EXT or stem in ENTRY_STEMS or re.search(r'(^|[._-])(test|spec)s?([._-]|$)', stem):
            continue
        pattern = re.compile(r'(?<![\w-])' + re.escape(stem) + r'(?![\w-])')
        if not any(other != rel and pattern.search(text) for other, text in corpus.items()):
            hits.append({'path': rel, 'detail': f'"{stem}" not mentioned in any other tracked file'})
    return hits


def _py_noop(fn):
    body = list(fn.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], 'value', None), ast.Constant) \
            and isinstance(body[0].value.value, str):
        body = body[1:]
    if not body:
        return 'docstring only'
    if len(body) != 1:
        return None
    s = body[0]
    if isinstance(s, ast.Pass):
        return 'pass'
    if isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and s.value.value is Ellipsis:
        return '...'
    if isinstance(s, ast.Return) and (s.value is None or (isinstance(s.value, ast.Constant) and s.value.value is None)):
        return 'return None'
    if isinstance(s, ast.Return) and isinstance(s.value, ast.Name) and fn.args.args \
            and s.value.id == fn.args.args[-1].arg and len(fn.args.args) <= 2:
        return 'returns its argument unchanged'
    return None


def _py_exempt(fn, parents):
    names = {getattr(d, 'id', None) or getattr(d, 'attr', None) for d in fn.decorator_list}
    if names & {'abstractmethod', 'overload', 'abc.abstractmethod', 'property'}:
        return True
    for cls in parents:
        bases = {getattr(b, 'id', None) or getattr(b, 'attr', None) for b in cls.bases}
        if bases & {'Protocol', 'ABC', 'Interface'}:
            return True
    return False


def noop_functions(repo, files):
    hits = []
    for rel in files:
        ext = os.path.splitext(rel)[1]
        text = read(repo, rel)
        if not text:
            continue
        if ext == '.py':
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue

            def walk(node, parents):
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        why = _py_noop(child)
                        if why and not _py_exempt(child, parents):
                            hits.append({'path': f'{rel}:{child.lineno}', 'detail': f'{child.name}: {why}'})
                        walk(child, parents)
                    elif isinstance(child, ast.ClassDef):
                        walk(child, parents + [child])
                    else:
                        walk(child, parents)
            walk(tree, [])
        elif ext in {'.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs'} and not rel.endswith('.d.ts'):
            for m in JS_NOOP.finditer(text):
                name = next((g for g in m.groups() if g), '?')
                if name in JS_KEYWORDS:
                    continue
                hits.append({'path': f'{rel}:{text.count(chr(10), 0, m.start()) + 1}',
                             'detail': f'{name}: empty body'})
    return hits


def missing_paths(repo, files):
    hits = []
    for rel in files:
        base = os.path.dirname(rel)
        if os.path.basename(rel) == 'package.json':
            try:
                scripts = json.loads(read(repo, rel) or '{}').get('scripts', {})
            except ValueError:
                continue
            for name, cmd in scripts.items():
                for tok in re.findall(r'(?:^|\s)(\.{0,2}/?[\w.@-]+(?:/[\w.@-]+)+\.\w+|[\w.@-]+\.(?:js|mjs|cjs|ts|py|sh))(?=\s|$)', cmd):
                    if not os.path.exists(os.path.join(repo, base, tok)):
                        hits.append({'path': rel, 'detail': f'script "{name}" names missing {tok}'})
        elif rel.endswith('.md'):
            for tok in re.findall(r'`([\w.@-]+(?:/[\w.@-]+)+/?)`', read(repo, rel) or ''):
                if tok.startswith(('http', '@')) or '://' in tok or '<' in tok:
                    continue
                if not any(os.path.exists(os.path.join(repo, b, tok)) for b in (base, '')):
                    hits.append({'path': rel, 'detail': f'names missing path {tok}'})
    return hits


def main(argv):
    as_json = '--json' in argv
    args = [a for a in argv if a != '--json']
    repo = os.path.abspath(args[0] if args else '.')
    files = [f for f in tracked(repo) if not set(f.split('/')[:-1]) & SKIP_DIRS
             and os.path.isfile(os.path.join(repo, f))]
    report = {
        'empty-dir': empty_dirs(repo),
        'empty-file': empty_files(repo, files),
        'orphan-file': orphan_files(repo, files),
        'noop-function': noop_functions(repo, files),
        'missing-path': missing_paths(repo, files),
    }
    for check, hits in report.items():
        seen = set()
        report[check] = [h for h in hits if not ((h['path'], h['detail']) in seen or seen.add((h['path'], h['detail'])))]
    if as_json:
        print(json.dumps(report, indent=2))
        return
    for check, hits in report.items():
        print(f'## {check} ({len(hits)})')
        for h in hits:
            print(f"  {h['path']}  {h['detail']}")
    print('\nCandidates only: prove each dead (references/dead-weight.md) before removing.')


if __name__ == '__main__':
    main(sys.argv[1:])
