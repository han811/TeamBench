# CROSS4: Authentication Federation Gateway

## Goal
Fix 5 security bugs in the authentication gateway that integrates Service A (JWT tokens)
and Service B (HMAC API keys).

## Requirements
1. JWT validation must require RS256 algorithm — reject all other algorithms (especially HS256)
2. API key comparison must use constant-time comparison to prevent timing attacks
3. Role mapping must include all roles from both auth systems
4. Session tokens must expire — set expiry to 3600 seconds
5. JWT validation must verify the `aud` (audience) claim matches the service

## Supporting Documents
- `gateway/auth.py` — Auth validation (contains bugs 1, 2, 4, 5)
- `gateway/rbac.py` — Role mapping (contains bug 3)
- `service_a/keys/` — RSA key pair for JWT verification
- `service_b/secrets.py` — HMAC shared secret
- `tests/attack_vectors.py` — Documents known attack vectors for each bug

## Security Requirements (all mandatory)
- RS256 ONLY: Rejecting HS256 prevents algorithm confusion attacks (CVSS 9.8)
- Constant-time: `hmac.compare_digest` prevents timing-based API key extraction
- Non-zero expiry: Session tokens that never expire allow indefinite impersonation
- Audience validation: Prevents token reuse across services
- Complete role mapping: Missing roles cause authorization failures
