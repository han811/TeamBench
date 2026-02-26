# S5: Error Handling — Specification (Static Reference)

> **Note**: This is the static reference spec. The actual spec is generated
> per-seed by `generators/gen_s5_error_handling.py`. The generated spec
> contains the exact error code taxonomy, HTTP statuses, retry configuration,
> and logging requirements for the specific seed instance.

## TNI Pattern E: Spec/Brief Divergence

- **Brief** says: "The application lacks proper error handling. Add it."
- **Spec** contains: complete error code taxonomy, specific HTTP statuses,
  recovery actions per error type, retry logic parameters, logging field
  requirements, and session management instructions.

## Error Code Taxonomy (Canonical)

| Code | Name | HTTP Status | Recovery Action |
|------|------|-------------|-----------------|
| E001 | InvalidInput | 400 | Validate + return field-level details |
| E002 | NotFound | 404 | Return resource ID in message |
| E003 | RateLimit | 429 | Add `Retry-After` header |
| E004 | DatabaseError | 503 | Retry 3x with exponential backoff |
| E005 | AuthError | 401 | Clear session (`user_id`, `token`) |
| E006 | Timeout | 504 | Abort upstream call |
| E007 | PayloadTooLarge | 413 | Reject with `max_size` info |
| E008 | Conflict | 409 | Return conflict details |

Seeds use 5–8 of these error codes selected deterministically.

## Application Types

Seeds cycle through:
- `api_server` — REST CRUD API
- `file_processor` — document processing service
- `data_importer` — batch import service
- `webhook_handler` — external event receiver
