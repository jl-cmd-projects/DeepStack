# Model sheet

`/setup-deepstack` writes this file. Delete a line to fall back to the parent session's model.

```
# DeepStack model configuration

altitude: inherit-parent
depth: inherit-parent
range: inherit-parent
judgment and prose: inherit-parent

default effort: session
session hook: on
```

`session hook: off` stops the SessionStart hook from injecting the DeepStack line. Any other value, or a missing line, leaves the hook on.
