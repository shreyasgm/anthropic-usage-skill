# Anthropic Usage Skill

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that fetches Anthropic API cost reports for any time period.

## Installation

Copy the skill to your Claude Code skills directory:

```bash
cp -r anthropic-usage ~/.claude/skills/
```

Or install the packaged skill:

```bash
# Download anthropic-usage.skill and place in ~/.claude/skills/
```

## Prerequisites

Set your Anthropic Admin API key in `~/.env`:

```bash
ANTHROPIC_ADMIN_KEY=sk-ant-admin-...
```

You can get an Admin API key from [console.anthropic.com](https://console.anthropic.com) (requires admin role).

## Usage

Once installed, Claude Code will automatically use this skill when you ask about API costs:

- "What's my API cost for last week?"
- "How much did I spend in January?"
- "Show me yesterday's usage"

### Supported Period Formats

| Format | Example | Description |
|--------|---------|-------------|
| Relative week | `last week`, `this week` | 7-day periods |
| Relative month | `last month`, `this month` | Calendar months |
| Relative day | `yesterday`, `today` | Single days |
| Last N days | `last 3 days`, `last 30 days` | Rolling window |
| Specific date | `2026-02-01` | Single UTC day |
| Date range | `2026-01-01 to 2026-01-31` | Inclusive range |
| Month name | `january`, `feb 2025` | Full calendar month |

### Direct Script Usage

You can also run the script directly:

```bash
~/.claude/skills/anthropic-usage/scripts/get_cost.py "last week"
```

Output:
```
Date                 Cost
-------------------------
2026-01-29   $      4.67
2026-01-30   $      2.80
2026-01-31   $      4.00
2026-02-01   $     48.72
-------------------------
Total        $     60.19
```

### Options

- `--format table` (default): Human-readable table with totals
- `--format json`: Raw API response

## Notes

- Costs are returned in USD
- Data is reported in UTC day buckets
- The Anthropic API returns amounts in cents; the script converts to dollars

## License

MIT
