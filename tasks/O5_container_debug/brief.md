# O5: Container Debug (Brief)

The containerized service fails to start or crashes immediately after starting.

The `Dockerfile` in the workspace is broken. Fix it so the container starts
correctly and the `/health` endpoint would respond with HTTP 200.

The Planner has the full container specification with the correct base image,
dependencies, environment variables, port mapping, and start command.

Write your findings to `submission/fix_notes.txt`.
