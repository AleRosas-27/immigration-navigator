"""
ImmigrationNavigator — Deadline Calculator
==========================================
UC Berkeley MIDS Capstone 2026

Deterministic rules-based deadline calculator.
No LLM involved — all date arithmetic is computed from USCIS rules.

Sources:
    USCIS Policy Manual, Volume 2, Part F, Chapter 5
    https://www.uscis.gov/policy-manual/volume-2-part-f-chapter-5

Usage:
    from src.deadlines import calculate_deadlines, format_deadlines
    from datetime import date

    deadlines = calculate_deadlines(date(2025, 5, 15))
    print(format_deadlines(deadlines))
"""

from datetime import date, timedelta


def calculate_deadlines(graduation_date: date) -> dict:
    """
    Calculate all key OPT, STEM OPT, and H-1B cap-gap deadlines
    based on the student's program end date.

    All rules sourced from USCIS Policy Manual, Volume 2 Part F Chapter 5.

    Args:
        graduation_date (date): Student's program end date (I-20 end date).

    Returns:
        dict: Named deadline groups, each with dates and a plain-English note.

    Example:
        >>> deadlines = calculate_deadlines(date(2025, 5, 15))
        >>> deadlines["opt_application"]["earliest"]
        date(2025, 2, 14)
    """

    # ── OPT Application Window ──────────────────────────────────────────────
    # Must apply no earlier than 90 days before graduation
    # Must apply no later than 60 days after graduation
    opt_app_earliest = graduation_date - timedelta(days=90)
    opt_app_latest   = graduation_date + timedelta(days=60)

    # ── OPT Period ──────────────────────────────────────────────────────────
    # Post-completion OPT: 12 months starting on graduation date
    # Maximum 90 days of unemployment
    opt_end = graduation_date + timedelta(days=365)

    # ── STEM OPT Extension ──────────────────────────────────────────────────
    # Must apply at least 90 days before OPT expires
    # 24-month extension after OPT ends
    # Maximum 150 days of unemployment during STEM OPT
    stem_app_deadline = opt_end - timedelta(days=90)
    stem_opt_end      = opt_end + timedelta(days=730)

    # ── H-1B Timeline ───────────────────────────────────────────────────────
    # Lottery typically opens March 1, petitions filed ~April 1
    # H-1B employment begins October 1
    # Cap-gap: if H-1B is pending/approved, F-1 status auto-extends to Oct 1
    current_year      = graduation_date.year
    h1b_lottery_open  = date(current_year, 3, 1)
    h1b_petition_date = date(current_year, 4, 1)
    h1b_start_date    = date(current_year, 10, 1)

    return {
        "opt_application": {
            "earliest": opt_app_earliest,
            "latest":   opt_app_latest,
            "note":     "File Form I-765 within this window. "
                        "Apply early — USCIS processing times can be 3–5 months.",
        },
        "opt_period": {
            "start": graduation_date,
            "end":   opt_end,
            "note":  "12 months of post-completion OPT. "
                     "Max 90 days of unemployment — track carefully.",
        },
        "stem_opt_application": {
            "deadline": stem_app_deadline,
            "note":     "File Form I-765 + I-983 at least 90 days before OPT expires. "
                        "Employer must be E-Verify registered.",
        },
        "stem_opt_period": {
            "start": opt_end,
            "end":   stem_opt_end,
            "note":  "24-month STEM OPT extension. "
                     "Max 150 days of unemployment. "
                     "Requires annual I-983 self-evaluation.",
        },
        "h1b_timeline": {
            "lottery_opens":  h1b_lottery_open,
            "petition_filed": h1b_petition_date,
            "start_date":     h1b_start_date,
            "note":           "Cap-gap automatically extends F-1 status to Oct 1 "
                              "if H-1B petition is pending or approved. "
                              "Unemployment during cap-gap counts toward OPT limits.",
        },
    }


def format_deadlines(deadlines: dict) -> str:
    """
    Format a deadlines dict (from calculate_deadlines) as a
    human-readable markdown string for display in the UI.

    Args:
        deadlines (dict): Output of calculate_deadlines().

    Returns:
        str: Markdown-formatted timeline string.
    """
    d = deadlines
    fmt = "%B %d, %Y"

    lines = [
        "📅 **Your Immigration Timeline**",
        "",
        "**OPT Application Window**",
        f"- Earliest: {d['opt_application']['earliest'].strftime(fmt)}",
        f"- Latest:   {d['opt_application']['latest'].strftime(fmt)}",
        f"- {d['opt_application']['note']}",
        "",
        "**OPT Period**",
        f"- Start: {d['opt_period']['start'].strftime(fmt)}",
        f"- End:   {d['opt_period']['end'].strftime(fmt)}",
        f"- {d['opt_period']['note']}",
        "",
        "**STEM OPT Extension**",
        f"- Apply by: {d['stem_opt_application']['deadline'].strftime(fmt)}",
        f"- {d['stem_opt_application']['note']}",
        f"- Period: {d['stem_opt_period']['start'].strftime(fmt)} "
        f"→ {d['stem_opt_period']['end'].strftime(fmt)}",
        f"- {d['stem_opt_period']['note']}",
        "",
        "**H-1B Timeline**",
        f"- Lottery opens:  {d['h1b_timeline']['lottery_opens'].strftime(fmt)}",
        f"- Petition filed: {d['h1b_timeline']['petition_filed'].strftime(fmt)}",
        f"- H-1B starts:   {d['h1b_timeline']['start_date'].strftime(fmt)}",
        f"- {d['h1b_timeline']['note']}",
    ]
    return "\n".join(lines)


def deadlines_to_dict(deadlines: dict) -> dict:
    """
    Convert a deadlines dict to a JSON-serializable format
    (converts date objects to ISO strings).

    Use this when returning deadlines from the API.

    Args:
        deadlines (dict): Output of calculate_deadlines().

    Returns:
        dict: Same structure but with date objects as ISO strings.
    """
    def convert(obj):
        if isinstance(obj, date):
            return obj.isoformat()
        if isinstance(obj, dict):
            return {k: convert(v) for k, v in obj.items()}
        return obj

    return convert(deadlines)
