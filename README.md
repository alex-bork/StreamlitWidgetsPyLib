# streamlit_plus

> ⚠️ **Built with vibe coding**
>
> This project was created via vibe coding. I've tested it as thoroughly as I could, but I make **no guarantees** and take **no responsibility** for any issues, bugs, or damages that may arise from using it. **Use it at your own risk.**

## Description

A small collection of custom widgets and components for [Streamlit](https://streamlit.io/), packaged as `streamlit_plus`. It adds richer, interactive UI building blocks on top of the standard Streamlit toolkit, some built with plain Streamlit containers and styling, others as Custom Components (v2) with their own HTML/CSS/JS.

## What's inside

The library exposes two groups of building blocks.

### Widgets

Higher-level constructs assembled from native Streamlit containers and theming:

- **`Card`** — a bordered card with an optional image, title, subtitle, status line, and arbitrary content.
- **`FormWizard`** / **`Step`** — a multi-step form wizard with a step indicator, per-step forms, back/next navigation, and finish handling. State persists across reruns via `st.session_state`.
- **`Box`** — a rounded, themed container that wraps arbitrary Streamlit content.

### Custom components

Interactive components rendered through Streamlit's Custom Components v2 (HTML/CSS/JS):

- **`table`** — a data table with row/cell selection, per-column filtering, sorting, draggable columns, pagination, and a configurable toolbar (built-in and custom actions).
- **`tree`** — a clickable, collapsible tree menu with icons and selection.
- **`calendar`** — a calendar supporting single and range date selection.
- **`persona`** — a person card with avatar, role, status, and an optional popover.
- **`breadcrumbs`** — a breadcrumb navigation trail with optional links.
- **`tile`** — a clickable tile with a title, icon, and content.
- **`clickable`** — a container that turns arbitrary content into a clickable region.
- **`icon`** — a Material icon component with label, size, status, and click handling.

## Requirements

- Python >= 3.14
- Streamlit >= 1.63.0

## Installation

Install from the project root (editable install for development):

```bash
pip install -e .
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv pip install -e .
```

## Usage

```python
import streamlit as st
from streamlit_plus import Card, Box, FormWizard, Step, table, tree, calendar, persona, breadcrumbs

Card(
    title="Jane Doe",
    subtitle="Senior Developer",
    status="Online",
    status_color="active",
    image_url="https://example.com/avatar.jpg",
    content=lambda: st.write("This is the card content."),
)
```

A full demo covering every widget and component lives in [`test/app.py`](test/app.py). Run it with:

```bash
streamlit run test/app.py
```

## License

See [LICENSE](LICENSE).
