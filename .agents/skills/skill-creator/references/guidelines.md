# Skill Creation & Progressive Disclosure Guidelines

## Core Principles
1. **Progressive Disclosure**: Keep `SKILL.md` clean and concise (<100 lines). Offload large manuals and mathematical proofs to `references/`.
2. **Actionable Helper Scripts**: Put deterministic math, API calls, and ETL logic in `scripts/`.
3. **Few-Shot Examples**: Store reference JSON/YAML payloads in `examples/` to ground model outputs in structured formats.
4. **Validation**: Test all python scripts for syntax and execute dry-runs before deployment.
