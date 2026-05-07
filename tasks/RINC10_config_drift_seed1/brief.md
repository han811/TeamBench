# RINC10: Config Drift Fix (Brief)

The FeatureFlagService is misbehaving in production. Monitoring shows:
checkout conversion 60% below normal — new checkout flow disabled in production

Engineering suspects the production config has diverged from version control.
The VCS reference is at `config/vcs_config.json`.

Implement `reconcile_to_vcs()` in `reconcile.py` to fix the production config.

Verify with:
```
pytest test_config.py -v
```

**Files to fix:** `reconcile.py`
**Do NOT modify:** `service.py`, `test_config.py`, `config/vcs_config.json`
