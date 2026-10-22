#!/usr/bin/env python3
"""Split a big JS/TS file into modules by moving top-level blocks verbatim.

Works on files where every top-level declaration starts at column 0
(function/async function/const/let/class/export ...) and multi-line ones end
with a line starting with `}` or `]` at column 0. Comment lines directly above
a declaration travel with it. Run `outline` first: any LOOSE line means the
file doesn't fit that shape and the split needs care by hand.

  split_blocks.py outline FILE                 list blocks; flag loose lines
  split_blocks.py deps FILE                    block -> blocks it references (JSON)
  split_blocks.py check FILE ASSIGN.json       module graph; fails on cycles or unassigned blocks
  split_blocks.py split FILE ASSIGN.json OUTDIR [--cjs]
                                               write one file per module with generated
                                               requires/exports (CommonJS with --cjs, else ESM)
  split_blocks.py verify ORIGINAL NEWFILE...   every original block appears byte-identical

ASSIGN.json: {"order": ["util", "board", ...],          # dependency order, earliest first
              "modules": {"util": {"header": "What this module owns.",
                                   "blocks": ["GameError", "makeEvent"]}, ...},
              "public": ["names the old file exported"]}
Names in a module's export list = names used by other modules + "public".
Destructured imports + cycles = undefined at load time in CommonJS, so `check`
must pass before `split`.
"""
import json, re, sys, os

START = re.compile(r'^(?:export\s+(?:default\s+)?)?(?:async\s+)?(function\*?|const|let|var|class)\s+([A-Za-z_$][\w$]*)')
_STRING = re.compile(r"'(?:[^'\\\n]|\\.)*'|\"(?:[^\"\\\n]|\\.)*\"|`(?:[^`\\]|\\.)*`", re.S)


class _Strip:
    """Blank out string literals but keep the code inside template ${...}."""
    @staticmethod
    def sub(_repl, text):
        def keep_code(m):
            lit = m.group(0)
            return "''" if lit[0] != '`' else ' '.join(re.findall(r'\$\{([^}]*)\}', lit)) or "''"
        return _STRING.sub(keep_code, text)


STRINGS = _Strip()


def blocks_of(lines):
    out, loose, i, n, pending = [], [], 0, len(lines), None
    while i < n:
        m = START.match(lines[i])
        if m:
            kind = m.group(1)
            if kind != 'function' and not kind.startswith('function') and lines[i].rstrip().endswith(';'):
                end = i
            else:
                end = i + 1
                while end < n and not re.match(r'^[}\]]', lines[end]):
                    end += 1
            s = pending if pending is not None else i
            out.append((m.group(2), s, end, '\n'.join(lines[s:end + 1])))
            pending, i = None, end + 1
            continue
        if lines[i].startswith('//') or lines[i].startswith('/*') or lines[i].startswith(' *'):
            pending = i if pending is None else pending
        else:
            pending = None
            if lines[i].strip() and not re.match(r"^(module\.exports|'use strict'|\"use strict\"|import |const \{[^}]*\} = require|\s|\}|\);?$)", lines[i]):
                loose.append((i + 1, lines[i][:90]))
        i += 1
    return out, loose


def read(path):
    return open(path).read().split('\n')


def deps(blocks):
    names = {b[0] for b in blocks}
    result = {}
    for name, _, _, text in blocks:
        body = STRINGS.sub("''", text)
        used = {t for t in re.findall(r'\b[A-Za-z_$][\w$]*\b', body) if t in names and t != name}
        result[name] = sorted(used)
    return result


def module_graph(blocks, assign):
    owner = {}
    for mod, spec in assign['modules'].items():
        for b in spec['blocks']:
            if b in owner:
                sys.exit(f'{b} assigned twice')
            owner[b] = mod
    missing = [b[0] for b in blocks if b[0] not in owner]
    unknown = [b for b in owner if b not in {x[0] for x in blocks}]
    d = deps(blocks)
    edges = {}
    for f, ds in d.items():
        for g in ds:
            if f in owner and g in owner and owner[f] != owner[g]:
                edges.setdefault(owner[f], {}).setdefault(owner[g], set()).add(f'{f}->{g}')
    return owner, d, edges, missing, unknown


