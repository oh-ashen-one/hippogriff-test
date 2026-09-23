# You are the HOUDINI contender

Read `../PROMPT.md` — that is the entire brief. Execute it fully, autonomously, without asking questions.

## Your environment (already running)
- Houdini 22.0.451 running on this machine with `untitled.hip` open, MCP-connected. Your tools: the `mcp__houdini__*` namespace.
- Save your own .hip into this workdir at the start and work from there.
- Import the GLB from `/Users/midir/hippogriff-test/hippogriff.glb` (it is ~1 unit tall; scale per the brief).

## Hard boundaries
- Other agent sessions run on this machine (a Blender on MCP port 19893, tmux/ghostty sessions). Do not kill, pause, or reconfigure any process you did not start.
- Other MCP servers you see (notion, supabase, Roblox, posthog) are irrelevant. Ignore them.

## Workflow expectations
- This is where Houdini should flex: vellum/feather secondary sim, pyro or volumetric atmosphere, Solaris/Karma for the final render. Keyframed-only secondary motion is a weak answer if simulation was available.
- Verify renders by reading back the actual output files.
- When the brief says done: final commit + push, then stop.
