"""
Parameterized generator for CROSS4: Authentication Federation Gateway.

Each seed produces a different gateway scenario (e-commerce / healthcare / finance)
with different service names and HMAC secrets. All 3 seeds embed the same 5 security
bugs so grading is seed-independent. RSA-2048 key pairs are generated fresh per seed
using the `cryptography` library so tests use real RS256 signing.
"""
from __future__ import annotations

import hashlib
import os
import time

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# Per-seed scenario configuration
SCENARIOS = [
    {
        "name": "E-Commerce Gateway",
        "gateway_name": "ShopGateway",
        "service_a_name": "StorefrontAPI",
        "service_b_name": "WarehouseAPI",
        "audience": "shopgateway-service",
        "hmac_secret": "warehouse-hmac-secret-ecommerce-2024",
        "session_secret": "shopgateway-session-secret-xyz",
        "admin_role": "store_admin",
        "user_role": "customer",
        "moderator_role": "support_agent",
        "viewer_role": "guest",
    },
    {
        "name": "Healthcare Gateway",
        "gateway_name": "HealthGateway",
        "service_a_name": "PatientPortal",
        "service_b_name": "RecordsSystem",
        "audience": "healthgateway-service",
        "hmac_secret": "records-hmac-secret-healthcare-2024",
        "session_secret": "healthgateway-session-secret-abc",
        "admin_role": "clinician_admin",
        "user_role": "patient",
        "moderator_role": "nurse",
        "viewer_role": "observer",
    },
    {
        "name": "Finance Gateway",
        "gateway_name": "FinGateway",
        "service_a_name": "BankingAPI",
        "service_b_name": "PaymentProcessor",
        "audience": "fingateway-service",
        "hmac_secret": "payment-hmac-secret-finance-2024",
        "session_secret": "fingateway-session-secret-pqr",
        "admin_role": "bank_admin",
        "user_role": "account_holder",
        "moderator_role": "advisor",
        "viewer_role": "auditor",
    },
]


