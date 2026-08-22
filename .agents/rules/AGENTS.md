# CFA Institutional Quantitative Workspace - Agent Rules & Architecture Standards

## Core Mandates & Fiduciary Engineering Standards

1. **Polymorphic Architecture & Pythonic Interoperability (Core Principle)**:
   - **Abstract Base Classes & Protocols**: Structure all financial instruments, valuation engines, risk models, and database adapters using `abc.ABC` with `@abstractmethod` contracts or `typing.Protocol` structural subtyping.
   - **Liskov Substitution & Unified Dispatch**: Any subclass must be a seamless drop-in replacement for its abstract base (e.g. `MunicipalBond`, `FixedCouponBond`, and `MortgageBackedSecurity` all polymorphically satisfy `InvestmentInstrument.calculate_cash_flows()` and `price()`).
   - **Pythonic Idioms & Clean Encapsulation**: Utilize `@property` decorators, type hints (`typing`), immutable `@dataclass` structures, context managers (`with`), and explicit magic methods (`__repr__`, `__str__`, `__len__`, `__iter__`). Avoid anti-patterns like hidden global state, monkey-patching, or monolithic god-classes.
   - **Decoupled Pluggable Interfaces**: Maintain strict separation of concerns—data persistence (DuckDB/SQLite), analytics engines, visual rendering, and autonomous agents interact strictly through clean, typed API boundaries.

2. **Mandatory Co-Testing & Negative Testing Best Practice (Non-Negotiable)**:
   - **Test-Driven Rigor**: Every new feature, parser, engine, or pipeline written MUST be accompanied by comprehensive unit, integration, and property-based tests in `tests/`.
   - **Negative Testing & Error Catching**: Do not only test happy paths. Always design tests specifically to catch critical bugs, failed operations, network dropouts, malformed XML/JSON/CSV inputs, missing columns, corrupt timestamps, and `NaN`/`None` values.
   - **Invariants & Mathematical Boundaries**: Verify financial invariants (e.g. Put-Call Parity, Bond Price Monotonicity $\frac{\partial P}{\partial y} < 0$, Quality Scores $Q \in [0.0, 1.0]$, Sentiment $\in [-1.0, 1.0]$, Brinson sum exactness, Weight sum conservation $\sum w_i = 1.0$).
   - **Pre-Commit Verification**: Run `pytest -v tests/` and guarantee 100% test pass rates before finishing any task or committing code.

3. **Zero Data Loss Archival Standard**:
   - Never discard, truncate, or drop raw data fields from lookups, APIs, or statements.
   - Always persist the unadulterated provider response in `raw_payload_json` within DuckDB columnar tables alongside structured typed columns.

4. **Standardized CFA Level I, II, III & CIPM Rigor**:
   - Always ground formulations in official CFA and CIPM curriculum standards (IPS Ability vs. Willingness, Brinson-Fachler attribution, Campisi fixed income, Carino logarithmic linking, Black-Litterman reverse optimization, GIPS composite dispersion).
   - Leverage local semantic curriculum search (`scripts/query_cfa_kb.py`) for exact formulas.

5. **Point-in-Time & Fiduciary Data Integrity**:
   - Avoid lookahead bias; enforce Point-in-Time (PIT) transaction state and financial statement reconstruction.
   - Execute deterministic math scripts rather than approximations.

6. **Temporal Grounding (Year 2026)**:
   - Explicitly anchored to **Year 2026**. All yield curves, SOFR benchmarks, tax rates, and copilot reasoning must reflect 2026.
