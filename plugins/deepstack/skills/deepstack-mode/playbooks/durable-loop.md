# Durable loop

1. Name the outcome that should keep happening with no person feeding the next task.
2. List the records the worker must fetch, the map from a version to the change, and the place where a result can be reproduced and checked.
3. Build that access before you ask the worker to own the outcome.
4. Keep the outside judge in the loop.
