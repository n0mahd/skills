// Template for a repo's map test (vitest). Copy it next to the source, then adjust the
// constants marked ADAPT. For another stack, port the same three checks to its test runner.
import { existsSync, readdirSync, readFileSync, statSync } from 'fs'
import { dirname, join, relative, resolve } from 'path'
import { fileURLToPath } from 'url'
import { describe, expect, it } from 'vitest'

/**
 * Keeps the agent-facing map honest. The docs are how an agent finds its way around,
 * so a path they name that no longer exists, or a source directory they never mention,
 * is a defect: it sends the next change to the wrong place.
 */

// ADAPT: the repo root, relative to this file.
const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
// ADAPT: where the module map and the strategy page live, and the source root to cover.
const MAP = 'documents/architecture.md'
const STRATEGY = 'documents/strategy.md'
const SOURCE = 'src'
const SOURCE_FILE = /\.tsx?$/
// ADAPT: directories that are never source: dependencies, build output, ignored local state.
const SKIP_DIRS = new Set(['.git', 'node_modules', 'dist', 'build', 'coverage', 'public'])
// ADAPT: point-in-time docs (decision records) that may name paths that have since moved.
const POINT_IN_TIME = ['documents/decisions']
// ADAPT: paths docs name on purpose that are not in the tree (ignored local files).
const LOCAL_ONLY: RegExp[] = []

const read = (path: string) => readFileSync(join(ROOT, path), 'utf8')

/** Walks the files rather than asking git, because some gates test a `git archive` copy with no `.git`. */
function livingDocs(dir = ROOT): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name)
    const rel = relative(ROOT, path)
    if (entry.isDirectory()) return SKIP_DIRS.has(entry.name) || POINT_IN_TIME.includes(rel) ? [] : livingDocs(path)
    return entry.name.endsWith('.md') ? [rel] : []
  })
}

/** Repo paths inside a doc: anything under a top-level directory that exists, or a root SHOUTY_CASE.md file. */
function pathPattern(): RegExp {
  const tops = readdirSync(ROOT, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && !SKIP_DIRS.has(entry.name))
    .map((entry) => entry.name.replace(/[.]/g, '\\.'))
  return new RegExp(`(?<![\\w/.~-])((?:${tops.join('|')})/[\\w./@-]*[\\w/]|[A-Z][A-Z_]+\\.md)(?![\\w*<{])`, 'g')
}

/** Any relative path in backticks that ends in `/` or a file extension, including short forms like `routes/books.ts`. */
const BACKTICKED = /`((?![/~.]|\w+:)[\w.@-]+\/[\w./@-]*?(?:\/|\.(?:tsx?|m?js|json|md|sh|sql|py|ya?ml|service|timer|css|html)))`/g

/** Every file and directory in the repo, so a short form resolves when some real path ends with it. */
function repoPaths(dir = ROOT): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    if (SKIP_DIRS.has(entry.name)) return []
    const rel = relative(ROOT, join(dir, entry.name))
    return entry.isDirectory() ? [rel, ...repoPaths(join(dir, entry.name))] : [rel]
  })
}

describe('architecture map', () => {
  it('every path a living doc names exists', () => {
    const pattern = pathPattern()
    const known = repoPaths()
    const missing: string[] = []
    for (const doc of livingDocs()) {
      let history = false
      read(doc)
        .split('\n')
        .forEach((line, index) => {
          // A "History" section records where things used to be, like a decision record.
          if (/^#+ /.test(line)) history = /^#+ History\b/i.test(line)
          if (history) return
          const named = new Set([...line.matchAll(pattern), ...line.matchAll(BACKTICKED)].map(([, path]) => path))
          for (const path of named) {
            if (LOCAL_ONLY.some((local) => local.test(path))) continue
            if (existsSync(join(ROOT, path)) || existsSync(join(ROOT, dirname(doc), path))) continue
            const tail = path.replace(/\/$/, '')
            if (known.some((known) => known.endsWith(`/${tail}`))) continue
            missing.push(`${doc}:${index + 1} names ${path}`)
          }
        })
    }
    expect(missing).toEqual([])
  })

  it('every repo path a source file names exists', () => {
    // Comments are read as much as docs, so a moved module leaves stale pointers there too.
    const pattern = pathPattern()
    const sources = (dir: string): string[] =>
      readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
        const path = join(dir, entry.name)
        if (entry.isDirectory()) return SKIP_DIRS.has(entry.name) ? [] : sources(path)
        return SOURCE_FILE.test(entry.name) && path !== fileURLToPath(import.meta.url) ? [relative(ROOT, path)] : []
      })
    const missing: string[] = []
    for (const file of sources(join(ROOT, SOURCE))) {
      read(file)
        .split('\n')
        .forEach((line, index) => {
          for (const [, path] of line.matchAll(pattern)) {
            if (!path.endsWith('.md') && !existsSync(join(ROOT, path))) missing.push(`${file}:${index + 1} names ${path}`)
          }
        })
    }
    expect(missing).toEqual([])
  })

  it('the module map names every source directory', () => {
    const map = read(MAP)
    const hasSource = (dir: string): boolean =>
      readdirSync(dir).some((name) => {
        const path = join(dir, name)
        return statSync(path).isDirectory() ? hasSource(path) : SOURCE_FILE.test(name)
      })
    const unmapped: string[] = []
    const walk = (dir: string, depth: number) => {
      for (const name of readdirSync(dir)) {
        const path = join(dir, name)
        if (!statSync(path).isDirectory() || !hasSource(path)) continue
        const rel = relative(ROOT, path)
        if (!map.includes(`${rel}/`)) unmapped.push(rel)
        if (depth < 2) walk(path, depth + 1) // ADAPT: how deep the map must go
      }
    }
    walk(join(ROOT, SOURCE), 1)
    expect(unmapped).toEqual([])
  })

  it('the strategy page keeps the sections agents rely on', () => {
    const strategy = read(STRATEGY)
    const sections = ['Purpose', 'Priorities', 'Invariants', 'Direction', 'Blast radius', 'Debt register', 'Open decisions', 'Keeping the map true']
    expect(sections.filter((section) => !new RegExp(`^## ${section}`, 'm').test(strategy))).toEqual([])
  })
})
