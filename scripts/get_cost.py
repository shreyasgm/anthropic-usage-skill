#!/usr/bin/env python3
"""Fetch Anthropic API cost report for a specified time period."""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


def load_api_key():
    """Load the admin API key from ~/.env file."""
    env_path = os.path.expanduser("~/.env")
    if not os.path.exists(env_path):
        print(f"Error: {env_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("ANTHROPIC_ADMIN_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")

    print("Error: ANTHROPIC_ADMIN_KEY not found in ~/.env", file=sys.stderr)
    sys.exit(1)


def fetch_cost_report(start_dt: datetime, end_dt: datetime, api_key: str) -> dict:
    """Fetch cost report from Anthropic API."""
    # API requires UTC day boundaries and at least 2 days span
    start_str = start_dt.strftime("%Y-%m-%dT00:00:00Z")
    end_str = end_dt.strftime("%Y-%m-%dT00:00:00Z")

    url = f"https://api.anthropic.com/v1/organizations/cost_report?starting_at={start_str}&ending_at={end_str}"

    req = Request(url)
    req.add_header("anthropic-version", "2023-06-01")
    req.add_header("x-api-key", api_key)

    try:
        with urlopen(req) as response:
            return json.loads(response.read().decode())
    except HTTPError as e:
        error_body = e.read().decode()
        print(f"API Error ({e.code}): {error_body}", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"Network Error: {e.reason}", file=sys.stderr)
        sys.exit(1)


MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
}


def parse_period(period: str) -> tuple[datetime, datetime, datetime, datetime]:
    """
    Parse a time period string into dates.

    Returns (api_start, api_end, filter_start, filter_end).
    - api_start/api_end: dates to send to API (padded to meet 2-day minimum)
    - filter_start/filter_end: actual requested dates for filtering results
    """
    period = period.lower().strip()
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    def make_result(start, end):
        """Return API dates (padded if needed) and filter dates."""
        filter_start, filter_end = start, end
        api_start, api_end = start, end
        # API requires minimum 2-day span
        if (api_end - api_start).days < 2:
            api_end = api_start + timedelta(days=2)
        return api_start, api_end, filter_start, filter_end

    if period in ("last week", "past week"):
        start = today - timedelta(days=6)
        end = today + timedelta(days=1)
        return make_result(start, end)

    if period in ("last month", "past month"):
        first_of_this_month = today.replace(day=1)
        end = first_of_this_month
        if first_of_this_month.month == 1:
            start = first_of_this_month.replace(year=first_of_this_month.year - 1, month=12)
        else:
            start = first_of_this_month.replace(month=first_of_this_month.month - 1)
        return make_result(start, end)

    if period == "this week":
        days_since_monday = today.weekday()
        start = today - timedelta(days=days_since_monday)
        end = today + timedelta(days=1)
        return make_result(start, end)

    if period == "this month":
        start = today.replace(day=1)
        end = today + timedelta(days=1)
        return make_result(start, end)

    if period == "yesterday":
        start = today - timedelta(days=1)
        end = today
        return make_result(start, end)

    if period == "today":
        start = today
        end = today + timedelta(days=1)
        return make_result(start, end)

    # "last N days"
    if period.startswith("last ") and "day" in period:
        parts = period.split()
        try:
            n = int(parts[1])
            start = today - timedelta(days=n - 1)
            end = today + timedelta(days=1)
            return make_result(start, end)
        except (ValueError, IndexError):
            pass

    # Date range: "YYYY-MM-DD to YYYY-MM-DD"
    if " to " in period:
        parts = period.split(" to ")
        try:
            start = datetime.strptime(parts[0].strip(), "%Y-%m-%d")
            end = datetime.strptime(parts[1].strip(), "%Y-%m-%d") + timedelta(days=1)
            return make_result(start, end)
        except ValueError:
            pass

    # Single date: "YYYY-MM-DD"
    try:
        date = datetime.strptime(period, "%Y-%m-%d")
        start = date
        end = date + timedelta(days=1)
        return make_result(start, end)
    except ValueError:
        pass

    # Month name with optional year
    for month_name, month_num in MONTHS.items():
        if period.startswith(month_name):
            parts = period.split()
            if len(parts) == 2:
                try:
                    year = int(parts[1])
                except ValueError:
                    year = today.year
            else:
                year = today.year

            start = datetime(year, month_num, 1)
            if month_num == 12:
                end = datetime(year + 1, 1, 1)
            else:
                end = datetime(year, month_num + 1, 1)
            return make_result(start, end)

    print(f"Error: Could not parse period '{period}'", file=sys.stderr)
    print("Supported formats: 'last week', 'last month', 'this month', 'yesterday',", file=sys.stderr)
    print("  'today', 'last N days', 'YYYY-MM-DD', 'YYYY-MM-DD to YYYY-MM-DD',", file=sys.stderr)
    print("  'january', 'january 2025', etc.", file=sys.stderr)
    sys.exit(1)


def filter_buckets(data: dict, filter_start: datetime, filter_end: datetime) -> list:
    """Filter buckets to only include those within the requested range."""
    buckets = data.get("data", [])
    filtered = []
    for bucket in buckets:
        bucket_start = datetime.strptime(bucket["starting_at"][:10], "%Y-%m-%d")
        if bucket_start >= filter_start and bucket_start < filter_end:
            filtered.append(bucket)
    return filtered


def format_output(buckets: list, output_format: str, raw_data: dict = None):
    """Format and print the cost report."""
    if output_format == "json":
        print(json.dumps(raw_data if raw_data else {"data": buckets}, indent=2))
        return

    if not buckets:
        print("No cost data found for the specified period.")
        return

    total_cents = 0.0

    print(f"{'Date':<12} {'Cost':>12}")
    print("-" * 25)

    for bucket in buckets:
        date = bucket["starting_at"][:10]
        amount_cents = sum(float(r["amount"]) for r in bucket.get("results", []))
        amount_dollars = amount_cents / 100
        total_cents += amount_cents
        print(f"{date:<12} ${amount_dollars:>10.2f}")

    print("-" * 25)
    print(f"{'Total':<12} ${total_cents / 100:>10.2f}")


def main():
    parser = argparse.ArgumentParser(description="Fetch Anthropic API cost report")
    parser.add_argument("period", help="Time period (e.g., 'last week', 'january 2025', '2025-01-15')")
    parser.add_argument("--format", choices=["table", "json"], default="table",
                        help="Output format (default: table)")

    args = parser.parse_args()

    api_key = load_api_key()
    api_start, api_end, filter_start, filter_end = parse_period(args.period)

    data = fetch_cost_report(api_start, api_end, api_key)
    filtered_buckets = filter_buckets(data, filter_start, filter_end)

    format_output(filtered_buckets, args.format, data if args.format == "json" else None)


if __name__ == "__main__":
    main()
