# CROSS3: Protocol Bridge — JSON to Message Translation

## Goal
Fix 4 translation bugs and 2 error mapping bugs in the bridge service that translates
Service A's JSON REST API responses into structured messages for Service B's consumer.

## Requirements
1. int64 fields must be translated as Python int (no truncation to 32-bit)
2. bytes fields must be base64-decoded from JSON strings
3. oneof fields must have exactly one variant set (not multiple)
4. enum fields must be mapped from string names to integer values
5. HTTP 404 from Service A must map to NOT_FOUND error code (5) for Service B
6. HTTP 429 from Service A must map to RESOURCE_EXHAUSTED error code (8) for Service B
7. All tests must pass: `pytest tests/`

## Supporting Documents
- `service_a/models.py` — JSON data models from Service A
- `service_b/schema.py` — Message schema for Service B (proto3-style)
- `bridge/translator.py` — JSON→Message translation (4 bugs)
- `bridge/error_mapper.py` — HTTP status → error code (2 bugs)

## Background

The bridge service sits between Service A (a REST API returning JSON) and Service B
(a queue consumer expecting structured proto3-style messages). Because JSON and proto3
have different type semantics, every field crossing this boundary needs a careful
type conversion.

### Type Semantic Differences

| JSON Type | Proto3 Type | Issue |
|-----------|-------------|-------|
| number    | int64       | JSON numbers lose precision for values > 2^53; must not be masked to 32-bit |
| string    | bytes       | Binary data is base64-encoded in JSON; must be decoded to bytes |
| object    | oneof       | JSON may include multiple keys; proto3 oneof allows exactly one |
| string    | enum        | Enum names in JSON must be converted to integer codes |

### Error Code Mapping

Service A returns HTTP status codes. Service B uses gRPC-style integer error codes:

| HTTP Status | Expected Error Code | Code Number |
|-------------|---------------------|-------------|
| 200         | OK                  | 0           |
| 400         | INVALID_ARGUMENT    | 3           |
| 401/403     | INVALID_ARGUMENT    | 3           |
| 404         | NOT_FOUND           | 5           |
| 429         | RESOURCE_EXHAUSTED  | 8           |
| 5xx         | INTERNAL            | 13          |
