# Architecture

CashTrace is split into independent work areas so teammates can develop the UI, API, and financial analysis without blocking one another.

## Boundaries

- **`frontend/`**: User interface and client-side interactions. Built with Next.js App Router. It should not contain financial calculation logic.
- **`backend/`**: HTTP API, request validation, and coordination. Built with FastAPI. It should not become the home of core financial algorithms.
- **`financial_engine/`**: Deterministic financial processing and analysis. This is the intended place for Pandas/NumPy-based calculations once the team is ready to implement them.
- **`docs/`**: Shared architecture notes and team conventions.

## Integration

Financial calculations should remain independent of the API layer. The backend may later import or call the financial engine, but that coupling should be explicit and thin.

Do not treat this document as a finalized API specification. Request and response contracts, file formats, and analysis outputs should be agreed upon by the team before implementation.
