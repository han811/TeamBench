# CROSS1: API Contract Reconciliation

## Goal
The Python client library must correctly communicate with the Go HTTP server.
Discrepancies exist between the API spec, the server implementation, and the client.

## Requirements
1. The Go server is the source of truth — fix the Python client to match server behavior
2. Update `api_spec.yaml` to document the actual contract (matching the server)
3. All integration tests must pass: `pytest tests/`
4. The Go server must still compile: `go build ./...` (do not change Go source)

## Supporting Documents
- `service/main.go`, `service/handlers.go` — Go server (source of truth)
- `client/api.py`, `client/models.py` — Python client (has 3 bugs)
- `api_spec.yaml` — API spec (wrong in 3 places)

## The 3 Discrepancies (find them yourself)
The spec documents one version of the contract; the server implements another.
Read both and reconcile in favor of the server's actual behavior.

## Important
Do NOT modify any Go source files. Only fix:
- `client/api.py` — client request/response handling
- `client/models.py` — client data models
- `client/exceptions.py` — client exception handling
- `api_spec.yaml` — update to match actual server behavior
