# DeepStack

DeepStack is a plugin for Claude Code, Codex, Copilot, and Cursor. It raises a task in altitude, depth, and range, then requires a proof before a done claim.

The principles follow Felix Rieseberg, [How to be more ambitious: A tutorial for humans with models](https://felixrieseberg.com/how-to-be-more-ambitious-a-tutorial-for-humans-with-models/) (13 October 2026). The page shows no licence. This repository states the principles in its own words. The citation and the four questions are in `plugins/deepstack/skills/deepstack-mode/references/source.md`.

Marketplace name: `DeepStack`. Plugin id: `deepstack@DeepStack`. Source repository: `jl-cmd-projects/DeepStack`.

`npx claude-dev-env` installs this plugin for Claude Code, Codex, and Cursor.

## Synchronize Codex skills on Linux

From a checkout of this repository, run:

```sh
python3 scripts/sync_codex.py
```

The command fetches the repository's default branch on every invocation. It
exposes skills through `~/.agents/skills` and the active `$CODEX_HOME/skills`,
or `~/.codex/skills` when `CODEX_HOME` is unset. It preserves Codex configuration,
credentials, and hook trust. Git and Python 3.10 or later are required.

Updates follow commit changes, including commits that leave the plugin version
unchanged. The command replaces the current plugin through one symlink, preserves
relative references, and removes links for deleted skills. A failed fetch leaves
the installed skills available. An existing unmanaged skill causes an error.
Concurrent invocations sharing the state directory run one at a time.

To refresh skills automatically at environment startup, configure the environment's
setup and maintenance commands to invoke this script before starting the agent.
Use an absolute checkout path in those commands. Retain the default state directory
`~/.local/share/deepstack`, or select retained storage with `--state-dir`.
Use repeated `--skills-dir` arguments to select other discovery directories.
The script itself does not register startup commands or schedule background work.

Installation does not establish Codex Cloud discovery. Before calling a Cloud
deployment complete, have a separate Cloud agent discover and load `deepstack-mode`
through its skill catalog. Repeat after a repository update and in a new Cloud
session. The JSON receipt leaves both Cloud verification fields false because
filesystem checks cannot establish those outcomes. A nested Codex CLI check does
not establish Cloud harness discovery.

Run the synchronization regression checks with:

```sh
python3 -m unittest discover -s tests -p test_codex_sync.py -v
```
