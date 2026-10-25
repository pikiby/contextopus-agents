---
operations: []
---

# Native host references

The shared lifecycle is agents/install. These references are starting points; check the
installed version and actual available commands before acting. No row implies tested
support on this machine or permission to install software or alter every client.

- Codex: https://developers.openai.com/codex/multi-agent/#custom-agents
  Current docs describe standalone TOML in ~/.codex/agents or .codex/agents with name,
  description, developer_instructions, model and model_reasoning_effort. Older versions
  may require an agents.<name>.config_file registration; inspect the actual loader.
  MCP and sandbox/approval policies are inherited from the parent; a profile cannot
  independently override them. Supported capability switches are version-dependent.
- Claude Code: https://code.claude.com/docs/en/sub-agents
  User/project agent Markdown has YAML metadata and a prompt body. tools/disallowedTools
  constrain the tool surface; mcpServers can scope connections. Plugin agent definitions
  have different supported fields. Preserve body text and verify effective restrictions.
- OpenCode: https://opencode.ai/docs/agents/ and https://opencode.ai/docs/permissions/
  Native JSON entries or Markdown/YAML profiles support model, prompt and per-agent
  permissions. Check the version's current keys; legacy tools differs from permission.
- Hermes: https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation
  Current delegation docs describe inherited tools, not a per-call toolsets selector.
  Verify whether reusable native profiles exist in the installed version; do not write
  a Codex TOML or invent a profile schema. Verbatim handoff is not isolated permissions.
- Crush: https://github.com/charmbracelet/crush
  Inspect current native agent configuration and loading support first. Do not interpret
  an auto-approval list as a restriction to those tools. No verified native profile
  installation recipe is claimed here.
- Other hosts: obtain official agent configuration, invocation and permission documentation.
  Apply the same lifecycle using supported native mechanisms. Report unsupported features;
  do not change the universal workflow or add a Core special case for a host.
