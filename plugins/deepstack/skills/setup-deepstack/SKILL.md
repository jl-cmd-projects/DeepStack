---
name: setup-deepstack
description: "Choose models per DeepStack role and turn the session hook on or off. Use for /setup-deepstack."
---

# Setup DeepStack

Write the current runtime's model sheet. The sheet shape is in [model-sheet](../deepstack-mode/references/model-sheet.md). Paths are in [runtimes](../deepstack-mode/references/runtimes.md).

## Steps

1. List the model names this session's agent tool accepts. `inherit-parent` is always valid. It runs the role on the parent session's model.
2. If the sheet exists, read it. Otherwise start from the shape in the model-sheet reference.
3. Show each role and ask the user to accept or change it. Ask for the default effort: `session`, or one of `low`, `medium`, `high`, `xhigh`, `max`.
4. Ask whether the session hook stays on. The default is on. `session hook: off` stops the injection.
5. Write the whole sheet again so a second run leaves the same file. The runtime directory for that file is in the runtimes reference.
