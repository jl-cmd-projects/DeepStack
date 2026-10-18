# Intake

Write these three lines before any plan:

```
SCOPE (role): <the standing job, in one sentence, with no example nouns>
EXAMPLES (illustration only): <each example the user gave, or none>
ZOOM-IN BLOCKER: <why the standing job cannot be done now, or none>
```

Scope is the standing job that would have handled the ask with no one requesting it. Examples are illustration. Zoom in only with a named blocker.

Then answer four things, in your own sentences:

1. What a top person in that field would do that this task left out.
2. The raw source to start from. Name the files, commands, diffs, and logs.
3. The methods and tools the worker will have.
4. What, other than the agent or the user, shows the result is right.

Rewrite the task deeper, at the same size. Put `CDE_DEEPEN:v1` on line 1. Carry the `SCOPE (role):` line in the worker prompt verbatim.

A rewrite is refused when it pastes the four question stems, when the scope line contains an example noun while `ZOOM-IN BLOCKER:` is `none`, or when it drops or loosens a hard constraint. Keep every hard constraint word for word, each on its own line.
