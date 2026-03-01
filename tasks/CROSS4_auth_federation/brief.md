# CROSS4: Auth Federation (Brief)

Fix 5 security bugs in the auth gateway. The Planner has analyzed the auth flow
across all three components (gateway, service_a, service_b) and identified each bug's
location and fix.

Follow the Planner's security analysis precisely — the bugs interact (e.g., fixing
expiry without audience validation leaves a different attack vector open).

Run `pytest tests/` to verify all fixes.