def _generate_rsa_keypair(seed: int) -> tuple[str, str]:
    """Generate a deterministic RSA-2048 key pair (private_pem, public_pem)."""
    # We generate a real RSA key pair. While RSA key generation isn't directly
    # seeded, we use a fixed set of pre-generated keys indexed by seed so output
    # is deterministic. Each seed has its own distinct key pair.
    PRIVATE_KEYS = [
        # Seed 0 — e-commerce
        b"""-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAtXgmVS9ohWOckhn+3wzJcwtKl/Qyc8H27icQGHo34XCt6eIZ
K+218oOSig+UU/AYnHuCW3sJ2Uidj81Sr6TcgWfcz4h69BWzFG9ZqIqZSWx3BHE6
v/0sdSeMJzS7nIioy1nNKI7PUJWCzlPTbq5XuNtJf1pdI/DbVaLX6Bp3FB7pE5/h
lFtJMbr5wq1IBSBgm4YecDuaGSf7hp/0oJWiYknOqyzjiIRepjxGEhhPgAP8jwP9
6ffZdH80nGQ0Q9erPfEHys0nUgrRjsTNOjnjM4TQl8xz1p/yVKCgmUwNNlEiPyrt
uCeC423VmfJWUJXb/fbTvCeoMtY+l1bAeaTvkwIDAQABAoIBAC88ViYIUBmggynY
kGo45tsGTmVdUCCnlYIKMvtcHN2Wuf5ONyUjHCBDNUqwoXhz38Qjthvf3AFuEG1V
EbfcnvUkNuriaLbOSy3/igQAB8R/8j76xkMhQIhCQg4WgNtPCzjbaDatbbNZJ5JT
aY6+3OCmW+xFdkcbs8wHtlGZSfO3Y8ZB7xKdsqrvXjh9hUlQnptv5LeIeqxKDsRt
aIY31JqvZrqlHTdQ5VEVDp6+sbWTjq1tHCyRcwfXRYpufJoPh1y2Ak/eLICThZbB
inoZJkyUfG4tt54qH84uU7JJ79l9PCsBReSYXqaIYNAwofL27/WOSjoZsgyb41w9
OZqLDOECgYEA32gudcaZGkTaK4wCWpx9/YCXVgzjG6e4uK253/g7WdH7kJzqn926
jgXSW/r1r9h6+kQn0xl0oD/yYFwwFmqbVJRQqDCgQFqPh0Azta791jX6mUvGW9h9
ohTp8895mHLhnVcrnbq7L1Y7qoBgI6RARzqmgFfdzQxtW8WKUgLoqCMCgYEAz/Gt
0XsuDCkCdps3e97E0FLLmsqLSeSZswfG9RqjgQa9Hvnd9hsY3GhAvYnP4nmzWqrY
qWLdLg0IZ2V3BCJBrLFRwLZ0sFxmzbd98JtXqD07U03482xNac0AA8Xw25F2P1D+
LGkyl30QM/IBsilXl9jQj8XkvQblgKDl1xv62dECgYEAr+zCaUxy1BTUGOawE9qX
/EB+6+xKC0UQWZ20eYJoelq41zA6MpnQhnZfKL9/KXI3pUx2b+3jwS2aF/eAhqZ8
myYQPeHMz+CAlekgzzl1+nGXXZAmK71XcYM2mCARiNMuh1BVsGeTb7tgUOu2yVpW
o8CzzO1kZEwc8d+lBN/1hjECgYAM32AsPJzgIdXGM9uebm7umoGCJpGy1FTzcULO
v4Rpo1onxb4I0yqZ0lZXpWVaFsCUl0jsS3N3u1TO2cghWGGKaDuwW1sj48R1bat9
LpChmJDImmYT45tzNj6O/TzoyrtwNfpWE3kPSa2sGYojVk3W15Qpok2Dqh6g9NTl
mRTRUQKBgCebPcqqlLxrefS+M0cvh2tythb6YIamC/le9eLWxskKaNq59xyMaove
l8N+9TWBDj7BLmV463iP8Tw+V0vv6piNJvHGesaBloLGfiAZsV3yeaRan4+C5xpC
XoTmdX8mAGRBXaBBCxBfs3DBGdCh6zLtn/9R2eC2HvPDeff/Ou0i
-----END RSA PRIVATE KEY-----""",
        # Seed 1 — healthcare
        b"""-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAmmwjR0whBwrxehGF8pE3A7PEYsZPnZDKJGNjFxZqCRh+TBOo
jJwrvLhSWB+EhzJO/sdzpMevZv3iNeRMAdJcb27z7qTPaMovasLGeo/pmlPDVMqJ
PDTKVkKP+dD6xhQEQGQSbTDk34tSk49Z88UmL501ksI6l3YrQgMp/glHzMTeA3AY
ZXBaedf6LSdVM5yhgtyc86AUaoVNG7rcERJOAt9xYx/PtnJGCGPOW1E04wKeJVCK
wVho95d3msp6oKO5dZv9Q9fq/QUVEyGsgoJ9BGdH+FCQY5tZ2GS59V1WSzaTydy8
9kEJHSuDSYsJt9IM1OtK3Cm5qBifFAqZy/KBAQIDAQABAoIBAADEflVlo7li/MnI
SgPnZGBclaKPDUjBdjvBkbXE6wCCEmii5WDTiuUcfm5JM9GvNpTOHX1Jb84Bf40Y
hicxKjv0j3pVb+F7tcogTze/POBDP9KNUirOMV5F5OzPNNvksBO4252W02BoEyBA
I2iSh4rPi3tgA0YK9JKWrPACEE0MgHrndrJq2CZ3wQICNZVLBzQ6tIlXJpQcjreB
M97N23AMBSkS74kU95YpUO7Q8YlaUwWaWF6C541R/cb90eVLzVLgdPBGvkErf5ch
9LawpY+TsO2s8BcO9LUHqkGYPxf+z8ookXLujKTEV/XyoRDBdmzbkyOoex+WrLG5
JXvS0xECgYEAysmy5oyweqh42l/DjBTVpTeLmH0o+HBTshe/B5FdyefK+sT6vlVg
A4HFbqAhIrm8zFIpujOSCESy70mTD2fLu2nsDPHL9CcK5KiJu0HixkX3oG2CZSG6
CxOtb3VuQY5WW4HmtJS7M+VuDCmPyiErgwKUq4K2S4Spe2SA7yoz38kCgYEAwvF7
fpA4Qc6yQANx2/q8YOF9moebhRQ3om665ZYe0AS3LHmGoJd9yvilxAXxg0qV4Zl+
dkpeAKUbEwnSU1uo8SJ0KR0NtUiETJrjge+XdiBGyNmx3XVRrRXDDP8+gM10IkzJ
vh2Lquyy351CKd7t6UAqOQCNVuZ9pwH72WpLY3kCgYEAlykKpjixRH1YuM8xoLXX
G7Tv5ddGNwrkGJkC2M1PMDYMZCl5D2/shjCxzuimSpBRX6zPVfEjJe6vwxcA/DbO
8wDd6DhFY9XGlPPc1y0hsdJt57Q5wtEFMUSVv8O1UECdttB5/JnxgZnAEmjYuj9H
g/zkfYSOBnT5MPWV9rFqwaECgYEAkBBFY1LRQFCwCf6Btj+l1zLMz9ZHaCF4u+F4
3RID01aox4VHqIZLwCPg3OxHfu8vtHjqrCBpN7DMQVWQyWmDgDAmB/wglUfx/Wq5
ltyo4fMYXHYEq9R3d6INcx1t42Hx4Sc+L/FFthsWVYqxyp+k0itJCLcPvJi5YyJk
LFgRPoECgYA2ZW+yE4qThpv7guzyKrBcB8JtPyiwgJZo33KV5p/nM7xYHVu9Y50L
hcRoMTHk6r0jocHyAL63V3r5vV9ldi2pGqxgkvK1lphY/cDW4Ym0nHNOb+skX7B/
vjPAcpRIo0IkPE+ewslHWboin5cQjthTFypqp5qMGEqX2WvLZ1/Bjg==
-----END RSA PRIVATE KEY-----""",
        # Seed 2 — finance
        b"""-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAupiU09Pl58Xq2SX/CZt/Ze3RABFLYgW7mQjZuuF4uv/BGO1d
B9+rae/clWZ11x6TC58/ySpvmrXA6z/PnmDCXJQpJkoZwRmpMKi/y3O6PvxSlb+2
86S8oKc2UcuCILpopFgLSkGeVfVsdEWGknIQY+z8kHBOAlkwhtZOPLIfsmAO7AIm
L6DkR/oNxDC5hunLWJkbWuYarebEAaNICW646qJcAddvWdV2G4LCPbI3NVHhF2Hj
GfuxzIqNu+kjq1f3GapT2+b1Te5Ld8/OGuXZ6h8K1nFETKknaD2y7BUahjJ618Hi
4F5sYtMjnIYAQXeBVJ5ObqzRh6CjRmYf9QJgVwIDAQABAoIBAAPkA5JpJC2RgGSX
uLokDmN7MnTsZ2R7Vx6JQzT015YamBWjeWGdJc9XK4PH96QNJKbE4skYg+w3Zvbg
xTz5qoPQqQz91YyjstXrZthgqN0AWN57eV6aLD6zTdwlwKhbCqyGk3GwbZNAQ0sn
Wfd6vmG/AsMmPFIrNupQ1J/KXQPUmLXSG9ZCNKcaTBbpd5FoKZ/ZVzVAyi/CJgNF
uAYUcP8P5YufTPC1EjXp7elmFUbzgICNu7pEBNHdJTgpZoC6tktJd1PwcMeCY9b8
pzqjmFmrpsRUMgSmLUY3XHEhztP5MFxvtRL0Lyo9lnLw0cjZswhPQIlhwn81aiZO
bGvCj80CgYEA/C+jJT1gYe1bohyrh8kF7f4orxtGGbRUtj5YbHSt2dc8eUgjUK/7
ZWx2WhPA97EmqzMZtli750gvBrb2IlmBOXSoL21S9zRfcly4S75licTnPrYLPZ5T
Giay5LEkjV+ecul2XMHX3P/41AWi1IMGROSeqHGQo58Bw9jDpuhuR70CgYEAvWsB
fdVMy+u5FJiFwpRB50e2Mj/QEVusgvV0xDOHz+aM1QvJjvjoOYbWfFXH6B2kPafq
E9a/Qoe8ddH4aD0Y9gi31ywFqr4ytIEBjMwwUigHGchbGGnrqDTHGXLQVh0dSdnc
tdxYo7oDHZB3sHFC5DLfXG7FFscybfPZmhSLL6MCgYEAhxpmRr8Y8Z2dp73AT2Bs
otG0rgrohUDM2U2RRZlEwh3DMh5pfQKqpe1zglJu4MOxOaqIrd3f3MoZF3nRZxmY
V1Wd/LqO5gzSzYvK2BlKgIJSeJBCeWJmlu4AjPAx6uM9GcblOFBI+wbPIZdbYopH
Q4VPUmJ04JOA+JEaUELZQekCgYADJzvgH2Pm5SawnBVl9tfeBMiYr41ELLWDfJiU
B5OUN29SwJ57XdNn2cHKUhdA2vV3/UqdR+7pKZ9Ois9K1PGMbvq4f0gc3ouzi44+
DMwlIft0R2yUzHaa1z4VQ18Kf/OT3ieZc3CaUSdqH5SOgGQvrlUfkcyAI5LIV83g
jcT/ZwKBgQCBTyHaKChCCL3C0YDpFohE/sGJ9MAcAmxdzFXAI5+VzYeOxVJbzxQ5
ucY6MuiHVrY7QiOZh+wlKGPc2luieV+fiAmsWGaJFy4M6l6yho1R29ddNftEEfkr
EEAIlI68Z4lrvNaLcU6D4ebgBxiFptEziJkmDdjnIAXxwIUiljECHA==
-----END RSA PRIVATE KEY-----""",
    ]

    idx = seed % len(PRIVATE_KEYS)
    priv_pem_bytes = PRIVATE_KEYS[idx]

    # Derive public key from private key using cryptography library
    from cryptography.hazmat.primitives.serialization import load_pem_private_key, Encoding, PublicFormat
    priv_key = load_pem_private_key(priv_pem_bytes, password=None)
    pub_pem = priv_key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode()
    priv_pem = priv_pem_bytes.decode()
    return priv_pem, pub_pem


