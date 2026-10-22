# Outside judge

1. Name who or what grades the result. The worker is not the judge.
2. Prefer a tool the worker can run and read in the same turn.
3. Calibrate that judge on a known-good case and a known-bad case before trusting a pass.
4. The judge reads a consumer of the output, such as a run that logs the value it resolved. The writer's own readback does not count.
5. The judge's verdict on the head the pull request opens with comes in before the pull request opens. A push after the verdict needs a new one. When the consumer can run only after the merge, such as a workflow that runs only on `workflow_dispatch`, the judge reads a pre-merge run of its steps with stubbed tools, and the pull request body names the consumer run that follows the merge.
6. A done claim uses the trust card in `references/trust-card.md`.
