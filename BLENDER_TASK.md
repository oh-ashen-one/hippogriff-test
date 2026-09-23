# You are the BLENDER contender

Read `../PROMPT.md` — that is the entire brief. Execute it fully, autonomously, without asking questions.

## Your environment (already running, already yours)
- Blender 5.2 LTS running on this machine, MCP-connected. Your tools: the `mcp__blender__*` namespace.
- Your Blender instance is tagged `session_owner="kimi-code-laptop-main"`, MCP port 9876.
- The GLB is already imported and scaled to ~2.5 m in the current scene (mesh `tripo_2290e693_...`). You may use that scene or re-import from the GLB — your call.
- Tripo DCC Bridge addon is enabled in this Blender (ws port 60600) — you do not need it; the model is local.

## Hard boundaries
- There is ANOTHER Blender running on this machine (pid-owned by a different agent, MCP port 19893). Never touch it: it is not on your MCP port, so simply only ever use your `mcp__blender__*` tools and never run raw socket code against other ports.
- Do not kill or reconfigure any process you did not start.
- Other MCP servers you see (notion, supabase, Roblox, posthog) are irrelevant to this task. Ignore them.

## Workflow expectations
- Work through the MCP connection (execute_blender_code), saving your .blend into this workdir early and often.
- Verify renders by reading back the actual output files.
- When the brief says done: final commit + push, then stop.