class Generator(TaskGenerator):
    task_id = "CROSS4_auth_federation"
    domain = "Security"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        scenario = SCENARIOS[seed % len(SCENARIOS)]
        priv_pem, pub_pem = _generate_rsa_keypair(seed)

        workspace_files = self._make_workspace(scenario, priv_pem, pub_pem, seed)

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", "CROSS4_auth_federation")
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id="CROSS4_auth_federation",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "bugs_fixed": ["B1_algorithm_confusion", "B2_timing_attack",
                               "B3_role_mapping", "B4_session_expiry", "B5_audience_validation"],
                "scenario": scenario["name"],
                "seed": seed,
            },
            workspace_files=workspace_files,
            metadata={
                "difficulty": "hard",
                "category": "Security",
                "scenario": scenario["name"],
                "bugs": 5,
            },
        )

    def _make_workspace(self, sc: dict, priv_pem: str, pub_pem: str, seed: int) -> dict:
        files = {}

        audience = sc["audience"]
        hmac_secret = sc["hmac_secret"]
        session_secret = sc["session_secret"]
        svc_a = sc["service_a_name"]
        svc_b = sc["service_b_name"]
        gw = sc["gateway_name"]
        admin_role = sc["admin_role"]
        user_role = sc["user_role"]
        mod_role = sc["moderator_role"]
        viewer_role = sc["viewer_role"]

        # ----------------------------------------------------------------
        # gateway/__init__.py
        # ----------------------------------------------------------------
        files["gateway/__init__.py"] = ""

        # ----------------------------------------------------------------
        # gateway/config.py
        # ----------------------------------------------------------------
        files["gateway/config.py"] = f'''"""
{gw} configuration.
"""

# JWT audience claim — all tokens must be issued for this audience
GATEWAY_AUDIENCE = "{audience}"

# Session token signing secret (symmetric HS256 for internal sessions only)
SESSION_SECRET = "{session_secret}"

# Service names
SERVICE_A_NAME = "{svc_a}"
SERVICE_B_NAME = "{svc_b}"
GATEWAY_NAME = "{gw}"
'''

        # ----------------------------------------------------------------
        # gateway/auth.py  — contains all 5 bugs
        # ----------------------------------------------------------------
        files["gateway/auth.py"] = f'''"""
{gw} authentication module.

Validates tokens from {svc_a} (JWT/RS256) and {svc_b} (HMAC API keys),
and issues internal session tokens.

KNOWN BUGS (to be fixed):
  Bug 1: JWT decode accepts HS256 — algorithm confusion attack possible
  Bug 2: API key comparison uses == — timing attack possible
  Bug 4: Session tokens never expire (exp=0)
  Bug 5: JWT decode does not validate audience claim
"""
import hmac as _hmac
import hashlib
import time

import jwt

from gateway.config import GATEWAY_AUDIENCE, SESSION_SECRET


def validate_jwt(token: str, public_key_pem: str) -> dict:
    """
    Validate a JWT token from {svc_a}.

    The token must be signed with RS256 using the service's RSA private key.
    Returns the decoded payload if valid, raises jwt.InvalidTokenError otherwise.
    """
    # BUG 1: HS256 accepted — enables algorithm confusion attack.
    # An attacker can sign a token with the public key used as an HMAC secret.
    # Fix: use algorithms=["RS256"] only.
    #
    # BUG 5: audience=None — tokens for other services are accepted.
    # Fix: pass audience=GATEWAY_AUDIENCE.
    payload = jwt.decode(
        token,
        public_key_pem,
        algorithms=["HS256", "RS256"],
        audience=None,
    )
    return payload


def validate_api_key(provided_key: str, stored_hmac: str) -> bool:
    """
    Validate an API key from {svc_b}.

    The stored value is an HMAC-SHA256 of the raw key using the shared secret.
    Returns True if the key is valid.
    """
    import service_b.secrets as svc_secrets
    expected = _hmac.new(
        svc_secrets.HMAC_SECRET.encode(),
        provided_key.encode(),
        hashlib.sha256,
    ).hexdigest()
    # BUG 2: timing-unsafe string comparison — allows byte-by-byte extraction.
    # Fix: use _hmac.compare_digest(expected, stored_hmac)
    return expected == stored_hmac


def create_session_token(user_id: str, roles: list) -> str:
    """
    Issue an internal session token after successful auth from either service.

    The token is signed with HS256 using SESSION_SECRET and contains:
    - sub: user identifier
    - roles: list of gateway roles
    - iat: issued-at timestamp
    - exp: expiry timestamp (BUG 4: currently set to 0 — never expires)
    """
    payload = {{
        "sub": user_id,
        "roles": roles,
        "iat": int(time.time()),
        # BUG 4: exp=0 means the token never expires.
        # Fix: "exp": int(time.time()) + 3600
        "exp": 0,
    }}
    return jwt.encode(payload, SESSION_SECRET, algorithm="HS256")
'''

        # ----------------------------------------------------------------
        # gateway/rbac.py  — contains Bug 3
        # ----------------------------------------------------------------
        files["gateway/rbac.py"] = f'''"""
{gw} role-based access control.

Maps roles from {svc_a} and {svc_b} to unified gateway roles.

BUG 3: Missing "admin" -> "superuser" mapping.
       Admin users from {svc_a} will be treated as ordinary members.
"""

# Unified role map: service role -> gateway role
ROLE_MAP = {{
    "{user_role}": "member",
    "{mod_role}": "staff",
    # BUG 3: Missing "admin": "superuser" entry.
    # Admin users from {svc_a} silently fall through to the default "member" role.
    "{viewer_role}": "readonly",
    "user": "member",
    "moderator": "staff",
    "viewer": "readonly",
    # Note: "admin" -> "superuser" is intentionally missing here (the bug).
    # Fix: add the line:  "admin": "superuser",
}}


def map_role(service_role: str) -> str:
    """Translate a service-specific role to a unified gateway role."""
    return ROLE_MAP.get(service_role, "member")


def get_permissions(gateway_role: str) -> list:
    """Return allowed permissions for a gateway role."""
    PERMS = {{
        "superuser": ["read", "write", "delete", "admin"],
        "staff": ["read", "write"],
        "member": ["read"],
        "readonly": ["read"],
    }}
    return PERMS.get(gateway_role, [])
'''

        # ----------------------------------------------------------------
        # gateway/session.py
        # ----------------------------------------------------------------
        files["gateway/session.py"] = f'''"""
Session helpers for {gw}.
"""
import jwt

from gateway.config import SESSION_SECRET
from gateway.auth import create_session_token
from gateway.rbac import map_role


def authenticate_jwt_user(token: str, public_key_pem: str) -> str:
    """Full JWT auth flow: validate -> map roles -> issue session token."""
    from gateway.auth import validate_jwt
    payload = validate_jwt(token, public_key_pem)
    service_roles = payload.get("roles", [payload.get("role", "user")])
    if isinstance(service_roles, str):
        service_roles = [service_roles]
    gateway_roles = [map_role(r) for r in service_roles]
    return create_session_token(payload["sub"], gateway_roles)


def authenticate_api_key_user(user_id: str, provided_key: str, stored_hmac: str) -> str:
    """Full API key auth flow: validate -> assign roles -> issue session token."""
    from gateway.auth import validate_api_key
    if not validate_api_key(provided_key, stored_hmac):
        raise ValueError("Invalid API key")
    # API key users get member role by default
    return create_session_token(user_id, ["member"])


def decode_session_token(session_token: str) -> dict:
    """Decode and verify an internal session token."""
    return jwt.decode(session_token, SESSION_SECRET, algorithms=["HS256"])
'''

        # ----------------------------------------------------------------
        # gateway/middleware.py
        # ----------------------------------------------------------------
        files["gateway/middleware.py"] = f'''"""
Request authentication middleware for {gw}.

Dispatches to the correct auth backend based on Authorization header format:
  Bearer <jwt>   -> JWT auth via {svc_a}
  ApiKey <key>   -> API key auth via {svc_b}
"""
from gateway.session import authenticate_jwt_user, authenticate_api_key_user


_PUBLIC_KEY_PEM = None  # Loaded at startup


def set_public_key(pem: str) -> None:
    global _PUBLIC_KEY_PEM
    _PUBLIC_KEY_PEM = pem


def authenticate_request(auth_header: str, api_key_store: dict | None = None) -> dict:
    """
    Authenticate a request from its Authorization header.

    Returns a dict with: session_token, user_id, roles
    Raises ValueError on auth failure.
    """
    if not auth_header:
        raise ValueError("Missing Authorization header")

    if auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer "):]
        if _PUBLIC_KEY_PEM is None:
            raise RuntimeError("Public key not configured")
        session = authenticate_jwt_user(token, _PUBLIC_KEY_PEM)
        return {{"session_token": session, "auth_method": "jwt"}}

    if auth_header.startswith("ApiKey "):
        parts = auth_header[len("ApiKey "):].split(":", 1)
        if len(parts) != 2:
            raise ValueError("ApiKey format: ApiKey user_id:raw_key")
        user_id, raw_key = parts
        store = api_key_store or {{}}
        stored_hmac = store.get(user_id)
        if not stored_hmac:
            raise ValueError(f"Unknown API key user: {{user_id}}")
        session = authenticate_api_key_user(user_id, raw_key, stored_hmac)
        return {{"session_token": session, "auth_method": "apikey"}}

    raise ValueError("Unsupported auth scheme")
'''

        # ----------------------------------------------------------------
        # service_a/__init__.py
        # ----------------------------------------------------------------
        files["service_a/__init__.py"] = ""

        # ----------------------------------------------------------------
        # service_a/app.py
        # ----------------------------------------------------------------
        files["service_a/app.py"] = f'''"""
{svc_a}: JWT-authenticated service.

Issues JWT tokens signed with RS256 for authenticated users.
"""
import time
import jwt
from pathlib import Path


def _load_private_key() -> str:
    key_path = Path(__file__).parent / "keys" / "private.pem"
    return key_path.read_text()


def _load_public_key() -> str:
    key_path = Path(__file__).parent / "keys" / "public.pem"
    return key_path.read_text()


def issue_jwt(user_id: str, roles: list, audience: str) -> str:
    """Issue a JWT token for a user. Signed with RS256."""
    private_key = _load_private_key()
    payload = {{
        "sub": user_id,
        "roles": roles,
        "aud": audience,
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
        "iss": "{svc_a}",
    }}
    return jwt.encode(payload, private_key, algorithm="RS256")


def get_public_key() -> str:
    """Return the RS256 public key PEM for token verification."""
    return _load_public_key()
'''

        # ----------------------------------------------------------------
        # service_a/keys/  (RSA key pair)
        # ----------------------------------------------------------------
        files["service_a/keys/private.pem"] = priv_pem
        files["service_a/keys/public.pem"] = pub_pem

        # ----------------------------------------------------------------
        # service_b/__init__.py
        # ----------------------------------------------------------------
        files["service_b/__init__.py"] = ""

        # ----------------------------------------------------------------
        # service_b/secrets.py
        # ----------------------------------------------------------------
        files["service_b/secrets.py"] = f'''"""
{svc_b}: Shared HMAC secret for API key validation.

The gateway uses this secret to verify API keys via HMAC-SHA256.
"""

HMAC_SECRET = "{hmac_secret}"
SERVICE_NAME = "{svc_b}"
'''

        # ----------------------------------------------------------------
        # service_b/app.py
        # ----------------------------------------------------------------
        files["service_b/app.py"] = f'''"""
{svc_b}: HMAC API key authenticated service.

Generates API keys as HMAC-SHA256(secret, user_id+salt).
"""
import hmac
import hashlib
import secrets

from service_b.secrets import HMAC_SECRET


def generate_api_key(user_id: str) -> tuple[str, str]:
    """
    Generate an API key for a user.

    Returns (raw_key, stored_hmac) where stored_hmac is saved server-side
    and raw_key is given to the user.
    """
    raw_key = secrets.token_hex(32)
    stored_hmac = hmac.new(
        HMAC_SECRET.encode(),
        raw_key.encode(),
        hashlib.sha256,
    ).hexdigest()
    return raw_key, stored_hmac


def verify_api_key(raw_key: str, stored_hmac: str) -> bool:
    """Verify an API key using constant-time comparison (reference implementation)."""
    expected = hmac.new(
        HMAC_SECRET.encode(),
        raw_key.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, stored_hmac)
'''

        # ----------------------------------------------------------------
        # tests/__init__.py
        # ----------------------------------------------------------------
        files["tests/__init__.py"] = ""

        # ----------------------------------------------------------------
        # tests/conftest.py
        # ----------------------------------------------------------------
        files["tests/conftest.py"] = f'''"""
Shared fixtures for CROSS4 test suite.
"""
import hmac as _hmac
import hashlib
import time
from pathlib import Path

import jwt
import pytest

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gateway.config import GATEWAY_AUDIENCE, SESSION_SECRET
from service_a.app import issue_jwt, get_public_key
from service_b.app import generate_api_key


@pytest.fixture
def public_key_pem():
    return get_public_key()


@pytest.fixture
def private_key_pem():
    key_path = Path(__file__).parent.parent / "service_a" / "keys" / "private.pem"
    return key_path.read_text()


@pytest.fixture
def valid_jwt_token():
    """A valid RS256 JWT for a regular user."""
    return issue_jwt("user1", ["user"], GATEWAY_AUDIENCE)


@pytest.fixture
def admin_jwt_token():
    """A valid RS256 JWT for an admin user."""
    return issue_jwt("admin1", ["admin"], GATEWAY_AUDIENCE)


@pytest.fixture
def api_key_pair():
    """A valid API key pair (raw_key, stored_hmac)."""
    return generate_api_key("svc_user1")


@pytest.fixture
def gateway_auth():
    """The gateway.auth module (for black-box testing)."""
    import gateway.auth as auth
    return auth


@pytest.fixture
def gateway_rbac():
    """The gateway.rbac module."""
    import gateway.rbac as rbac
    return rbac
'''

        # ----------------------------------------------------------------
        # tests/test_jwt_auth.py
        # ----------------------------------------------------------------
        files["tests/test_jwt_auth.py"] = f'''"""
JWT authentication tests for CROSS4.
Tests that the gateway correctly validates RS256 JWT tokens.
"""
import time
import jwt
import pytest

from gateway.config import GATEWAY_AUDIENCE, SESSION_SECRET
from gateway.auth import validate_jwt
from service_a.app import issue_jwt, get_public_key


def test_valid_rs256_jwt_accepted():
    """A correctly signed RS256 token is accepted."""
    token = issue_jwt("user1", ["user"], GATEWAY_AUDIENCE)
    pub = get_public_key()
    payload = validate_jwt(token, pub)
    assert payload["sub"] == "user1"


def test_jwt_returns_roles():
    """JWT payload roles are returned correctly."""
    token = issue_jwt("admin1", ["admin", "user"], GATEWAY_AUDIENCE)
    pub = get_public_key()
    payload = validate_jwt(token, pub)
    assert "admin" in payload["roles"] or "admin" in payload.get("roles", [])


def test_expired_jwt_rejected():
    """An expired JWT is rejected."""
    from pathlib import Path
    priv = (Path(__file__).parent.parent / "service_a" / "keys" / "private.pem").read_text()
    payload = {{
        "sub": "user1",
        "roles": ["user"],
        "aud": GATEWAY_AUDIENCE,
        "iat": int(time.time()) - 7200,
        "exp": int(time.time()) - 3600,
        "iss": "TestService",
    }}
    token = jwt.encode(payload, priv, algorithm="RS256")
    pub = get_public_key()
    with pytest.raises(Exception):
        validate_jwt(token, pub)


def test_invalid_signature_rejected():
    """A token with a tampered payload is rejected."""
    from pathlib import Path
    import cryptography.hazmat.primitives.asymmetric.rsa as _rsa
    from cryptography.hazmat.primitives import serialization

    # Generate a different RSA key — signature should be invalid
    other_key = _rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_priv = other_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode()
    payload = {{
        "sub": "attacker",
        "roles": ["admin"],
        "aud": GATEWAY_AUDIENCE,
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }}
    forged = jwt.encode(payload, other_priv, algorithm="RS256")
    pub = get_public_key()
    with pytest.raises(Exception):
        validate_jwt(forged, pub)


def test_wrong_audience_rejected():
    """A token with a different audience claim is rejected (Bug 5 fix)."""
    from pathlib import Path
    priv = (Path(__file__).parent.parent / "service_a" / "keys" / "private.pem").read_text()
    payload = {{
        "sub": "user1",
        "roles": ["user"],
        "aud": "other-service",   # Wrong audience
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }}
    token = jwt.encode(payload, priv, algorithm="RS256")
    pub = get_public_key()
    with pytest.raises(Exception):
        validate_jwt(token, pub)
'''

        # ----------------------------------------------------------------
        # tests/test_apikey_auth.py
        # ----------------------------------------------------------------
        files["tests/test_apikey_auth.py"] = f'''"""
API key authentication tests for CROSS4.
Tests constant-time comparison and correct HMAC validation.
"""
import hmac
import hashlib
import pytest

from gateway.auth import validate_api_key
from service_b.app import generate_api_key
from service_b.secrets import HMAC_SECRET


def test_valid_api_key_accepted():
    """A correct API key is accepted."""
    raw_key, stored_hmac = generate_api_key("user1")
    assert validate_api_key(raw_key, stored_hmac) is True


def test_wrong_api_key_rejected():
    """A wrong API key is rejected."""
    _, stored_hmac = generate_api_key("user1")
    assert validate_api_key("wrong_key_value", stored_hmac) is False


def test_tampered_hmac_rejected():
    """A correct key with a tampered stored HMAC is rejected."""
    raw_key, _ = generate_api_key("user1")
    bad_hmac = "a" * 64  # Wrong HMAC value
    assert validate_api_key(raw_key, bad_hmac) is False


def test_compare_digest_used(gateway_auth):
    """Verify hmac.compare_digest is used (not ==) in validate_api_key."""
    import ast, inspect
    src = inspect.getsource(gateway_auth.validate_api_key)
    tree = ast.parse(src)
    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "compare_digest":
            found = True
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "compare_digest":
                found = True
    assert found, "hmac.compare_digest must be used in validate_api_key"


def test_different_users_different_hmac():
    """Different users get different stored HMACs even with same raw key style."""
    raw1, hmac1 = generate_api_key("alice")
    raw2, hmac2 = generate_api_key("bob")
    # Keys are random so they should differ with overwhelming probability
    assert raw1 != raw2
    assert hmac1 != hmac2
'''

        # ----------------------------------------------------------------
        # tests/test_rbac.py
        # ----------------------------------------------------------------
        files["tests/test_rbac.py"] = f'''"""
Role mapping tests for CROSS4.
Tests that all roles (including admin) are correctly translated.
"""
import pytest

from gateway.rbac import map_role, get_permissions


def test_admin_maps_to_superuser():
    """Admin role must map to superuser (Bug 3 fix)."""
    assert map_role("admin") == "superuser", (
        "admin must map to superuser — add \\"admin\\": \\"superuser\\" to ROLE_MAP"
    )


def test_user_maps_to_member():
    """Regular user role maps to member."""
    result = map_role("user")
    assert result == "member"


def test_moderator_maps_to_staff():
    """Moderator role maps to staff."""
    result = map_role("moderator")
    assert result == "staff"


def test_viewer_maps_to_readonly():
    """Viewer role maps to readonly."""
    result = map_role("viewer")
    assert result == "readonly"


def test_unknown_role_defaults_to_member():
    """Unknown roles default to member."""
    result = map_role("some_unknown_role")
    assert result == "member"


def test_superuser_has_admin_permission():
    """Superuser role has admin permission."""
    perms = get_permissions("superuser")
    assert "admin" in perms


def test_member_has_no_admin_permission():
    """Member role does not have admin permission."""
    perms = get_permissions("member")
    assert "admin" not in perms
'''

        # ----------------------------------------------------------------
        # tests/test_session.py
        # ----------------------------------------------------------------
        files["tests/test_session.py"] = f'''"""
Session token expiry tests for CROSS4.
Tests that session tokens expire correctly (Bug 4 fix).
"""
import time
import jwt
import pytest

from gateway.auth import create_session_token
from gateway.config import SESSION_SECRET


def test_session_token_has_expiry():
    """Session token must have a non-zero exp claim (Bug 4 fix)."""
    token = create_session_token("user1", ["member"])
    payload = jwt.decode(token, options={{"verify_signature": False, "verify_exp": False}})
    exp = payload.get("exp", 0)
    assert exp > 0, f"Session token exp must be > 0, got {{exp}}"


def test_session_token_expires_within_two_hours():
    """Session token must expire within 2 hours."""
    token = create_session_token("user1", ["member"])
    payload = jwt.decode(token, options={{"verify_signature": False, "verify_exp": False}})
    exp = payload.get("exp", 0)
    now = int(time.time())
    assert exp > now, "Session token is already expired"
    assert exp <= now + 7200, f"Session expiry too far in the future: {{exp - now}}s"


def test_session_token_expires_around_one_hour():
    """Session token should expire approximately 3600 seconds from now."""
    before = int(time.time())
    token = create_session_token("user1", ["member"])
    after = int(time.time())
    payload = jwt.decode(token, options={{"verify_signature": False, "verify_exp": False}})
    exp = payload.get("exp", 0)
    # Allow ±5 seconds for timing jitter
    assert before + 3590 <= exp <= after + 3610, (
        f"Expected exp ~3600s from now, got {{exp - before}}s"
    )


def test_session_token_contains_roles():
    """Session token must carry the user's roles."""
    token = create_session_token("admin1", ["superuser"])
    payload = jwt.decode(token, options={{"verify_signature": False, "verify_exp": False}})
    assert "superuser" in payload.get("roles", [])


def test_session_token_contains_sub():
    """Session token must carry the user identifier."""
    token = create_session_token("user42", ["member"])
    payload = jwt.decode(token, options={{"verify_signature": False, "verify_exp": False}})
    assert payload.get("sub") == "user42"
'''

        # ----------------------------------------------------------------
        # tests/test_federation.py
        # ----------------------------------------------------------------
        files["tests/test_federation.py"] = f'''"""
End-to-end federation tests for CROSS4.
Tests the full auth flow from service token to gateway session token.
"""
import time
import jwt
import pytest

from gateway.config import GATEWAY_AUDIENCE, SESSION_SECRET
from gateway.session import authenticate_jwt_user, authenticate_api_key_user
from service_a.app import issue_jwt, get_public_key
from service_b.app import generate_api_key


def test_jwt_user_gets_session_token():
    """A valid JWT user gets a gateway session token."""
    token = issue_jwt("user1", ["user"], GATEWAY_AUDIENCE)
    pub = get_public_key()
    session = authenticate_jwt_user(token, pub)
    assert session is not None
    assert len(session) > 10


def test_admin_jwt_gets_superuser_session():
    """An admin JWT user gets a superuser session token (requires Bug 3 fix)."""
    token = issue_jwt("admin1", ["admin"], GATEWAY_AUDIENCE)
    pub = get_public_key()
    session = authenticate_jwt_user(token, pub)
    payload = jwt.decode(session, options={{"verify_signature": False, "verify_exp": False}})
    assert "superuser" in payload.get("roles", []), (
        "Admin user must be mapped to superuser role"
    )


def test_api_key_user_gets_session_token():
    """A valid API key user gets a gateway session token."""
    raw_key, stored_hmac = generate_api_key("svc_user1")
    session = authenticate_api_key_user("svc_user1", raw_key, stored_hmac)
    assert session is not None
    payload = jwt.decode(session, options={{"verify_signature": False, "verify_exp": False}})
    assert payload["sub"] == "svc_user1"


def test_invalid_api_key_raises():
    """An invalid API key raises ValueError."""
    raw_key, stored_hmac = generate_api_key("svc_user1")
    with pytest.raises(ValueError):
        authenticate_api_key_user("svc_user1", "wrong_key", stored_hmac)


def test_session_token_verifiable():
    """Session tokens issued by the gateway can be decoded."""
    token = issue_jwt("user1", ["user"], GATEWAY_AUDIENCE)
    pub = get_public_key()
    session = authenticate_jwt_user(token, pub)
    from gateway.session import decode_session_token
    # decode_session_token uses verify_exp=True, so token must not be expired
    # We re-decode without exp check since the session was just created
    payload = jwt.decode(session, options={{"verify_signature": False, "verify_exp": False}})
    assert "sub" in payload
    assert "roles" in payload
    exp = payload.get("exp", 0)
    assert exp > int(time.time()), "Fresh session token must not be expired"
'''

        # ----------------------------------------------------------------
        # tests/attack_vectors.py  — adversarial tests (must PASS after fixes)
        # ----------------------------------------------------------------
        files["tests/attack_vectors.py"] = f'''"""
Attack vector tests for CROSS4.

These tests attempt known attacks against the auth gateway.
AFTER all 5 bugs are fixed, every test in this file should PASS
(meaning: each attack is successfully blocked).
"""
import time
from pathlib import Path

import jwt
import pytest

from gateway.config import GATEWAY_AUDIENCE, SESSION_SECRET
from gateway.auth import validate_jwt, validate_api_key, create_session_token
from service_a.app import get_public_key, issue_jwt
from service_b.app import generate_api_key


# ---------------------------------------------------------------------------
# Attack 1: Algorithm confusion (CVE pattern — Bug 1)
# ---------------------------------------------------------------------------

def test_algorithm_confusion_attack_blocked():
    """
    Algorithm confusion attack: sign a JWT with the RS256 public key used as
    an HMAC-SHA256 secret. If the gateway accepts HS256, this forged token
    would be accepted. After Bug 1 fix, it must be rejected.

    PyJWT 2.x refuses to sign HS256 with a PEM key directly (key safety check),
    so we build the forged token manually using base64url + hmac.
    """
    import base64
    import json
    import hmac as _hmac_mod
    import hashlib

    public_key_pem = get_public_key()

    # Build a forged HS256 JWT manually (bypassing PyJWT's key safety check)
    header = base64.urlsafe_b64encode(
        json.dumps({{"alg": "HS256", "typ": "JWT"}}).encode()
    ).rstrip(b"=")
    body = base64.urlsafe_b64encode(
        json.dumps({{
            "sub": "attacker",
            "roles": ["admin"],
            "aud": GATEWAY_AUDIENCE,
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        }}).encode()
    ).rstrip(b"=")
    signing_input = header + b"." + body
    # Use the raw PEM bytes as HMAC-SHA256 secret (the algorithm confusion attack)
    sig = _hmac_mod.new(
        public_key_pem.encode(), signing_input, hashlib.sha256
    ).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=")
    forged_token = (signing_input + b"." + sig_b64).decode()

    with pytest.raises(Exception):
        validate_jwt(forged_token, public_key_pem)


# ---------------------------------------------------------------------------
# Attack 2: Session token never-expiry (Bug 4)
# ---------------------------------------------------------------------------

def test_session_token_cannot_be_eternal():
    """
    A session token with exp=0 (or far future) must not be issued.
    After Bug 4 fix, tokens must expire within 2 hours.
    """
    token = create_session_token("user1", ["member"])
    payload = jwt.decode(token, options={{"verify_signature": False, "verify_exp": False}})
    exp = payload.get("exp", 0)
    now = int(time.time())
    assert exp > 0, "exp must be non-zero (eternal tokens are a security bug)"
    assert exp < now + 7200, f"exp is too far in the future: {{exp - now}}s"


# ---------------------------------------------------------------------------
# Attack 3: Cross-service token reuse (Bug 5 — audience)
# ---------------------------------------------------------------------------

def test_cross_service_token_reuse_blocked():
    """
    A token issued for a different service (different audience) must be rejected.
    After Bug 5 fix, the audience claim is validated.
    """
    priv = (Path(__file__).parent.parent / "service_a" / "keys" / "private.pem").read_text()
    payload = {{
        "sub": "user1",
        "roles": ["user"],
        "aud": "other-microservice",  # Wrong audience
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }}
    cross_token = jwt.encode(payload, priv, algorithm="RS256")
    pub = get_public_key()
    with pytest.raises(Exception):
        validate_jwt(cross_token, pub)


# ---------------------------------------------------------------------------
# Attack 4: Privilege escalation via missing role mapping (Bug 3)
# ---------------------------------------------------------------------------

def test_admin_not_silently_downgraded():
    """
    An admin user must not be silently downgraded to 'member'.
    After Bug 3 fix, 'admin' maps to 'superuser'.
    """
    from gateway.rbac import map_role
    result = map_role("admin")
    assert result == "superuser", (
        f"admin must map to superuser, not {{result!r}} — this is a privilege escalation bug"
    )


# ---------------------------------------------------------------------------
# Attack 5: API key timing oracle (Bug 2)
# ---------------------------------------------------------------------------

def test_api_key_uses_constant_time_comparison():
    """
    The API key comparison must use hmac.compare_digest (constant-time).
    After Bug 2 fix, == is replaced with compare_digest.
    """
    import ast, inspect
    import gateway.auth as auth_module
    src = inspect.getsource(auth_module.validate_api_key)
    tree = ast.parse(src)

    uses_compare_digest = False
    uses_plain_eq = False

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "compare_digest":
            uses_compare_digest = True
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "compare_digest":
                uses_compare_digest = True
        # Detect bare == comparison between computed hmac and stored value
        if isinstance(node, ast.Compare):
            for op in node.ops:
                if isinstance(op, ast.Eq):
                    # Check if either side looks like an hmac result
                    left_src = ast.unparse(node.left)
                    if "hexdigest" in left_src or "digest" in left_src:
                        uses_plain_eq = True

    assert uses_compare_digest, "hmac.compare_digest must be used in validate_api_key"
    assert not uses_plain_eq, "Plain == comparison on HMAC digest must be replaced with compare_digest"
'''

        # ----------------------------------------------------------------
        # requirements.txt
        # ----------------------------------------------------------------
        files["requirements.txt"] = "PyJWT>=2.0\ncryptography>=3.0\npytest>=7.0\n"

        return files
