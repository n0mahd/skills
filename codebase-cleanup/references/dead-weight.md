# Dead weight: what to remove and how to prove it

Dead weight is anything in the repo that no longer affects what the code does, how it is built,
tested, deployed or understood. It costs every reader (and every agent) attention, and it lies:
a reader assumes anything present matters. Removing it is behaviour-preserving by definition, so
the whole job is **proving it is dead**.

Start with `scripts/dead_weight.py <repo>` for the structural candidates, the stack's own
dead-code tools for symbols, then the catalogue below for what tools miss.

## Catalogue

### Structure

- **Empty folders**, and folders holding only placeholders (`.gitkeep`, `.keep`, `.DS_Store`, an
  empty `__init__.py`) when nothing writes into them at runtime or build time.
- **Empty or comment-only files**: a module with only a header, a stylesheet with no rules, an
  `index` that re-exports nothing.
- **Orphan files** nothing imports, loads, routes to, lists or runs: old scripts, superseded
  migrations helpers, unused assets (images, fonts, icons), fixtures no test reads, old configs
  for tools no longer used (`.travis.yml` after moving CI, a second linter config).
- **Pass-through layers**: a folder or barrel file that only re-exports another, a wrapper module
  around a single call with one caller.

### Code

- **Functions that do nothing**: empty bodies, `pass`, `return` / `return None` / `return x`
  unchanged, a wrapper that forwards its arguments unchanged to one other function, a handler
  that only logs and swallows. Keep them only when they are a deliberate default (a `noop`
  callback, an interface's default hook, an abstract method), and then name them as such.
- **Functions only tests use**: if production never calls it, it is dead, and so are the tests
  that exist only to test it. Delete both. Keep it only if it is a real test helper (lives with
  the tests, used by several tests to build fixtures or assert outcomes); move it there if it
  lives in production code.
- **Test helpers, fakes, fixtures and mocks** that no test uses, or that mock a module that no
  longer exists.
- **Unused symbols**: exports, functions, classes, constants, types, parameters every caller
  passes the same value for, return values nobody reads, fields written but never read.
- **Unreachable code**: branches behind a condition that is always true or false, code after a
  `return` or `throw`, `case`s for values that can no longer occur, feature flags that are fully
  rolled out or fully off (keep the live path, remove the flag and the other path).
- **Compatibility shims** for versions, clients or data formats no longer supported, deprecated
  aliases with no callers, migrations-era dual reads and writes after the migration finished.
- **Commented-out code**. Git keeps history; delete it.
- **Suppressions that no longer suppress anything**: `eslint-disable`, `# type: ignore`,
  `@ts-expect-error`, `noqa`, `nolint`, `#[allow(...)]` on lines that no longer trigger the rule.

### References to things that are gone

- **Docs and comments** naming files, functions, flags, commands or env vars that no longer exist,
  or describing behaviour the code no longer has. `TODO`s for work that is done or abandoned.
- **Config entries** for paths and tools that are gone: `package.json` scripts pointing at missing
  files, `tsconfig` paths and includes, test-runner globs, lint overrides for deleted folders,
  `.gitignore` / `.dockerignore` lines for outputs nothing produces, CODEOWNERS for deleted paths,
  CI steps and caches for removed jobs, Dockerfile `COPY` of missing paths.
- **Env vars and settings** nobody reads, in `.env.example`, docs, CI and deploy config. Removing
  one that production config sets is an owner decision (see below).
- **Dependencies** nothing imports (and dev dependencies for tools no longer run), `@types/*` for
  removed packages, lockfile entries that remain after the manifest dropped them.
- **Styles and markup**: CSS selectors nothing renders, i18n keys nobody looks up, unused design
  tokens, templates no route renders.

## Proving it is dead

A symbol is dead only when every way it could be reached has been checked:

- **Whole-repo search**, including tests, scripts, docs, HTML, templates, CSS, config, CI and
  infrastructure files, for the name and its likely string forms (kebab, snake, camel, with and
  without prefixes).
- **Dynamic reach**: string-built names, reflection, `getattr`, `require(variable)`, dependency
  injection containers, plugin registries, decorators that register, routes and handlers named in
  config, serverless or cron entry points, CLI entry points in manifests, ORM model discovery,
  template lookups by name, migrations loaded by directory.
- **Outside the repo**: a published package's public API, an HTTP or RPC endpoint, a webhook, a
  database function or column, a file other services or users import. These are **owner
  decisions**, not cleanups, unless the owner confirms nothing external uses them.
- **Generated code and build outputs**: don't delete what a generator recreates; fix the generator
  or its config instead.
- **Tooling**: use the stack's analyser as a lead, never as the proof (TypeScript/JS: `knip`,
  `ts-prune`, `depcheck`, `tsc --noUnusedLocals --noUnusedParameters`; Python: `vulture`, `ruff`
  rules `F401`, `F841`, `ERA001`; Go: `deadcode`, `staticcheck` `U1000`; Rust: compiler warnings,
  `cargo-udeps`, `cargo-machete`; CSS: coverage in the browser's dev tools or `purgecss` in report
  mode). Check the tool's false positives the same way as any other claim.

Record the evidence with the finding: the search commands run and that they returned nothing
outside the definition, or the reason the dynamic paths don't apply.

## Removing it

- **Delete, don't disable.** No commenting out, no `_unused` renames, no "deprecated" markers on
  things with no callers.
- **Remove the whole chain** in one commit: the code, its tests, fixtures, types, exports, docs,
  config entries, env vars in examples, dependencies only it used, and any folder left empty.
  Then search again for the name: zero hits outside history.
- **One topic per commit** (for example "remove unused report exporter"), separate from moves and
  behaviour fixes, so a wrong call is a one-commit revert.
- **Run the full gate** after each removal batch: types and build catch most mistakes, the test
  suite catches the rest of the static ones, and only runtime catches dynamic reach, so lean on
  the evidence above for those.
- **Owner decisions** (list, with a recommendation, don't do): anything reachable from outside
  the repo, env vars production sets, feature flags whose off path might still be needed, data
  model fields and columns, anything security-relevant (an "unused" auth check is a finding, not
  dead weight).
