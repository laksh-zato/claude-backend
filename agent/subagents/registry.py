from .loader import build_subagent_spec, SubagentSpec


SUBAGENTS: list[SubagentSpec] = [
    build_subagent_spec(
        name="gl_reconciler",
        skill_dir="gl-reconciler",
        web=False,
        description="Reconciles a general ledger against source documents (bank statements, sub-ledgers, supporting schedules) and explains discrepancies.",
    ),
    build_subagent_spec(
        name="statement_auditor",
        skill_dir="statement-auditor",
        web=False,
        description="Audits financial statements (P&L, balance sheet, cash flow) for completeness, internal consistency, and red flags.",
    ),
    build_subagent_spec(
        name="month_end_closer",
        skill_dir="month-end-closer",
        web=False,
        description="Walks through the month-end close checklist using uploaded trial balances and supporting schedules.",
    ),
    build_subagent_spec(
        name="earnings_reviewer",
        skill_dir="earnings-reviewer",
        web=True,
        description="Reviews quarterly earnings releases and 10-Q/10-K filings; can search the web for filings, transcripts, and analyst notes.",
    ),
    build_subagent_spec(
        name="model_builder",
        skill_dir="model-builder",
        web=True,
        description="Builds and reviews 3-statement / DCF financial models; can search the web for comparables and current rates.",
    ),
    build_subagent_spec(
        name="valuation_reviewer",
        skill_dir="valuation-reviewer",
        web=True,
        description="Reviews valuation work (DCF, comparables, precedent transactions); can search the web for trading multiples and recent transactions.",
    ),
]


WEB_ENABLED_NAMES: set[str] = {s["name"] for s in SUBAGENTS if s["web"]}
