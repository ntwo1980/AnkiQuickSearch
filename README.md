# Anki Quick Search

I don't want to show **suspended** cards by default and I often want to search for **new** or **due** cards within a deck. While it's possible to use search queries for them, switching to another deck resets the query, requiring me to re-enter it.
To streamline this, I created this add-on—it automatically appends search filters as needed.

![Screenshot](https://raw.githubusercontent.com/ntwo1980/AnkiQuickSearch/refs/heads/main/screenshot.png)

This simple Anki add-on adds a quick filter bar on the second row of the Browser, directly below the search bar.
By default, **suspended cards are hidden**.

## Filter options

Current order from left to right: **Due**, **New**, **Studied**, **Added**, **Introduced**, **Again**, **Flag**, **Marked**, **Suspended**.

- **Due** – Single-select filter with `in 0 days`, `in 1 days`, `in 3 days`, `in 7 days`, `in 14 days`, and `in 30 days`.
- **New** – Checkbox to show only new cards.
- **Studied** – Single-select filter with `in 1 days`, `in 3 days`, `in 7 days`, `in 14 days`, and `in 30 days`.
- **Added** – Single-select filter with `in 1 days`, `in 3 days`, `in 7 days`, `in 14 days`, and `in 30 days`.
- **Introduced** – Single-select filter with `in 1 days`, `in 3 days`, `in 7 days`, `in 14 days`, and `in 30 days`.
- **Again** – Single-select filter with `in 1 days`, `in 3 days`, `in 7 days`, `in 14 days`, and `in 30 days`.
- **Flag** – Multi-select filter with `Any flag` or one or more values from `flag 1` to `flag 7`.
- **Marked** – Checkbox to include only cards with `tag:marked`.
- **Suspended** – When checked, suspended cards are included. When unchecked, suspended cards are excluded.
