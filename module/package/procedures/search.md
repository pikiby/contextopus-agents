---
operations: ["agents.list", "agents.read", "agents.search", "agents.status", "agents.team_read"]
---

# Find and inspect agents

Use agents.list for a catalog, agents.read for a known profile/team, agents.team_read for
a team's rules and member purposes, or agents.search for semantic discovery. Inherit Core
selection parameters; assess diagnostics, pending_count and stale_results_omitted before
concluding that nothing suitable exists. Read a selected full record before relying on it.

This procedure is read-only: do not create profiles, change rules, launch workers or open
Workspace cycles. If asked to use a team, obtain agents/work and follow its complete
main-agent instruction and selection sequence. Reuse already-read procedures in this task.

The catalog is file-authoritative. Semantic discovery embeds nonempty Markdown instruction bodies verbatim. Empty bodies
use title and description for discovery; other YAML fields remain metadata. Inspect reference_errors and
agents.status for broken file links or failed source scans. An unavailable or malformed
source is an error; an empty search is not proof that its file was removed.

For an empty or whitespace-only profile/team instruction body, semantic discovery uses
only the title and description as derived search text. Source bytes and executor/team
instructions stay empty. Its vector revision hashes that actual discovery text, so a title
or description edit triggers reembedding; other metadata/path changes retain the vector.
