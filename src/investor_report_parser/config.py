from __future__ import annotations

from .models import StatementSpec


STATEMENT_SPECS: tuple[StatementSpec, ...] = (
    StatementSpec(
        name="Profit or Loss",
        sheet_name="P&L",
        heading_aliases=(
            "Condensed consolidated statement of profit or loss and other comprehensive income",
            "statement of profit or loss",
            "income statement",
        ),
    ),
    StatementSpec(
        name="Financial Position",
        sheet_name="Balance Sheet",
        heading_aliases=(
            "Condensed consolidated statement of financial position",
            "balance sheet",
            "statement of financial position",
        ),
    ),
    StatementSpec(
        name="Cash Flows",
        sheet_name="Cash Flow",
        heading_aliases=(
            "Condensed consolidated statement of cash flows",
            "statement of cash flows",
        ),
    ),
)
