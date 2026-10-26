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
   instructions. Follow their direct team/profile wikilinks. A chat invocation such as
   `$agents TEAM` selects a team,
   but is not a document link and does not recursively reload this skill. Preserve applicable
   shared rules already returned by the current context without requiring Workspace to be
   installed. Creating or changing those context rules belongs to Workspace's instructions
   procedure. Do not infer a default-team setting.
2. Honor the explicit team choice; otherwise follow these rules. Use agents.list/search
   only when discovery is needed. Read linked records through agents.read and verify that
   the returned file matches the link; do not assume a filename equals its record ID.
   Resolve ambiguity before launching. For `$agents development`,
   call agents.team_read(team="development") without requiring a role in advance.
3. Read the team's complete instructions and member purposes. Choose the appropriate role
   for the actual task according to the main-agent rules. For that role, use team_resolve
   to obtain the full profile. Do not substitute a catalog description
   for the selected profile's instructions or change a configured model silently.
4. team_resolve returns the full profile, team instructions and main_agent_rules, including
   required instruction documents. Read these complete texts. The main agent decides how
   to create or use the subagent through the current host's applicable skills and native
   tools. Read the relevant host skill before following it; verify that it supports this
   actual environment. Contextopus does not register or launch native agents.
   When the selected profile refers to skill cards or other Contextopus records, follow
   those direct links through the owning enabled module before dependent use. A skill
   card points to the source SKILL.md; read that source before executing the skill.
5. Perform only the requested creation or launch. Permanent profile registration is not
   a universal prerequisite. When the selected host method needs registration, the main
   agent performs and verifies it using the host's skills/tools; agents/install describes
   source preservation and conflict checks. When the host supports direct profile handoff,
   pass the full original instructions verbatim and the supported model/settings. Pass the
   concrete assignment, boundaries, expected result, references and applicable team rules.
   Do not weaken required restrictions or substitute models silently. A catalog save does
   not complete a request to create a native agent. User-written routing and concurrency
   limits remain main-agent rules.
6. Receive and check the result, request corrections or follow the next routing step.
   Distinguish evidence from verified conclusions. Apply permanent-memory rules only when
   working with Workspace; ordinary workers need not start their own Workspace cycles.

Reuse optional .tmp assignments and knowledge links instead of regenerating large shared
inputs. Pass applicable rules to workers. A supplied link alone is not proof of reading.
Microagents and hard execution sandboxes are outside this module's current scope.
