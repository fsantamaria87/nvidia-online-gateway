# Capacity Engineering Benchmark V1

Deterministic synthetic benchmark for the NVIDIA Online Gateway.

## Acceptance gates
- 20/20 cases must preserve arithmetic, units, and requested denominators.
- Missing-data cases must not invent values.
- AUTO routing target: simple arithmetic/extraction -> fast; multi-factor analysis -> balanced; audit/debug/high-consequence verification -> deep.
- A model-generated evalset is advisory only and is never ground truth until deterministic checks pass.
- Partial/truncated evalsets are rejected when the parsed top-level `cases` array is absent or its length differs from `requested_count`.
- Reviews are advisory and cannot grant release approval.

## Data policy
All benchmark data is SYNTHETIC. Real company-sensitive data must not be sent to an external provider unless explicitly approved under the gateway classification contract.
