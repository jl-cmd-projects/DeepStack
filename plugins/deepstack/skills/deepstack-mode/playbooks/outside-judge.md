# Outside judge

1. Name who or what grades the result. The worker is not the judge.
2. Prefer a tool the worker can run and read in the same turn.
3. Calibrate that judge on a known-good case and a known-bad case before trusting a pass.
4. The judge reads a consumer of the output, such as a run that logs the value it resolved. The writer's own readback does not count.
5. The judge's verdict comes in before the pull request opens.
6. A done claim uses the trust card in `references/trust-card.md`.
