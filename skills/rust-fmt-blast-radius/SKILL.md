---
name: rust-fmt-blast-radius
description: 'Cargo gotcha. `cargo fmt -- path/to/file.rs` formats the entire crate, not just the named file — silently rewriting every other Rust file in the working tree. Trigger on any of: "run cargo fmt on just one file", "format only web_search.rs", "fmt this one Rust file", "rust formatting blast radius", "why are 14 files in git status after fmt". When working in any Rust crate (Tauri, cargo workspace, single crate) and about to invoke `cargo fmt` on a subset of files, use this skill before running the command.'
---

# `cargo fmt -- <file>` has crate-wide blast radius

`rustfmt`'s CLI accepts a file path after `--`, but `cargo fmt` invokes `rustfmt` against the **entire crate's source set**, ignoring the positional file. Running `cargo fmt -- src/foo.rs` reformats every `.rs` file under `src/`, not just `src/foo.rs`.

Confirmed against rustc/rustfmt 1.85+ via `cargo fmt --check`: a `cargo fmt -- src/web_search.rs` invocation produced `Diff in ...agent_runtime.rs:30:` plus 13 other unrelated files.

## Recovery when this has already happened

1. `git status --short` — see how many files got touched.
2. `git stash` — save your intentional work so you can compare.
3. `git stash show --name-only stash@{0}` — list stashed files.
4. Files you actually edited → keep in your final commit.
5. Files only in the stash (reformatted but not your edit) → `git checkout -- <file>` each.
6. `git stash pop` — restore your real work.
7. `git diff --stat` — confirm only the files you intended changed.

If the stash is too entangled to pop cleanly:

```bash
git --no-pager stash show -p "stash@{0}" --no-color > /tmp/full.patch
git stash drop
git checkout -- <only-your-intentional-files>
git apply --include='.env.example' --include='src/**' /tmp/full.patch
```

## The rule that prevents it

**Never run `cargo fmt` on a single file.** Either:

- Format the whole crate and let `cargo fmt --check` in the pre-commit gate catch drift, OR
- Skip the fmt call entirely and match the surrounding style by hand.

If the pre-commit gate fails on the one file you touched, fix only the lines the gate flagged — `rustfmt` is deterministic, so two passes over the same content produce the same output. Running it once more does not help and may rewrite code you didn't read.

## Detection heuristic

Before any `cargo fmt` invocation, check:

```bash
git diff --stat | wc -l   # baseline file count in your work
```

If after the fmt run that count is wildly higher than baseline, treat the run as crate-wide and use the recovery above.