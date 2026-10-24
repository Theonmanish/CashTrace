# Financial Engine

This package is reserved for CashTrace's deterministic financial processing.

It will eventually contain logic for:

- Reconstructing historical cash balances
- Detecting financial dead zones
- Identifying root causes
- Forecasting liquidity risk
- Supporting what-if simulations

This module should stay independent of HTTP handling, request parsing, and API routing. The backend may call into it later, but calculation code should not live in FastAPI route handlers.

No analysis algorithms or data contracts are implemented yet. Agree on integration boundaries with the team before adding code here.
