---
operations: ["agents.instructions_read", "agents.list", "agents.read", "agents.search", "agents.team_read", "agents.team_resolve"]
---

# Work with agent teams

Read this procedure before using Agents; reuse it within the task. Use the common
Contextopus guide/read/write tools. Obtain only unknown operation signatures. Missing MCP
is a connection failure, not permission to substitute a private catalog or guess profiles.

## Route the request

| Request / short skill | Procedure |
| --- | --- |
| Use a team: `$agents development` | The work sequence below |
| Find or inspect teams/profiles: `$agents-search` | agents/search |
| Create or edit teams/profiles: `$agents-edit` | agents/edit |
| Read or change the main agent's rules: `$agents-settings` | agents/instructions |

Ordinary language after `$agents` uses the same routing. A lookup does not authorize launch;
a team name alone selects that team and does not launch every member or invent a task.

## Main-agent work sequence

1. Call agents.instructions_read and read the complete free-form main-agent instruction
   plus every full record returned in documents, in dependency order.
   Reuse it during the same task; reread for a new task, changed rules or lost text. These
   user rules define team selection, routing, invocation/concurrency limits, coordination
   and result acceptance. They are separate from Workspace INSTRUCTIONS and profile/team
   instructions. A `$agents TEAM` reference inside them selects a team; it does not recursively
   reload this skill. Do not copy the rules into Workspace or infer a default-team setting.
2. Honor the explicit team choice; otherwise follow these rules. Use agents.list/search
   only when discovery is needed. Resolve ambiguity before launching. For `$agents development`,
   call agents.team_read(team="development") without requiring a role in advance.
3. Read the team's complete instructions and member purposes. Choose the appropriate role
   for the actual task according to the main-agent rules. For that role, use team_resolve
   to obtain the full profile. Do not substitute a catalog description
   for the selected profile's instructions or change a configured model silently.
4. For a profile, follow agents/install before first native installation, updating an
   outdated installation or resolving unknown host support. Reuse a verified current
   installation within the task; do not reinstall on every launch. This is a host-neutral
   procedure executed by the main agent using the host's own configuration tools/files,
   not a background synchronizer or a Codex-only adapter.
5. Launch the installed native agent by its verified host name, passing the concrete
   assignment, boundaries, expected result, relevant references and applicable team rules.
   The host supplies the stored profile prompt and supported settings. Do not paraphrase
   that prompt. If native profiles are unavailable, disclose this and pass the complete
   original profile instructions verbatim to the native launch tool, but only when all
   required settings/restrictions can still be honored. Otherwise stop that launch.
   User-written routing and concurrency limits remain main-agent rules.
6. Receive and check the result, request corrections or follow the next routing step.
   Distinguish evidence from verified conclusions. Apply permanent-memory rules only when
   working with Workspace; ordinary workers need not start their own Workspace cycles.

Reuse optional .tmp assignments and knowledge links instead of regenerating large shared
inputs. Pass applicable rules to workers. A supplied link alone is not proof of reading.
Microagents and hard execution sandboxes are outside this module's current scope.