def check(path, assign_path):
    blocks, _ = blocks_of(read(path))
    assign = json.load(open(assign_path))
    owner, _, edges, missing, unknown = module_graph(blocks, assign)
    ok = True
    if missing:
        print('UNASSIGNED', missing); ok = False
    if unknown:
        print('UNKNOWN', unknown); ok = False
    order = assign['order']
    for a, targets in edges.items():
        for b, why in targets.items():
            if order.index(b) >= order.index(a):
                print(f'BACKWARD/CYCLE {a} -> {b}: {sorted(why)[:5]}'); ok = False
    for m in order:
        print(f'{m} -> {sorted(edges.get(m, {}))}')
    sys.exit(0 if ok else 1)


def split(path, assign_path, outdir, cjs):
    source = read(path)
    blocks, _ = blocks_of(source)
    externals = external_imports(source)
    assign = json.load(open(assign_path))
    owner, d, _, missing, _ = module_graph(blocks, assign)
    if missing:
        sys.exit(f'unassigned: {missing}')
    order = [b[0] for b in blocks]
    used_outside = set(assign.get('public', []))
    for f, ds in d.items():
        for g in ds:
            if owner[f] != owner[g]:
                used_outside.add(g)
    ext = os.path.splitext(path)[1]
    os.makedirs(outdir, exist_ok=True)
    for mod in assign['order']:
        spec = assign['modules'][mod]
        mine = [b for b in blocks if owner[b[0]] == mod]
        imports = {}
        for b in mine:
            for g in d[b[0]]:
                if owner[g] != mod:
                    imports.setdefault(owner[g], set()).add(g)
        lines = ['// ' + spec.get('header', mod).replace('\n', '\n// '), '']
        mine_text = STRINGS.sub("''", '\n'.join(b[3] for b in mine))
        for line, names in externals.items():
            if any(re.search(r'\b' + re.escape(n) + r'\b', mine_text) for n in names):
                lines.append(line)
        for im in assign['order']:
            if im in imports:
                names = ', '.join(sorted(imports[im], key=order.index))
                lines.append(f"const {{ {names} }} = require('./{im}');" if cjs else f"import {{ {names} }} from './{im}{ext}';")
        if imports:
            lines.append('')
        for b in mine:
            text = b[3] if cjs else re.sub(r'^(?=(async\s+)?(function|const|let|class)\s)', '', b[3])
            lines += [text, '']
        exported = [b[0] for b in mine if b[0] in used_outside]
        if cjs:
            lines += ['module.exports = {'] + [f'    {n},' for n in exported] + ['};']
        else:
            lines += ['export {'] + [f'    {n},' for n in exported] + ['};']
        open(os.path.join(outdir, mod + ext), 'w').write('\n'.join(lines) + '\n')
        print(f'{mod}: {len(mine)} blocks, {len(exported)} exports')


IMPORT_LINE = re.compile(r"^(?:const|let|var)\s+(.+?)\s*=\s*require\(|^import\s+(.+?)\s+from\s")


def external_imports(lines):
    """Top-level require/import lines -> {line: [names it binds]}."""
    found = {}
    for line in lines:
        m = IMPORT_LINE.match(line)
        if not m:
            continue
        binding = (m.group(1) or m.group(2)).strip('{} ')
        names = [part.split(':')[-1].split(' as ')[-1].strip() for part in binding.split(',') if part.strip()]
        found[line] = [n for n in names if n]
    return found


def verify(original, new_files):
    old = sorted(b[3] for b in blocks_of(read(original))[0])
    new = sorted(b[3] for f in new_files for b in blocks_of(read(f))[0])
    print(f'original {len(old)} blocks, new {len(new)}, identical: {old == new}')
    sys.exit(0 if old == new else 1)


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    cmd = a[0]
    if cmd == 'outline':
        blocks, loose = blocks_of(read(a[1]))
        for name, s, e, _ in blocks:
            print(f'{name}\t{s + 1}-{e + 1}')
        for ln, text in loose:
            print(f'LOOSE {ln}: {text}')
    elif cmd == 'deps':
        print(json.dumps(deps(blocks_of(read(a[1]))[0]), indent=1))
    elif cmd == 'check':
        check(a[1], a[2])
    elif cmd == 'split':
        split(a[1], a[2], a[3], '--cjs' in a)
    elif cmd == 'verify':
        verify(a[1], a[2:])
    else:
        sys.exit(__doc__)
