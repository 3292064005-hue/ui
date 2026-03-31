# DEPLOYMENT

Canonical deployment entrypoint for the converged runtime.

Profiles:
- `dev`: local iteration, relaxed seal requirements, debug-level logging
- `research`: writable runtime with strong evidence and provenance capture
- `clinical`: strict control authority, token-gated writes, strict evidence seal
- `review`: read-only replay/review/export profile

Primary smoke check:
```bash
python scripts/deployment_smoke_test.py
```

Runtime boundaries:
- C++ / robot core owns real motion authority and final runtime verdicts
- Python headless exposes contracts, evidence access, and profile guards
- Desktop/Web consume the control-plane snapshot and do not invent parallel truth


Preflight:

```bash
python scripts/doctor_runtime.py
```

Real runtime launch now runs the doctor first and will also honor `XCORE_SDK_ROOT` / `ROKAE_SDK_ROOT` when building the C++ core.
