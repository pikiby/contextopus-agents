# Contextopus Agents

**Define your agents once. Reuse the right team for each task.**

Agents is an optional [Contextopus Core](https://github.com/pikiby/contextopus-core)
module for reusable agent profiles, named teams and your delegation rules. Keep
model settings and complete prompts in readable Markdown, find them through
shared semantic search, and let your coding assistant use its native subagent tools.

## Install

Requires **Contextopus Core 1.7+**. Download the
[Agents 0.4.0 ZIP](https://github.com/pikiby/contextopus-agents/releases/download/v0.4.0/contextopus-agents-0.4.0.zip)
and verify it against the release's SHA256SUMS. Then run:

```console
contextopus modules install agents --source /path/to/contextopus-agents-0.4.0.zip
contextopus integrate codex --user --apply
```

Replace `codex` with your configured client. Integration installs the module's skills;
reload the client afterward. For an existing Agents installation, use `modules update`
instead of `modules install`. Add `--plan` to inspect installation before applying it.
Core manages the module database, background indexing and shared embedding model.
Your profiles, teams and rules survive module updates.

## Four entrypoints

- **`$agents development`** — use a named team for the task you actually requested.
- **`$agents-search`** — find profiles and teams by name or meaning without launching them.
- **`$agents-edit`** — create or update profiles and teams.
- **`$agents-settings`** — edit the main agent's delegation and routing rules.

Skill invocation syntax depends on your client. Ordinary-language requests use
the same procedures. Selecting a team does not launch every member.

### Profiles: reusable instructions and settings

A profile can be just a model, or include a complete role prompt and settings.
For example, a Git reader can answer repository questions with a lightweight model.
The main agent retrieves the full profile, checks the chosen client's native
profile support, and installs or updates its native definition before use.
Local edits are protected; unsupported model settings or required permissions
are reported rather than silently weakened. Profiles are not an execution sandbox.

### Teams: choose participants by purpose

A team groups profiles under named roles and may add shared instructions. The
main agent reads member descriptions, selects the appropriate role and obtains
its full profile. Teams link to profile files with Obsidian-style wikilinks.

### Your rules for the main agent

Keep delegation rules in a separate instruction: a simple `$agents development`,
or detailed routing, concurrency limits and result-review criteria. These rules
are read in full and reused within the task. They complement the selected
team and executor prompts rather than replacing either.

### Files you can inspect and edit

Profiles and teams live in `modules/agents/data/profiles/` and `data/teams/`.
YAML stores identity, description and configuration; Markdown holds the prompt.
Main-agent rules live in `core/instructions/`, referenced by a module-owned file.
SQL and RAG are derived from these files through Core's shared reconciliation.
External changes and deletions are reflected without resurrecting deleted files.
Broken links and incomplete scans are reported for repair.

Use the Core web library (`contextopus web`) to browse profiles and teams or
search by meaning. Full reads preserve the original instructions.

## Boundaries

Agents supplies profiles and procedures; the coding environment launches workers.
This release does not deliver messages, watch chats, manage sessions, subscribe
to events or start coordinators. Session communication is separate future work.
Native profile installation is a procedure executed with the client's existing
facilities, not a background synchronizer. Changes do not rewrite running workers.

[File format and migration](docs/file-format.md) ·
[Architecture](docs/architecture.md) · [Verification](docs/verification.md)

## Build from source

```console
python scripts/build.py
```

Install the resulting ZIP with the command above. To run tests, install Core with
its test dependencies and use its Python environment:

```console
PYTHONPATH=/path/to/contextopus-core/src python -m pytest tests -q
```

Tests use temporary roots, real Core module installation and deterministic
embeddings. They do not require access to your conversations or a model API.

## License

[Apache License 2.0](LICENSE). See [NOTICE](NOTICE).

## Client delivery

Core 1.7 client packages share one installer and one persistent data root.
Skills use full canonical names under the `contextopus` plugin namespace, or a
`contextopus-` prefix for native file delivery. Short aliases are user-selected.
See the [client package guide](https://github.com/pikiby/contextopus-core/blob/main/docs/client-packages.md)
for package formats, setup and verification limits.

## Current release

[0.4.0: Full skill names and discoverable procedures](docs/releases/0.4.0.md) · [Downloads](https://github.com/pikiby/contextopus-agents/releases/tag/v0.4.0)
