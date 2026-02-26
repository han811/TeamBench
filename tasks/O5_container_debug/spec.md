# O5: Container Debug

## Goal

Fix the broken `Dockerfile` in the workspace so the containerized service
starts correctly and passes all static correctness checks.

The service currently fails to start due to multiple Dockerfile bugs.
The application server file and `app_config.json` are correct — only
the `Dockerfile` needs to be fixed.

## Note on Grading

Because we cannot run Docker in the grading environment, grading is done
**statically**: the grader parses the Dockerfile and config files to verify
correctness. This means the fix must be syntactically and semantically correct
even if not executed.

## Per-Seed Specification

Each seed instance has its own `spec.md` generated at runtime (via the
parameterized generator). The per-seed spec contains:

- Exact base image required
- Exact packages to install and the RUN command
- Required ENV variable names and values
- Correct EXPOSE port
- Correct CMD / ENTRYPOINT
- List of bugs injected in the Dockerfile

## Hard Requirements (All Seeds)

1. `FROM` must use the exact correct base image for the app type.
2. `WORKDIR /app` must be set.
3. `COPY` must include the application files.
4. `RUN` must correctly install all required dependencies.
5. `EXPOSE` must declare the correct service port.
6. All required `ENV` vars must be declared in the Dockerfile.
7. `CMD` or `ENTRYPOINT` must match the correct start command.
8. `HEALTHCHECK` must be defined with the correct port.
9. `app_config.json` must not be modified.
10. Write a `submission/fix_notes.txt` describing each bug fixed.

## Trap Design (TNI Pattern A+B)

The brief only says the container fails to start. The Dockerfile contains
misleading comments suggesting the current configuration is correct.
The full requirements are only in the per-seed spec (this document at
runtime) — the Executor alone cannot fix all bugs without the Planner's spec.
