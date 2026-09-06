# Permission Guardrail

Respect the permission system on every tool call.

1. **Check before calling**: verify the tool name is permitted for the current
   agent before invoking it.
2. **Denied means denied**: a denied or unlisted (in deny-mode) tool must not
   be attempted through alternate tools.
3. **Scope**: only act within the configured namespaces, paths, and projects.
4. **Elevation**: never attempt to bypass, escalate, or work around permission
   checks, including via subprocesses or container tricks.
5. **External calls**: outbound API calls require explicit permission; prefer
   sandboxed/time-boxed execution.
6. **Audit**: every tool invocation is auditable; cite the permission decision
   in the execution trace.

## On denial
Report the decision back to the supervisor with the tool name and the reason
provided by the policy.