import inspect
import json
import re
from datetime import date
from typing import Any, Callable, Dict, List, Literal, Optional, Union, cast

import streamlit as st

Width = Union[int, Literal["stretch", "content"]]
Height = Union[int, Literal["stretch", "content"]]


def _default_key(prefix: str, depth: int = 2) -> str:
    """Build a fallback key from the caller's source location.

    Components that need a stable, non-``None`` key (e.g. to target a
    container via a ``st-key-*`` CSS class, or to namespace internal session
    state) can't simply fall back to a fixed literal: every unkeyed call
    would then produce the exact same key and collide. Deriving the default
    from the immediate caller's file + line number keeps calls at different
    call sites distinct while staying stable across reruns. Multiple calls
    from the *same* line (e.g. inside a loop) still require an explicit
    ``key``, matching normal Streamlit widget-key conventions.

    ``depth`` is the number of stack frames between this function and the
    user's call site; increase it when calling through an extra helper.
    """

    caller = inspect.stack()[depth]
    return f"_stplus_{prefix}_{abs(hash((caller.filename, caller.lineno)))}"


def _wire_icon_click(
    prefix: str, key: Optional[str], on_click: Optional[Callable[[], None]]
):
    """Resolve the widget key and click callback for a clickable icon badge.

    Returns ``(key, None)`` unchanged when ``on_click`` isn't provided, since
    the component then has no trigger to track. Otherwise, a stable event key
    is derived (falling back to the caller's source location) and a
    dedupe-and-forward callback is returned for ``on_clicked_change``.
    """
    if on_click is None:
        return key, None
    resolved_key = key or _default_key(prefix, depth=3)
    last_click_state_key = f"{resolved_key}_last_click"
    event_key = f"{resolved_key}_event"

    def _on_clicked():
        component_state = st.session_state.get(event_key, {})
        click_value = component_state.get("clicked")
        if click_value is not None and click_value != st.session_state.get(
            last_click_state_key
        ):
            st.session_state[last_click_state_key] = click_value
            on_click()

    return event_key, _on_clicked


# Keep this Literal synchronized with every standard toolbar control. Any new
# standard function must be added here so it can be passed to
# ``standard_toolbar_exclude``.
StandardToolbarAction = Literal["select_columns", "export_csv", "clear_filters"]


# ---------------------------------------------------------------------------
# Menu tree custom component (Custom Components v2)
# ---------------------------------------------------------------------------
#
# A clickable, collapsible tree. Clicking a node sends its id back to Python
# as a trigger value (read via ``result.selected``).
#
# Data contract (passed as a JSON string via the ``data`` mount parameter):
#   {
#     "tree": [ {"id": str, "label": str, "icon": str|null,
#                "children": [ ...same shape... ]}, ... ]
#   }

_MENU_TREE_CSS = """
.tg-tree {
    font-family: var(--st-font);
    color: var(--st-text-color);
}
.tg-tree.with-background {
    border: 1px solid var(--st-border-color);
    border-radius: var(--st-base-radius, 0.5rem);
    padding: 0.5rem;
    background: var(--st-secondary-background-color);
}
.tg-node {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.2rem 0.4rem;
    border-radius: 0.375rem;
    cursor: pointer;
    font-size: 0.875rem;
    user-select: none;
}
.tg-node:hover { background: var(--st-background-color); }
.tg-node.selected {
    background: transparent;
    color: var(--st-primary-color);
}
.tg-node.selected:hover { background: transparent; }
.tg-caret {
    font-family: 'Material Symbols Rounded';
    font-size: 1.125rem;
    width: 1.125rem;
    opacity: 0.7;
}
.tg-icon {
    font-family: 'Material Symbols Rounded';
    font-size: 1.125rem;
    width: 1.125rem;
}
.tg-emoji {
    font-size: 1rem;
    width: 1.125rem;
    text-align: center;
}
.tg-children { margin-left: 1rem; }
.tg-children.collapsed { display: none; }
"""

_MENU_TREE_JS = r"""
export default function(component) {
    const { data, parentElement, setTriggerValue } = component;

    // Remove anything this component appended on a previous mount so a
    // re-render (e.g. after a hot reload) does not stack duplicate trees.
    parentElement
        .querySelectorAll(".tg-tree, link.tg-font")
        .forEach((el) => el.remove());

    const model = JSON.parse(data || "{}");
    const tree = model.tree || [];
    const expanded = model.expanded !== false;  // default: expanded
    const backgroundOn = model.backgroundOn === true;  // default: off
    const selectedId = model.selectedNode || null;

    // Build the set of ancestor ids on the path to the selected node so we
    // can expand only that hierarchy when ``expanded`` is false.
    const ancestors = new Set();
    (function findPath(nodes, trail) {
        for (const n of nodes) {
            if (n.id === selectedId) {
                trail.forEach((id) => ancestors.add(id));
                return true;
            }
            if (n.children && n.children.length) {
                if (findPath(n.children, trail.concat(n.id))) return true;
            }
        }
        return false;
    })(tree, []);

    const treeEl = document.createElement("div");
    treeEl.className = "tg-tree" + (backgroundOn ? " with-background" : "");

    function renderNodes(nodes, container) {
        nodes.forEach((node) => {
            const row = document.createElement("div");
            row.className = "tg-node";
            row.dataset.id = node.id;
            if (node.id === selectedId) row.classList.add("selected");

            const hasChildren = node.children && node.children.length;
            // Expand this branch when everything is expanded, or when it lies
            // on the path to the selected node.
            const branchOpen = expanded || ancestors.has(node.id);
            const caret = document.createElement("span");
            caret.className = "tg-caret";
            caret.textContent = hasChildren
                ? (branchOpen ? "expand_more" : "chevron_right")
                : "";
            row.appendChild(caret);

            if (node.icon) {
                const icon = document.createElement("span");
                // Support Streamlit's icon convention: ":material/name:" for
                // a Material Symbol, or any other string (e.g. an emoji).
                const match = /^:material\/([a-z0-9_]+):$/.exec(node.icon);
                if (match) {
                    icon.className = "tg-icon";
                    icon.textContent = match[1];
                } else {
                    icon.className = "tg-emoji";
                    icon.textContent = node.icon;
                }
                row.appendChild(icon);
            }

            const label = document.createElement("span");
            label.textContent = node.label;
            row.appendChild(label);

            container.appendChild(row);

            let childContainer = null;
            if (hasChildren) {
                childContainer = document.createElement("div");
                childContainer.className =
                    "tg-children" + (branchOpen ? "" : " collapsed");
                container.appendChild(childContainer);
                renderNodes(node.children, childContainer);
            }

            row.onclick = (e) => {
                e.stopPropagation();
                // Toggle expand/collapse for branch nodes.
                if (childContainer) {
                    childContainer.classList.toggle("collapsed");
                    caret.textContent = childContainer.classList.contains(
                        "collapsed"
                    ) ? "chevron_right" : "expand_more";
                }
                // Update selection highlight.
                treeEl.querySelectorAll(".tg-node.selected").forEach((el) =>
                    el.classList.remove("selected")
                );
                row.classList.add("selected");
                setTriggerValue("selected", node.id);
            };
        });
    }
    renderNodes(tree, treeEl);

    // Material Symbols font for the icons/carets.
    const fontLink = document.createElement("link");
    fontLink.className = "tg-font";
    fontLink.rel = "stylesheet";
    fontLink.href =
        "https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded";
    parentElement.appendChild(fontLink);

    parentElement.appendChild(treeEl);

    // Clean up our own elements when the component unmounts.
    return () => {
        treeEl.remove();
        fontLink.remove();
    };
}
"""

_menu_tree_component = st.components.v2.component(
    name="menu_tree",
    css=_MENU_TREE_CSS,
    js=_MENU_TREE_JS,
)


def menu_tree(
    tree: List[Dict[str, Any]],
    *,
    on_select: Optional[Callable[[str], None]] = None,
    key: Optional[str] = None,
    width: Width = "stretch",
    expanded: bool = False,
    background_on: bool = False,
    selected_node: Optional[str] = None,
) -> Optional[str]:
    """Render a clickable, collapsible tree menu.

    Args:
        tree: Nested node dicts, each ``{"id", "label", "icon"?, "children"?}``.
            ``icon`` follows Streamlit's convention: either an emoji (e.g.
            ``"📁"``) or a Material symbol as ``":material/icon_name:"``.
        on_select: Optional callback invoked with the clicked node's id.
        key: Optional Streamlit widget key.
        width: Width of the tree. ``"stretch"`` (default), ``"content"``, or a
            fixed pixel width.
        expanded: When ``True``, branches start expanded; when ``False``
            (default), they start collapsed.
        background_on: When ``True``, the tree is drawn with a background color
            and border. When ``False`` (default), neither is shown.
        selected_node: Optional node id selected by default. When ``expanded``
            is ``False``, only the hierarchy leading to this node is expanded.

    Returns:
        The id of the currently selected node, or ``None``.
    """
    data = json.dumps(
        {
            "tree": tree,
            "expanded": expanded,
            "backgroundOn": background_on,
            "selectedNode": selected_node,
        }
    )
    with st.container(width=width):
        result = _menu_tree_component(
            data=data,
            on_selected_change=lambda: None,
            key=key,
        )
    selected = result.selected if result.selected is not None else selected_node
    if on_select is not None and selected is not None:
        on_select(selected)
    return selected


# ---------------------------------------------------------------------------
# Smart table custom component (Custom Components v2)
# ---------------------------------------------------------------------------
#
# A table with configurable row selection: "single", "multiple" or "none".
# Selected row ids are sent back to Python as a JSON-encoded trigger value
# (read via ``result.selection``).
#
# Data contract (passed as a JSON string via the ``data`` mount parameter):
#   {
#     "columns": [str, ...],                 # column labels
#     "rows": [ [<value>, ...], ... ],        # one list of cells per row
#     # a row's id is its index (as a string)
#     "selectionMode": "single" | "multiple" | "none",
#     "selected": [str, ...]
#   }

_SMART_TABLE_CSS = """
.stbl {
    font-family: var(--st-font);
    color: var(--st-text-color);
    overflow-x: auto;
}
.stbl table {
    border-collapse: separate;
    border-spacing: 0;
    width: 100%;
    font-size: 0.875rem;
    /* Rounded outer corners, matching the theme radius used by inputs. */
    border: 1px solid var(--st-border-color);
    border-radius: var(--st-base-radius, 0.5rem);
    overflow: hidden;
}
/* "auto": fixed layout with equal columns and ellipsis truncation. */
.stbl table.cw-auto { table-layout: fixed; }
.stbl table.cw-auto th, .stbl table.cw-auto td {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
/* "content": columns size to their content, no truncation. */
.stbl table.cw-content { table-layout: auto; }
.stbl table.cw-content th, .stbl table.cw-content td {
    white-space: nowrap;
}
.stbl th, .stbl td {
    /* The table supplies the outer top + left edge, so cells only draw the
       right + bottom gridlines. Transparent top + left borders reserve the
       space so selection highlights don't shift the layout. */
    border-top: 1px solid transparent;
    border-left: 1px solid transparent;
    border-right: 1px solid var(--st-border-color);
    border-bottom: 1px solid var(--st-border-color);
    padding: 0.4rem 0.6rem;
    text-align: left;
}
.stbl th:last-child, .stbl td:last-child { border-right: none; }
/* Only the last *visible* row drops its bottom border. This is driven
   entirely from JS (no :last-child CSS) so it stays correct after sorting
   reorders the DOM. */
.stbl tbody tr.no-bottom-border td { border-bottom: none; }
.stbl th {
    background: var(--st-secondary-background-color);
    font-weight: 600;
    position: relative;
}
.stbl th:has(.th-head) { padding-right: 0.35rem; }
.stbl .th-head {
    display: flex;
    align-items: center;
    gap: 0.35rem;
}
.stbl .th-head > span:first-child {
    flex: 1 1 auto;
    overflow: hidden;
    text-overflow: ellipsis;
}
.stbl .sort-btns {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    gap: 0.125rem;
}
.stbl .sort-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0.4;
}
.stbl .sort-btn svg { display: block; }
.stbl .sort-btns:hover .sort-btn { opacity: 0.7; }
.stbl .sort-btn.active {
    opacity: 1;
    color: var(--st-primary-color);
}
.stbl .filter-icon {
    font-family: 'Material Symbols Rounded';
    font-size: 1.125rem;
    line-height: 1;
    width: 1.125rem;
    height: 1.125rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    opacity: 0.5;
}
.stbl .filter-icon:hover { opacity: 0.85; }
.stbl .filter-icon.active {
    opacity: 1;
    color: var(--st-primary-color);
}
.stbl .filter-pop {
    position: fixed;
    z-index: 1000;
    box-sizing: border-box;
    padding: 0.5rem;
    min-width: 12rem;
    background: var(--st-background-color);
    border: 1px solid var(--st-border-color);
    border-radius: var(--st-base-radius, 0.5rem);
    box-shadow: 0 0.125rem 0.5rem rgba(0, 0, 0, 0.15);
}
.stbl .filter-pop .stbl-filter { margin-bottom: 0.4rem; }
.stbl .filter-clear {
    margin-top: 0.5rem;
    width: 100%;
    padding: 0.3rem 0.5rem;
    font: inherit;
    font-weight: 400;
    color: var(--st-primary-content-color, white);
    background: var(--st-primary-color);
    border: 1px solid var(--st-primary-color);
    border-radius: var(--st-base-radius, 0.5rem);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.375rem;
}
.stbl .filter-clear .material-symbols-rounded {
    font-family: 'Material Symbols Rounded';
    font-size: 1.125rem;
}
.stbl .filter-clear:hover {
    background: color-mix(in srgb, var(--st-primary-color) 85%, black);
    border-color: color-mix(in srgb, var(--st-primary-color) 85%, black);
    color: var(--st-primary-content-color, white);
}
.stbl .filter-exclude {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    font-weight: 400;
    font-size: 0.8125rem;
    cursor: pointer;
}
.stbl th.select-col, .stbl td.select-col {
    width: 2.5rem;
    text-align: center;
}
.stbl tbody tr {
    height: 2.35rem;
    cursor: pointer;
}
.stbl tbody td {
    height: 2.35rem;
    box-sizing: border-box;
}
.stbl tbody tr.banded {
    background: color-mix(in srgb,
        var(--st-secondary-background-color) 55%, transparent);
}
.stbl tbody tr:hover { background: var(--st-secondary-background-color); }
.stbl tbody tr.filler-row { cursor: default; }
.stbl tbody tr.filler-row:hover { background: none; }
.stbl tbody tr.selected {
    background: var(--st-primary-color);
    color: var(--st-background-color);
}
.stbl tbody tr.selected:hover {
    background: var(--st-primary-color);
}
.stbl tbody tr.selected td {
    background: var(--st-primary-color);
    color: var(--st-background-color);
    border-color: white;
}
/* On a selected (primary) row, flip the checkbox/radio accent to the row's
   text color so it stays visible instead of blending primary-on-primary.
   The select cell keeps the row/band background (no override). */
.stbl tbody tr.selected input[type="checkbox"],
.stbl tbody tr.selected input[type="radio"] {
    accent-color: var(--st-background-color);
}
.stbl td.cell-selectable { cursor: pointer; }
.stbl td.cell-selectable.selected {
    background: var(--st-primary-color);
    color: var(--st-background-color);
    border-color: white;
}
.stbl th.visible-column-last, .stbl td.visible-column-last {
    border-right: none;
}
.stbl tbody tr.selected td.visible-column-last,
.stbl td.cell-selectable.selected.visible-column-last {
    border-right: 1px solid white;
}
.stbl input[type="checkbox"], .stbl input[type="radio"] {
    cursor: pointer;
    accent-color: var(--st-primary-color);
}
.stbl-toolbar {
    display: flex;
        position: relative;
    justify-content: flex-end;
    gap: 0;
    margin-bottom: 0.15rem;
}
.stbl-toolbar .toolbar-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.25rem 0.3rem;
    color: var(--st-text-color);
    background: transparent;
    border: 1px solid transparent;
    border-radius: var(--st-base-radius, 0.5rem);
    cursor: pointer;
    opacity: 0.7;
}
.stbl-toolbar .toolbar-btn:hover:not(:disabled) {
    color: var(--st-primary-color);
    opacity: 1;
}
.stbl-toolbar .toolbar-btn.active {
    color: var(--st-primary-color);
    opacity: 1;
}
.stbl-toolbar .toolbar-btn:disabled {
    cursor: default;
    opacity: 0.35;
}
.stbl-toolbar .dynamic-toolbar-btn {
    /* Dynamic controls stay at the outer edge of the button group. */
    order: -1;
}
.stbl-toolbar .toolbar-btn .material-symbols-rounded {
    font-family: 'Material Symbols Rounded';
    font-size: 1.125rem;
    font-weight: 300;
    font-variation-settings: 'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 24;
}
.stbl-pager {
    display: flex;
    position: relative;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.05rem;
    justify-content: center;
    margin-top: 0.5rem;
}
.stbl-pager .pager-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 1.4rem;
    height: 1.4rem;
    padding: 0 0.3rem;
    font-size: 0.8125rem;
    line-height: 1;
    color: var(--st-text-color);
    background: transparent;
    border: 1px solid transparent;
    border-radius: var(--st-base-radius, 0.5rem);
    cursor: pointer;
    opacity: 0.7;
}
.stbl-pager .pager-btn:hover:not(:disabled) {
    color: var(--st-primary-color);
    opacity: 1;
}
.stbl-pager .pager-btn.active {
    color: var(--st-primary-color);
    opacity: 1;
}
.stbl-pager .page-gap {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 1.4rem;
    height: 1.4rem;
    color: var(--st-text-color);
    opacity: 0.7;
}
.stbl-column-pop {
    position: absolute;
    top: calc(100% + 0.25rem);
    right: 0;
    z-index: 1000;
    min-width: 12rem;
    max-height: 18rem;
    overflow-y: auto;
    box-sizing: border-box;
    padding: 0.375rem;
    font: inherit;
    color: var(--st-text-color);
    background: var(--st-background-color);
    border: 1px solid var(--st-border-color);
    border-radius: var(--st-base-radius, 0.5rem);
    box-shadow: 0 0.125rem 0.5rem rgba(0, 0, 0, 0.15);
}
.stbl-column-option {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    min-height: 2rem;
    padding: 0.25rem 0.5rem;
    font-weight: 400;
    line-height: 1.25;
    border-radius: calc(var(--st-base-radius, 0.5rem) - 0.125rem);
    cursor: pointer;
    white-space: nowrap;
}
.stbl-column-option:hover {
    background: var(--st-secondary-background-color);
}
.stbl-column-option input {
    width: 1rem;
    height: 1rem;
    margin: 0;
    accent-color: var(--st-primary-color);
}
.stbl-pager .pager-btn:disabled { opacity: 0.3; cursor: default; }
.stbl-pager .pager-btn svg { display: block; }
.stbl-pager .page-select {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    box-sizing: border-box;
    min-width: 4.25rem;
    height: 1.75rem;
    padding: 0.15rem 0.45rem;
    font: inherit;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--st-text-color);
    text-align: center;
    background: var(--st-background-color);
    border: 1px solid var(--st-border-color);
    border-radius: var(--st-button-radius, var(--st-base-radius, 0.5rem));
    outline: none;
    cursor: pointer;
    transition: border-color 120ms ease;
}
.stbl-pager .page-select:hover {
    border-color: var(--st-border-color);
}
.stbl-pager .page-select:focus-visible {
    border-color: var(--st-primary-color);
}
.stbl-pager .page-select[aria-expanded="true"] {
    border-color: var(--st-primary-color);
}
.stbl-pager .page-menu {
    position: fixed;
    top: auto;
    left: 0;
    z-index: 1000;
    min-width: 4.25rem;
    transform: translateX(-50%);
}
.stbl-pager .page-menu-list {
    max-height: 5.75rem;
    overflow-y: auto;
    scrollbar-width: none;
    padding: 0.25rem;
    background: var(--st-background-color);
    border: 1px solid var(--st-border-color);
    border-radius: var(--st-base-radius, 0.5rem);
}
.stbl-pager .page-menu-list::-webkit-scrollbar {
    display: none;
}
.stbl-pager .page-menu-arrow {
    position: absolute;
    right: 0.35rem;
    bottom: 0.2rem;
    color: var(--st-text-color);
    font-family: 'Material Symbols Rounded';
    font-size: 1rem;
    line-height: 1;
    pointer-events: none;
}
.stbl-pager .page-menu-arrow-up {
    position: absolute;
    top: 0.2rem;
    right: 0.35rem;
    color: var(--st-text-color);
    font-family: 'Material Symbols Rounded';
    font-size: 1rem;
    line-height: 1;
    pointer-events: none;
}
.stbl-pager .page-menu.last-page .page-menu-arrow {
    display: none !important;
}
.stbl-pager .page-option {
    display: block;
    width: 100%;
    padding: 0.35rem 0.5rem;
    font: inherit;
    font-size: 0.75rem;
    color: var(--st-text-color);
    text-align: center;
    background: transparent;
    border: 0;
    border-radius: calc(var(--st-base-radius, 0.5rem) - 0.125rem);
    cursor: pointer;
}
.stbl-pager .page-option:hover {
    color: var(--st-text-color);
    background: var(--st-secondary-background-color);
}
.stbl-pager .page-option.active {
    color: var(--st-primary-color);
    background: transparent;
}
.stbl-tooltip {
    position: fixed;
    z-index: 1000;
    max-width: 24rem;
    padding: 0.4rem 0.6rem;
    font-family: var(--st-font);
    font-size: 0.8125rem;
    line-height: 1.4;
    color: var(--st-text-color);
    background: var(--st-background-color);
    border: 1px solid var(--st-border-color);
    border-radius: var(--st-base-radius, 0.5rem);
    box-shadow: 0 0.125rem 0.5rem rgba(0, 0, 0, 0.15);
    white-space: normal;
    pointer-events: none;
}
.stbl-filter {
    width: 100%;
    box-sizing: border-box;
    margin-bottom: 0.5rem;
    padding: 0.35rem 0.5rem;
    font: inherit;
    font-weight: 400;
    color: var(--st-text-color);
    background: var(--st-secondary-background-color);
    border: 1px solid transparent;
    border-radius: var(--st-base-radius, 0.5rem);
    outline: none;
}
.stbl-filter:focus {
    border-color: var(--st-primary-color);
}
"""

_SMART_TABLE_JS = r"""
export default function(component) {
    const { data, parentElement, setTriggerValue } = component;

    // Remove anything this component appended on a previous mount so a
    // re-render (e.g. after a hot reload) does not stack duplicate tables.
    parentElement
        .querySelectorAll(".stbl, .stbl-tooltip")
        .forEach((el) => el.remove());

    const model = JSON.parse(data || "{}");
    const columns = model.columns || [];
    const rows = model.rows || [];
    const mode = model.selectionMode || "none";
    const selectable = mode === "single" || mode === "multiple";
    const cellMode = mode === "cell";
    // A stable element that survives frontend-only re-mounts (e.g. a
    // light/dark theme switch, which does not rerun Python). With style
    // isolation, parentElement is a ShadowRoot, so use its host element for
    // dataset storage.
    const stateEl = parentElement.host || parentElement;
    // Only restore a saved selection when it belongs to the current mode;
    // switching modes (e.g. multiple -> cell) should not carry it over.
    const savedMode = stateEl.dataset ? stateEl.dataset.stblMode : undefined;
    const modeMatches = savedMode === mode;
    // Restore the selection saved on that element from a previous render so
    // the selection stays visible across re-mounts.
    const savedSel =
        modeMatches && stateEl.dataset ? stateEl.dataset.stblSelected : undefined;
    const initialSelected = savedSel !== undefined
        ? JSON.parse(savedSel)
        : [];
    const selected = new Set(initialSelected);
    if (stateEl.dataset) {
        // Record the current mode and drop any saved selection from another
        // mode. (The restore above is already gated on ``modeMatches``, so
        // ``selected`` / ``selectedCell`` start empty on a mode change.)
        if (!modeMatches) {
            delete stateEl.dataset.stblSelected;
            delete stateEl.dataset.stblSelectedCell;
        }
        stateEl.dataset.stblMode = mode;
    }
    const filtering = model.filtering;
    const filterable = filtering === "table" || filtering === "both";
    const columnFilter = filtering === "column" || filtering === "both";
    // ``sorting`` may be true/false or a fixed direction string. A fixed
    // direction restricts each column to that one order (toggle on/off).
    const sortOpt = model.sorting;
    const fixedDir =
        sortOpt === "ascending" ? 1
        : sortOpt === "descending" ? -1
        : 0;
    const sorting = fixedDir !== 0 || sortOpt === true;
    // Rows per page (a positive integer) or 0/false to show everything.
    const pageSize =
        typeof model.pageSize === "number" && model.pageSize > 0
            ? Math.floor(model.pageSize)
            : 0;
    const switchPage = model.switchPage || "number";
    let currentPage = 0;
    // Standard controls are optional; custom controls automatically enable
    // the toolbar when at least one custom action is supplied.
    const showStandard = model.standardToolbar === true;
    const showCustom = Array.isArray(model.customToolbar) &&
        model.customToolbar.length > 0;
    const showToolbar = showStandard || showCustom;
    const inactiveStandard = new Set(
        Array.isArray(model.standardToolbarExclude)
            ? model.standardToolbarExclude
            : []
    );
    const toolbarAlign = model.toolbarAlign === "left"
        ? "flex-start"
        : model.toolbarAlign === "center"
            ? "center"
            : "flex-end";
    // Custom toolbar icons (Material name / ":material/x:" / emoji).
    const customIcons = Array.isArray(model.customToolbar)
        ? model.customToolbar
        : [];
    let columnPop = null;
    let clearFiltersBtn = null;
    // Preselected cell as [rowIndex, colIndex] or null (restored from a
    // previous mount when present).
    const savedCell =
        modeMatches && stateEl.dataset
            ? stateEl.dataset.stblSelectedCell
            : undefined;
    let selectedCell = savedCell !== undefined
        ? JSON.parse(savedCell)
        : null;

    // Per-column filter state: { value: string, exclude: bool }.
    const colFilters = columns.map(() => ({ value: "", exclude: false }));
    const activeColumns = Array.isArray(model.activeColumns)
        ? new Set(model.activeColumns)
        : null;
    const visibleColumns = columns.map(
        (label) => activeColumns === null || activeColumns.has(label)
    );
    const columnElements = columns.map(() => []);
    // Collected references so filtering/sorting can reorder/show/hide rows.
    const rowEls = [];        // <tr> per row (indexed by original row id)
    const rowCells = [];      // raw cell text per row
    let sortCol = -1;         // currently sorted column index, or -1
    let sortDir = 0;          // 1 asc, -1 desc, 0 none
    const sortButtonSetters = [];  // updates each column's button highlight
    function refreshSortButtons() {
        sortButtonSetters.forEach((fn) => fn());
    }

    // Reorder the tbody rows according to the current sort state. Sorting
    // only reorders <tr> elements; it never changes their data-id, so
    // selection and filtering stay correct.
    function sortRows() {
        const order = rowEls.map((tr, idx) => idx);
        if (sortCol >= 0 && sortDir !== 0) {
            order.sort((a, b) => {
                const va = (rowCells[a][sortCol] || "");
                const vb = (rowCells[b][sortCol] || "");
                const na = parseFloat(va);
                const nb = parseFloat(vb);
                let cmp;
                if (!isNaN(na) && !isNaN(nb) && va !== "" && vb !== "") {
                    cmp = na - nb;
                } else {
                    cmp = va.localeCompare(vb, undefined, {
                        numeric: true,
                        sensitivity: "base",
                    });
                }
                return cmp * sortDir;
            });
        }
        order.forEach((idx) => tbody.appendChild(rowEls[idx]));
        // Keep filler rows at the very bottom after reordering.
        fillerRows.forEach((tr) => tbody.appendChild(tr));
    }

    function emit() {
        const val = JSON.stringify(Array.from(selected));
        if (stateEl.dataset) stateEl.dataset.stblSelected = val;
        setTriggerValue("selection", val);
    }
    function emitCell() {
        const val = JSON.stringify(selectedCell);
        if (stateEl.dataset) stateEl.dataset.stblSelectedCell = val;
        setTriggerValue("selection", val);
    }
    // Clear all selection state and visuals. When ``notify`` is false the
    // selection is cleared without sending a trigger to Python (avoids a
    // rerun that would re-mount the component mid-interaction, e.g. sorting).
    function clearSelection(notify) {
        selected.clear();
        selectedCell = null;
        if (tbody) {
            tbody.querySelectorAll(".selected")
                .forEach((el) => el.classList.remove("selected"));
            tbody.querySelectorAll("input[type='checkbox'], input[type='radio']")
                .forEach((el) => { el.checked = false; });
        }
        if (stateEl.dataset) {
            delete stateEl.dataset.stblSelected;
            delete stateEl.dataset.stblSelectedCell;
        }
        if (notify) {
            if (cellMode) emitCell();
            else emit();
        }
    }

    const wrapper = document.createElement("div");
    wrapper.className = "stbl";

    // Shared themed tooltip for truncated cells.
    const tooltip = document.createElement("div");
    tooltip.className = "stbl-tooltip";
    tooltip.style.display = "none";

    // Optional toolbar with an export (download CSV) button.
    // Render an icon (":material/x:" or "x" -> Material glyph, else emoji).
    function renderIcon(el, icon) {
        const m = /^:material\/([a-z0-9_]+):$/.exec(icon) ||
            /^([a-z0-9_]+)$/.exec(icon || "");
        if (m) {
            el.className = "material-symbols-rounded";
            el.textContent = m[1];
        } else {
            el.textContent = icon || "";
        }
    }

    if (showToolbar) {
        const bar = document.createElement("div");
        bar.className = "stbl-toolbar";
        bar.style.justifyContent = toolbarAlign;

        if (showStandard) {
            // Every standard toolbar control must have a matching value in
            // StandardToolbarAction for standard_toolbar_exclude support.
            const exportBtn = document.createElement("button");
            exportBtn.type = "button";
            exportBtn.className = "toolbar-btn";
            exportBtn.disabled = inactiveStandard.has("export_csv");
            exportBtn.title = "Export as CSV";
            const exportIcon = document.createElement("span");
            exportIcon.className = "material-symbols-rounded";
            exportIcon.textContent = "download";
            exportBtn.appendChild(exportIcon);
            exportBtn.onclick = () => exportCsv();
            bar.appendChild(exportBtn);

            columnPop = document.createElement("div");
            columnPop.className = "stbl-column-pop";
            columnPop.style.display = "none";
            columns.forEach((label, colIndex) => {
                const option = document.createElement("label");
                option.className = "stbl-column-option";
                const checkbox = document.createElement("input");
                checkbox.type = "checkbox";
                checkbox.checked = visibleColumns[colIndex];
                checkbox.onchange = () => {
                    const visibleCount = visibleColumns.filter(Boolean).length;
                    if (!checkbox.checked && visibleCount <= 1) {
                        checkbox.checked = true;
                        return;
                    }
                    visibleColumns[colIndex] = checkbox.checked;
                    refreshColumnVisibility();
                    columnBtn.classList.toggle(
                        "active", visibleColumns.some((visible) => !visible)
                    );
                };
                option.appendChild(checkbox);
                option.appendChild(document.createTextNode(label));
                columnPop.appendChild(option);
            });
            // Keep checkbox clicks inside the popover from reaching the
            // document outside-click handler and closing the menu.
            columnPop.onclick = (e) => e.stopPropagation();

            const columnBtn = document.createElement("button");
            columnBtn.type = "button";
            columnBtn.className = "toolbar-btn";
            columnBtn.disabled = inactiveStandard.has("select_columns");
            columnBtn.title = "Select columns";
            const columnIcon = document.createElement("span");
            columnIcon.className = "material-symbols-rounded";
            columnIcon.textContent = "view_column";
            columnBtn.appendChild(columnIcon);
            columnBtn.classList.toggle(
                "active", visibleColumns.some((visible) => !visible)
            );
            columnBtn.onclick = (e) => {
                e.stopPropagation();
                columnPop.style.display =
                    columnPop.style.display === "none" ? "block" : "none";
            };
            bar.appendChild(columnBtn);
            bar.appendChild(columnPop);

            if (filtering !== false) {
                clearFiltersBtn = document.createElement("button");
                clearFiltersBtn.type = "button";
                clearFiltersBtn.className =
                    "toolbar-btn dynamic-toolbar-btn";
                // Dynamic toolbar actions stay on the button group's outer
                // edge: left for right alignment, right for left or center.
                // Keep this rule for every future dynamic toolbar action.
                clearFiltersBtn.style.order =
                    toolbarAlign === "flex-end" ? "-1" : "1";
                clearFiltersBtn.title = "Clear all filters";
                const clearFiltersIcon = document.createElement("span");
                clearFiltersIcon.className = "material-symbols-rounded";
                clearFiltersIcon.textContent = "filter_alt_off";
                clearFiltersBtn.appendChild(clearFiltersIcon);
                clearFiltersBtn.disabled = inactiveStandard.has("clear_filters");
                bar.appendChild(clearFiltersBtn);
            }
        }

        if (showCustom) {
            customIcons.forEach((icon, i) => {
                const btn = document.createElement("button");
                btn.type = "button";
                btn.className = "toolbar-btn";
                const span = document.createElement("span");
                renderIcon(span, icon);
                btn.appendChild(span);
                btn.onclick = () => {
                    // Notify Python: which custom action was clicked. A nonce
                    // ensures repeated clicks always register as a change.
                    setTriggerValue(
                        "toolbarAction",
                        JSON.stringify({ index: i, nonce: Date.now() })
                    );
                };
                bar.appendChild(btn);
            });
        }

        wrapper.appendChild(bar);
    }

    // Build a CSV of the currently matching rows (respecting filters and the
    // active sort order) and trigger a download.
    function exportCsv() {
        const esc = (v) => {
            const s = v === undefined || v === null ? "" : String(v);
            return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
        };
        const lines = [columns.map(esc).join(",")];
        // Iterate rows in current DOM (sorted) order; export all matching
        // rows across every page, skipping filler rows.
        Array.from(tbody.children).forEach((tr) => {
            if (tr.classList.contains("filler-row")) return;
            if (!rowMatches(tr)) return;
            const r = rowEls.indexOf(tr);
            if (r < 0) return;
            lines.push(rows[r].map(esc).join(","));
        });
        const blob = new Blob([lines.join("\n")], {
            type: "text/csv;charset=utf-8;",
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "table.csv";
        a.click();
        URL.revokeObjectURL(url);
    }

    // Optional filter box.
    let filterInput = null;
    if (filterable) {
        filterInput = document.createElement("input");
        filterInput.type = "text";
        filterInput.className = "stbl-filter";
        filterInput.placeholder = "Filter...";
        wrapper.appendChild(filterInput);
    }

    const table = document.createElement("table");
    // Column sizing: "auto" (fixed layout, ellipsis) or "content" (size to
    // content, no truncation).
    table.classList.add(
        model.columnWidth === "content" ? "cw-content" : "cw-auto"
    );
    const coloredRows = model.coloredRows === true;

    // Header row.
    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");
    if (selectable) {
        const th = document.createElement("th");
        th.className = "select-col";
        headRow.appendChild(th);
    }
    columns.forEach((label, colIndex) => {
        const th = document.createElement("th");
        th.dataset.col = String(colIndex);
        th.style.display = visibleColumns[colIndex] ? "" : "none";
        columnElements[colIndex].push(th);
        if (columnFilter) {
            const head = document.createElement("div");
            head.className = "th-head";

            const labelEl = document.createElement("span");
            labelEl.textContent = label;
            head.appendChild(labelEl);

            const icon = document.createElement("span");
            icon.className = "filter-icon material-symbols-rounded";
            icon.textContent = "filter_alt";
            head.appendChild(icon);

            // Popover with value input + exclude checkbox.
            const pop = document.createElement("div");
            pop.className = "filter-pop";
            pop.style.display = "none";

            const valInput = document.createElement("input");
            valInput.type = "text";
            valInput.className = "stbl-filter";
            valInput.placeholder = "Value...";
            pop.appendChild(valInput);

            const exLabel = document.createElement("label");
            exLabel.className = "filter-exclude";
            const exCb = document.createElement("input");
            exCb.type = "checkbox";
            exLabel.appendChild(exCb);
            exLabel.appendChild(document.createTextNode("Exclude"));
            pop.appendChild(exLabel);

            const clearBtn = document.createElement("button");
            clearBtn.type = "button";
            clearBtn.className = "filter-clear";
            const clearIcon = document.createElement("span");
            clearIcon.className = "material-symbols-rounded";
            clearIcon.textContent = "delete";
            clearBtn.appendChild(clearIcon);
            clearBtn.appendChild(document.createTextNode("Clear"));
            pop.appendChild(clearBtn);

            const positionPop = () => {
                if (pop.style.display === "none") return;
                const r = icon.getBoundingClientRect();
                const sidebar = stateEl.ownerDocument.querySelector(
                    '[data-testid="stSidebar"]'
                );
                const minLeft = Math.max(
                    8,
                    (sidebar ? sidebar.getBoundingClientRect().right : 0) + 8
                );
                const availableWidth = window.innerWidth - minLeft - 8;
                if (pop.offsetWidth > availableWidth) {
                    pop.style.minWidth = "0";
                    pop.style.width = Math.max(0, availableWidth) + "px";
                } else {
                    pop.style.minWidth = "";
                    pop.style.width = "";
                }
                const popWidth = pop.offsetWidth || 192;
                let left = r.right - popWidth;
                if (left < minLeft) left = minLeft;
                const maxLeft = Math.max(
                    minLeft,
                    window.innerWidth - popWidth - 8
                );
                if (left > maxLeft) left = maxLeft;
                pop.style.left = left + "px";
                pop.style.top = r.bottom + 4 + "px";
            };
            // Capture scroll events from Streamlit's scrolling main section.
            window.addEventListener("scroll", positionPop, true);
            window.addEventListener("resize", positionPop);
            const sidebar = stateEl.ownerDocument.querySelector(
                '[data-testid="stSidebar"]'
            );
            const sidebarObserver = sidebar ? new ResizeObserver(positionPop) : null;
            if (sidebarObserver) sidebarObserver.observe(sidebar);

            const apply = () => {
                colFilters[colIndex] = {
                    value: valInput.value.trim().toLowerCase(),
                    exclude: exCb.checked,
                };
                icon.classList.toggle(
                    "active",
                    colFilters[colIndex].value !== "" || exCb.checked
                );
                currentPage = 0;  // reset to first page when filtering
                applyFilters();
            };
            valInput.oninput = apply;
            exCb.onchange = apply;
            clearBtn.onclick = () => {
                valInput.value = "";
                exCb.checked = false;
                apply();
            };

            icon.onclick = (e) => {
                e.stopPropagation();
                // Close any other open popover.
                thead.querySelectorAll(".filter-pop").forEach((p) => {
                    if (p !== pop) p.style.display = "none";
                });
                const opening = pop.style.display === "none";
                pop.style.display = opening ? "block" : "none";
                if (opening) {
                    positionPop();
                    // Focus the value input for immediate typing.
                    valInput.focus();
                }
            };
            // Prevent clicks inside the popover from closing it.
            pop.onclick = (e) => e.stopPropagation();
            pop._cleanup = () => {
                window.removeEventListener("scroll", positionPop, true);
                window.removeEventListener("resize", positionPop);
                if (sidebarObserver) sidebarObserver.disconnect();
            };

            head.appendChild(pop);
            th.appendChild(head);
        } else {
            th.textContent = label;
        }

        if (sorting) {
            // Ensure a flex header layout exists (columnFilter already made
            // one as ".th-head"; otherwise build it now).
            let head = th.querySelector(".th-head");
            if (!head) {
                th.textContent = "";
                head = document.createElement("div");
                head.className = "th-head";
                const labelEl = document.createElement("span");
                labelEl.textContent = label;
                head.appendChild(labelEl);
                th.appendChild(head);
            }

            const chevronSvg = (points) =>
                '<svg viewBox="6 8 12 8" width="9" height="6" ' +
                'fill="none" stroke="currentColor" stroke-width="2" ' +
                'stroke-linecap="round" stroke-linejoin="round">' +
                '<polyline points="' + points + '"></polyline></svg>';

            const sortBtns = document.createElement("span");
            sortBtns.className = "sort-btns";
            const upBtn = document.createElement("span");
            upBtn.className = "sort-btn sort-up";
            upBtn.innerHTML = chevronSvg("6 15 12 9 18 15");   // chevron up
            const downBtn = document.createElement("span");
            downBtn.className = "sort-btn sort-down";
            downBtn.innerHTML = chevronSvg("6 9 12 15 18 9");  // chevron down
            // With a fixed order only the relevant arrow is shown.
            if (fixedDir === 0 || fixedDir === 1) sortBtns.appendChild(upBtn);
            if (fixedDir === 0 || fixedDir === -1) sortBtns.appendChild(downBtn);

            // Always place the sort buttons at the far right of the header,
            // after the filter icon.
            head.appendChild(sortBtns);

            sortBtns.style.cursor = "pointer";
            sortBtns.onclick = (e) => {
                e.stopPropagation();
                if (fixedDir !== 0) {
                    // Restricted: toggle this column on/off in the fixed
                    // direction only.
                    if (sortCol === colIndex && sortDir === fixedDir) {
                        sortCol = -1;
                        sortDir = 0;
                    } else {
                        sortCol = colIndex;
                        sortDir = fixedDir;
                    }
                } else if (sortCol !== colIndex) {
                    // Full cycle: none -> ascending -> descending -> none.
                    sortCol = colIndex;
                    sortDir = 1;
                } else if (sortDir === 1) {
                    sortDir = -1;
                } else {
                    sortCol = -1;
                    sortDir = 0;
                }
                refreshSortButtons();
                clearSelection(false);  // sorting drops the selection
                sortRows();
                currentPage = 0;  // reset to first page after re-sorting
                applyFilters();
            };

            sortButtonSetters.push(() => {
                upBtn.classList.toggle(
                    "active", sortCol === colIndex && sortDir === 1
                );
                downBtn.classList.toggle(
                    "active", sortCol === colIndex && sortDir === -1
                );
            });
        }

        headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);

    // Body rows.
    const tbody = document.createElement("tbody");
    const inputs = {};

    function setRowSelected(tr, id, isSelected) {
        if (isSelected) {
            selected.add(id);
            tr.classList.add("selected");
        } else {
            selected.delete(id);
            tr.classList.remove("selected");
        }
        if (inputs[id]) inputs[id].checked = isSelected;
    }

    rows.forEach((row, rowIndex) => {
        const tr = document.createElement("tr");
        const id = String(rowIndex);
        if (selected.has(id)) tr.classList.add("selected");

        if (selectable) {
            const td = document.createElement("td");
            td.className = "select-col";
            const input = document.createElement("input");
            input.type = mode === "single" ? "radio" : "checkbox";
            input.name = "stbl-select";
            input.checked = selected.has(id);
            inputs[id] = input;
            td.appendChild(input);
            tr.appendChild(td);
        }

        const searchParts = [];
        const cellTexts = [];
        columns.forEach((label, i) => {
            const td = document.createElement("td");
            td.dataset.col = String(i);
            td.style.display = visibleColumns[i] ? "" : "none";
            columnElements[i].push(td);
            const value = row[i];
            const text =
                value === undefined || value === null ? "" : String(value);
            td.textContent = text;
            // Themed tooltip (follows the Streamlit theme) shown only when
            // the cell text is actually truncated.
            if (text) {
                td.addEventListener("mouseenter", () => {
                    if (td.scrollWidth <= td.clientWidth) return;
                    tooltip.textContent = text;
                    tooltip.style.display = "block";
                    const r = td.getBoundingClientRect();
                    let left = r.left;
                    const maxLeft = window.innerWidth - tooltip.offsetWidth - 8;
                    if (left > maxLeft) left = Math.max(8, maxLeft);
                    tooltip.style.left = left + "px";
                    tooltip.style.top = r.bottom + 4 + "px";
                });
                td.addEventListener("mouseleave", () => {
                    tooltip.style.display = "none";
                });
            }
            searchParts.push(text.toLowerCase());
            cellTexts.push(text.toLowerCase());

            if (cellMode) {
                td.classList.add("cell-selectable");
                if (
                    selectedCell &&
                    selectedCell[0] === rowIndex &&
                    selectedCell[1] === i
                ) {
                    td.classList.add("selected");
                }
                td.onclick = () => {
                    tbody
                        .querySelectorAll("td.cell-selectable.selected")
                        .forEach((el) => el.classList.remove("selected"));
                    td.classList.add("selected");
                    selectedCell = [rowIndex, i];
                    emitCell();
                };
            }
            tr.appendChild(td);
        });
        tr.dataset.search = searchParts.join(" ");
        rowEls.push(tr);
        rowCells.push(cellTexts);

        if (selectable) {
            const toggle = () => {
                if (mode === "single") {
                    // Clear others, select this one.
                    selected.forEach((sid) => {
                        const otherTr = tbody.querySelector(
                            `tr[data-id="${sid}"]`
                        );
                        if (otherTr) otherTr.classList.remove("selected");
                        if (inputs[sid]) inputs[sid].checked = false;
                    });
                    selected.clear();
                    setRowSelected(tr, id, true);
                } else {
                    setRowSelected(tr, id, !selected.has(id));
                }
                emit();
            };
            tr.dataset.id = id;
            tr.onclick = toggle;
        }

        tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    wrapper.appendChild(table);

    // Filler rows keep the table height constant on partially filled pages.
    const fillerRows = [];
    const colCount = columns.length + (selectable ? 1 : 0);
    if (pageSize > 0) {
        for (let i = 0; i < pageSize; i++) {
            const tr = document.createElement("tr");
            tr.className = "filler-row";
            tr.style.display = "none";
            for (let c = 0; c < colCount; c++) {
                const td = document.createElement("td");
                td.innerHTML = "&nbsp;";
                tr.appendChild(td);
                if (c < columns.length) columnElements[c].push(td);
            }
            tbody.appendChild(tr);
            fillerRows.push(tr);
        }
    }

    function refreshColumnVisibility() {
        let lastVisible = -1;
        visibleColumns.forEach((visible, colIndex) => {
            if (visible) lastVisible = colIndex;
        });
        columnElements.forEach((elements, colIndex) => {
            const visible = visibleColumns[colIndex];
            elements.forEach((el) => {
                el.style.display = visible ? "" : "none";
                el.classList.toggle(
                    "visible-column-last", visible && colIndex === lastVisible
                );
            });
        });
    }
    refreshColumnVisibility();

    // Pagination controls (only rendered when pageSize > 0).
    const pager = document.createElement("div");
    pager.className = "stbl-pager";
    let pageMenuCleanup = null;
    if (pageSize > 0) wrapper.appendChild(pager);

    // Whether a row passes the current table + column filters.
    function rowMatches(tr) {
        const r = rowEls.indexOf(tr);
        const cells = rowCells[r];
        const q = filterInput ? filterInput.value.trim().toLowerCase() : "";
        if (q && !(tr.dataset.search || "").includes(q)) return false;
        for (let c = 0; c < colFilters.length; c++) {
            const f = colFilters[c];
            if (!f.value) continue;
            const has = (cells[c] || "").includes(f.value);
            if (f.exclude ? has : !has) return false;
        }
        return true;
    }

    function renderPager(totalPages) {
        if (pageMenuCleanup) {
            pageMenuCleanup();
            pageMenuCleanup = null;
        }
        pager.textContent = "";
        if (pageSize <= 0 || totalPages <= 1) return;

        if (switchPage === "selectbox") {
            const select = document.createElement("button");
            select.type = "button";
            select.className = "page-select";
            select.setAttribute("aria-label", "Select page");
            select.setAttribute("aria-haspopup", "listbox");
            select.setAttribute("aria-expanded", "false");
            select.textContent = String(currentPage + 1);
            const menu = document.createElement("div");
            menu.className = "page-menu";
            menu.setAttribute("role", "listbox");
            menu.style.display = "none";
            const menuList = document.createElement("div");
            menuList.className = "page-menu-list";
            menuList.setAttribute("role", "presentation");
            let pageArrow = null;
            let pageArrowUp = null;
            for (let p = 0; p < totalPages; p++) {
                const option = document.createElement("button");
                option.type = "button";
                option.className = "page-option" +
                    (p === currentPage ? " active" : "");
                option.setAttribute("role", "option");
                option.setAttribute("aria-selected", String(p === currentPage));
                option.textContent = String(p + 1);
                option.onclick = (e) => {
                    e.stopPropagation();
                    closeMenu();
                    clearSelection(false);  // changing page drops the selection
                    currentPage = p;
                    updatePageArrow();
                    applyFilters();
                };
                menuList.appendChild(option);
            }
            menu.appendChild(menuList);
            if (menuList.childElementCount > 3) {
                pageArrow = document.createElement("span");
                pageArrow.className = "page-menu-arrow";
                pageArrow.textContent = "expand_more";
                pageArrow.title = "More pages below";
                menu.appendChild(pageArrow);
                pageArrowUp = document.createElement("span");
                pageArrowUp.className = "page-menu-arrow-up";
                pageArrowUp.textContent = "expand_less";
                pageArrowUp.title = "More pages above";
                menu.appendChild(pageArrowUp);
            }
            const updatePageArrow = () => {
                menu.classList.toggle(
                    "last-page", currentPage >= totalPages - 1
                );
                if (pageArrow) {
                    pageArrow.style.display =
                        currentPage < totalPages - 1 &&
                        menuList.scrollTop + menuList.clientHeight <
                            menuList.scrollHeight - 1
                            ? ""
                            : "none";
                }
                if (pageArrowUp) {
                    pageArrowUp.style.display = menuList.scrollTop > 0
                        ? ""
                        : "none";
                }
            };
            menuList.addEventListener("scroll", updatePageArrow);
            updatePageArrow();
            const positionMenu = () => {
                if (menu.style.display === "none") return;
                const rect = select.getBoundingClientRect();
                menu.style.left = rect.left + rect.width / 2 + "px";
                menu.style.top = rect.bottom + 4 + "px";
            };
            const closeMenu = () => {
                menu.style.display = "none";
                select.setAttribute("aria-expanded", "false");
                window.removeEventListener("scroll", positionMenu, true);
                window.removeEventListener("resize", positionMenu);
                menuList.removeEventListener("scroll", updatePageArrow);
                if (pageMenuCleanup === closeMenu) pageMenuCleanup = null;
            };
            menu._close = closeMenu;
            select.onclick = (e) => {
                e.stopPropagation();
                const isOpen = menu.style.display !== "none";
                if (!isOpen) {
                    menu.style.display = "block";
                    select.setAttribute("aria-expanded", "true");
                    const activeOption = menuList.querySelector(
                        ".page-option.active"
                    );
                    if (activeOption) {
                        menuList.scrollTop = Math.max(
                            0,
                            activeOption.offsetTop -
                                (menuList.clientHeight - activeOption.offsetHeight) / 2
                        );
                    }
                    positionMenu();
                    updatePageArrow();
                    window.addEventListener("scroll", positionMenu, true);
                    window.addEventListener("resize", positionMenu);
                    pageMenuCleanup = closeMenu;
                    return;
                }
                closeMenu();
            };
            pager.appendChild(select);
            pager.appendChild(menu);
            return;
        }

        const chevron = (direction) =>
            '<svg viewBox="0 0 24 24" width="10" height="10" ' +
            'fill="none" stroke="currentColor" stroke-width="3" ' +
            'stroke-linecap="round" stroke-linejoin="round">' +
            '<polyline points="' +
            (direction === "left" ? "15 6 9 12 15 18" : "9 6 15 12 9 18") +
            '"></polyline></svg>';
        const makeButton = (content, page, options) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "pager-btn" +
                (options.active ? " active" : "");
            button.innerHTML = content;
            if (options.disabled) {
                button.disabled = true;
            } else {
                button.onclick = () => {
                    clearSelection(false);  // changing page drops the selection
                    currentPage = page;
                    applyFilters();
                };
            }
            return button;
        };
        pager.appendChild(makeButton(chevron("left"), currentPage - 1, {
            disabled: currentPage === 0,
        }));
        const pageTokens = [];
        if (totalPages <= 7 || currentPage <= 3) {
            for (let page = 0; page < Math.min(5, totalPages); page++) {
                pageTokens.push(page);
            }
            if (totalPages > 6) pageTokens.push("gap", totalPages - 1);
        } else if (currentPage >= totalPages - 4) {
            pageTokens.push(0, "gap");
            for (let page = Math.max(1, totalPages - 5); page < totalPages; page++) {
                pageTokens.push(page);
            }
        } else {
            pageTokens.push(
                0, "gap", currentPage - 1, currentPage, currentPage + 1,
                "gap", totalPages - 1
            );
        }
        let previousToken = null;
        pageTokens.forEach((page) => {
            if (page === "gap") {
                const gap = document.createElement("span");
                gap.className = "page-gap";
                gap.textContent = "...";
                pager.appendChild(gap);
            } else if (page !== previousToken) {
                pager.appendChild(makeButton(String(page + 1), page, {
                    active: page === currentPage,
                }));
            }
            previousToken = page;
        });
        pager.appendChild(makeButton(chevron("right"), currentPage + 1, {
            disabled: currentPage >= totalPages - 1,
        }));
    }

    // Central filter + pagination: show only matching rows on the current
    // page. Combines the table-wide filter and per-column filters.
    function applyFilters() {
        // Matching data rows in current DOM (sorted) order, so banding,
        // pagination and the last-row border all follow what is shown.
        const matching = Array.from(tbody.children).filter(
            (tr) =>
                !tr.classList.contains("filler-row") && rowMatches(tr)
        );

        let startIdx = 0;
        let endIdx = matching.length;
        let totalPages = 1;
        if (pageSize > 0) {
            totalPages = Math.max(1, Math.ceil(matching.length / pageSize));
            if (currentPage > totalPages - 1) currentPage = totalPages - 1;
            if (currentPage < 0) currentPage = 0;
            startIdx = currentPage * pageSize;
            endIdx = startIdx + pageSize;
        }

        // Hide everything, then reveal only the current page's slice.
        rowEls.forEach((tr) => { tr.style.display = "none"; });
        const pageRows = matching.slice(startIdx, endIdx);
        pageRows.forEach((tr, i) => {
            tr.style.display = "";
            // Band alternating visible rows (correct across pages/filtering).
            if (coloredRows) tr.classList.toggle("banded", i % 2 === 1);
        });

        // Track the last visible row so its bottom border can be removed
        // (mirrors the last-row look regardless of page/filler state).
        let lastVisible = pageRows[pageRows.length - 1] || null;

        // Fill the rest of the page with empty rows so the table height is
        // constant. Keep the fillers below the visible data rows.
        if (pageSize > 0) {
            const need = pageSize - pageRows.length;
            fillerRows.forEach((tr, i) => {
                if (i < need) {
                    tbody.appendChild(tr);  // move to the bottom
                    tr.style.display = "";
                    lastVisible = tr;
                } else {
                    tr.style.display = "none";
                }
            });
        }

        // Only the last visible row drops its bottom border, so every page
        // has the same clean bottom edge.
        rowEls.forEach((tr) => tr.classList.remove("no-bottom-border"));
        fillerRows.forEach((tr) => tr.classList.remove("no-bottom-border"));
        if (lastVisible) lastVisible.classList.add("no-bottom-border");

        renderPager(totalPages);
        if (clearFiltersBtn) {
            const columnFiltersActive = colFilters.some(
                (filter) => filter.value !== "" || filter.exclude
            );
            const tableFilterActive = filterInput &&
                filterInput.value.trim() !== "";
            clearFiltersBtn.disabled = inactiveStandard.has("clear_filters") ||
                !(columnFiltersActive || tableFilterActive);
        }
    }

    if (filterInput) {
        filterInput.oninput = () => {
            currentPage = 0;  // reset to first page on a new search
            applyFilters();
        };
    }

    if (clearFiltersBtn) {
        clearFiltersBtn.onclick = (e) => {
            e.stopPropagation();
            if (filterInput) filterInput.value = "";
            colFilters.forEach((filter) => {
                filter.value = "";
                filter.exclude = false;
            });
            thead.querySelectorAll(".filter-icon").forEach((icon) => {
                icon.classList.remove("active");
            });
            thead.querySelectorAll(".filter-pop").forEach((pop) => {
                const input = pop.querySelector(".stbl-filter");
                const checkbox = pop.querySelector("input[type='checkbox']");
                if (input) input.value = "";
                if (checkbox) checkbox.checked = false;
            });
            currentPage = 0;
            applyFilters();
        };
    }

    // Close open column-filter popovers when clicking elsewhere.
    const onDocClick = () => {
        if (columnFilter) {
            thead.querySelectorAll(".filter-pop").forEach((p) => {
                p.style.display = "none";
            });
        }
        if (columnPop) columnPop.style.display = "none";
        const pageMenu = pager.querySelector(".page-menu");
        const pageSelect = pager.querySelector(".page-select");
        if (pageMenu && pageMenu._close) pageMenu._close();
        else if (pageMenu) pageMenu.style.display = "none";
        if (pageSelect) pageSelect.setAttribute("aria-expanded", "false");
    };
    document.addEventListener("click", onDocClick);

    // Material Symbols font for the filter icons.
    if (columnFilter || sorting || showToolbar) {
        const fontLink = document.createElement("link");
        fontLink.className = "stbl-font";
        fontLink.rel = "stylesheet";
        fontLink.href =
            "https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded";
        parentElement.appendChild(fontLink);
    }

    parentElement.appendChild(wrapper);
    parentElement.appendChild(tooltip);
    applyFilters();

    return () => {
        document.removeEventListener("click", onDocClick);
        thead.querySelectorAll(".filter-pop").forEach((pop) => {
            if (pop._cleanup) pop._cleanup();
        });
        parentElement.querySelectorAll("link.stbl-font").forEach((el) =>
            el.remove()
        );
        tooltip.remove();
        wrapper.remove();
    };
}
"""

_smart_table_component = st.components.v2.component(
    name="smart_table",
    css=_SMART_TABLE_CSS,
    js=_SMART_TABLE_JS,
)


def _excel_column_name(index: int) -> str:
    """Return a zero-based column index as an Excel-style label."""
    label = ""
    while index >= 0:
        index, remainder = divmod(index, 26)
        label = chr(ord("A") + remainder) + label
        index -= 1
    return label


def smart_table(
    columns: Optional[List[str]] = None,
    rows: Optional[List[List[Any]]] = None,
    *,
    selecting: Literal["single", "multiple", "cell", "none"] = "none",
    on_select: Optional[Callable[[Any], None]] = None,
    key: Optional[str] = None,
    width: Width = "stretch",
    filtering: Union[bool, Literal["table", "column", "both"]] = False,
    sorting: Union[bool, Literal["ascending", "descending"]] = False,
    page_size: Union[bool, int] = False,
    switch_page: Literal["number", "selectbox"] = "number",
    column_width: Literal["auto", "content"] = "auto",
    colored_rows: bool = False,
    standard_toolbar: bool = True,
    standard_toolbar_exclude: Optional[
        Union[StandardToolbarAction, List[StandardToolbarAction]]
    ] = None,
    toolbar_align: Literal["left", "center", "right"] = "right",
    custom_toolbar: Optional[List[List[Any]]] = None,
    active_columns: Optional[List[str]] = None,
) -> Any:
    """Render a table with configurable selection.

    Args:
        columns: Optional column labels. When omitted, columns are named using
            Excel-style labels: ``A`` through ``Z``, then ``AA``, ``AB``, and
            so on. A column's position is its key.
        rows: Optional list of rows, each a list of cell values aligned to
            ``columns`` by position. A row's id is its index (as a string).
        selecting: ``"single"`` (one row), ``"multiple"`` (many rows),
            ``"cell"`` (one cell) or ``"none"`` (default, not selectable).
        on_select: Optional callback invoked with the current selection. In
            row modes it receives the list of selected ids; in cell mode it
            receives ``[row_index, col_index]`` or ``None``.
        key: Optional Streamlit widget key.
        width: Width of the table. ``"stretch"`` (default), ``"content"``, or a
            fixed pixel width.
        filtering: Filtering mode. ``"table"`` shows a single search box that
            filters the whole table by a case-insensitive match across all
            cells. ``"column"`` shows a filter icon on each column header with
            a popover to filter (or exclude) that column; column filters
            combine (AND). ``"both"`` enables the table and column filters at
            the same time. ``False`` (default) disables filtering.
        sorting: Column sorting. ``True`` shows sort controls that cycle
            ascending -> descending -> unsorted. ``"ascending"`` or
            ``"descending"`` restrict each column to that single direction
            (toggle on/off). ``False`` (default) disables sorting. Sorting is
            numeric-aware and happens client-side.
        page_size: Rows shown per page. An integer (e.g. ``5``) paginates the
            table with page controls below it. ``False`` (default) shows all
            rows without pagination.
        switch_page: Pagination control to render. ``"number"`` shows arrow
            and numbered buttons; ``"selectbox"`` shows a page selectbox.
            Defaults to ``"number"``.
        column_width: How columns are sized. ``"auto"`` (default) gives evenly
            sized columns and truncates overflowing text with an ellipsis.
            ``"content"`` sizes each column to its content without truncation.
        colored_rows: When ``True``, alternating rows get a subtle background
            tint (zebra striping). Defaults to ``False``.
        standard_toolbar: Whether to show the standard toolbar buttons
            (export to CSV and column selection, plus clear filters when
            filtering is enabled). Defaults to ``True``.
        standard_toolbar_exclude: One standard toolbar action or a list of
            actions to disable. Supported values are ``"select_columns"``,
            ``"export_csv"`` and ``"clear_filters"``. Disabled controls remain
            visible.
        toolbar_align: Horizontal alignment of the toolbar buttons: ``"left"``,
            ``"center"`` or ``"right"`` (default).
        custom_toolbar: A list of ``[icon, callback]`` pairs. ``icon`` is an
            emoji or Material symbol (``"download"`` or ``":material/x:"``).
            Clicking the button calls ``callback(selection)`` with the current
            selection (row ids, or the ``[row, col]`` cell in cell mode).
        active_columns: Optional list of column names shown initially. When
            omitted, all columns are visible. The column-selection toolbar
            button reflects this initial set.

    Returns:
        Row modes: the list of selected row ids (empty when none). Cell mode:
        the selected ``[row_index, col_index]`` or ``None``.
    """

    rows = rows or []
    if columns is None or not columns:
        column_count = max((len(row) for row in rows), default=0)
        columns = [_excel_column_name(i) for i in range(column_count)]

    if selecting not in ("single", "multiple", "cell", "none"):
        raise ValueError(
            f"Invalid selecting {selecting!r}. Expected "
            "'single', 'multiple', 'cell' or 'none'."
        )
    if sorting not in (True, False, "ascending", "descending"):
        raise ValueError(
            f"Invalid sorting {sorting!r}. Expected True, False, "
            "'ascending' or 'descending'."
        )
    if filtering not in (False, "table", "column", "both"):
        raise ValueError(
            f"Invalid filtering {filtering!r}. Expected 'table', 'column', 'both' "
            "or False."
        )
    if page_size is not False and (
        not isinstance(page_size, int) or isinstance(page_size, bool) or page_size < 1
    ):
        raise ValueError(
            f"Invalid page_size {page_size!r}. Expected a positive integer or " "False."
        )
    if switch_page not in ("number", "selectbox"):
        raise ValueError(
            f"Invalid switch_page {switch_page!r}. Expected 'number' or " "'selectbox'."
        )
    if column_width not in ("auto", "content"):
        raise ValueError(
            f"Invalid column_width {column_width!r}. Expected 'auto' or " "'content'."
        )
    if not isinstance(standard_toolbar, bool):
        raise ValueError(
            f"Invalid standard_toolbar {standard_toolbar!r}. Expected True or False."
        )
    if standard_toolbar_exclude is None:
        inactive_standard = []
    elif isinstance(standard_toolbar_exclude, str):
        inactive_standard = [standard_toolbar_exclude]
    elif isinstance(standard_toolbar_exclude, list):
        inactive_standard = standard_toolbar_exclude
    else:
        raise ValueError(
            "Invalid standard_toolbar_exclude. Expected a supported action "
            "name or a list of action names."
        )
    valid_standard_actions = {"select_columns", "export_csv", "clear_filters"}
    invalid_standard_actions = [
        action for action in inactive_standard if action not in valid_standard_actions
    ]
    if invalid_standard_actions:
        raise ValueError(
            "Invalid standard_toolbar_exclude values: "
            f"{invalid_standard_actions!r}. Expected one of "
            f"{sorted(valid_standard_actions)!r}."
        )
    if toolbar_align not in ("left", "center", "right"):
        raise ValueError(
            f"Invalid toolbar_align {toolbar_align!r}. Expected 'left', "
            "'center' or 'right'."
        )
    if active_columns is not None:
        if not active_columns:
            raise ValueError(
                "Invalid active_columns. Expected at least one column name."
            )
        if len(set(active_columns)) != len(active_columns):
            raise ValueError("Invalid active_columns. Column names must be unique.")
        unknown_columns = [name for name in active_columns if name not in columns]
        if unknown_columns:
            raise ValueError(
                f"Invalid active_columns. Unknown columns: {unknown_columns!r}."
            )
    custom_toolbar = custom_toolbar or []

    # Persist the selection across re-mounts (e.g. a light/dark theme switch
    # re-mounts the component and would otherwise reset its visual state).
    state_key = f"_stbl_sel_{key}"
    mode_key = f"_stbl_mode_{key}"
    # Changing the selection mode clears any stored selection.
    if st.session_state.get(mode_key) != selecting:
        st.session_state[mode_key] = selecting
        st.session_state.pop(state_key, None)
    stored = st.session_state.get(state_key)
    if selecting == "cell":
        init_cell = stored
        default_selected = []
    else:
        default_selected = list(stored) if stored is not None else []
        init_cell = None

    data = json.dumps(
        {
            "columns": columns,
            "rows": rows,
            "selectionMode": selecting,
            "filtering": filtering,
            "sorting": sorting,
            "pageSize": page_size if page_size is not False else 0,
            "switchPage": switch_page,
            "columnWidth": column_width,
            "coloredRows": colored_rows,
            "standardToolbar": standard_toolbar,
            "standardToolbarExclude": inactive_standard,
            "toolbarAlign": toolbar_align,
            "customToolbar": [item[0] for item in custom_toolbar],
            "activeColumns": active_columns,
        }
    )
    with st.container(width=width):
        result = _smart_table_component(
            data=data,
            on_selection_change=lambda: None,
            on_toolbarAction_change=lambda: None,
            key=key,
        )

    if selecting == "cell":
        if result.selection is not None:
            current = json.loads(result.selection)
        else:
            current = init_cell
    else:
        if result.selection is not None:
            current = json.loads(result.selection)
        else:
            current = default_selected

    # Remember the selection so it survives a re-mount (theme switch, etc.).
    st.session_state[state_key] = current

    if on_select is not None:
        on_select(current)

    # Dispatch a custom-toolbar click to its Python callback. A per-click
    # nonce lets us detect a new click and avoid re-firing on reruns.
    if custom_toolbar and result.toolbarAction is not None:
        action = json.loads(result.toolbarAction)
        nonce_key = f"_stbl_toolbar_nonce_{key}"
        if st.session_state.get(nonce_key) != action.get("nonce"):
            st.session_state[nonce_key] = action.get("nonce")
            idx = action.get("index")
            if idx is not None and 0 <= idx < len(custom_toolbar):
                callback = custom_toolbar[idx][1]
                if callable(callback):
                    callback(current)

    return current


# ---------------------------------------------------------------------------
# Breadcrumbs custom component (Custom Components v2)
# ---------------------------------------------------------------------------

_BREADCRUMBS_CSS = """
.bc {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    font-family: var(--st-font);
    color: var(--st-text-color);
}
.bc a, .bc span.bc-link {
    display: inline-flex;
    align-items: center;
    line-height: 1;
    border-radius: 3rem;
    color: inherit;
    text-decoration: none;
    padding: 0.25rem 0.375rem;
}
.bc.small a, .bc.small span.bc-link { padding: 0.25rem 0.25rem; }
.bc a:hover { background: var(--st-secondary-background-color); }
.bc .bc-sep {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    line-height: 1;
    opacity: 0.6;
    padding: 0.25rem 0;
}
"""

_BREADCRUMBS_JS = r"""
export default function(component) {
    const { data, parentElement, setTriggerValue } = component;
    parentElement.querySelectorAll(".bc").forEach((el) => el.remove());

    const model = JSON.parse(data || "{}");
    const items = model.items || [];
    const size = model.size || "small";
    const separator = model.separator || "\u203a";
    const allDisabled = model.allDisabled === true;

    const labelSize = size === "small" ? "0.75rem" : "0.875rem";
    const sepSize = size === "small" ? "1rem" : "1.125rem";
    const sepMargin = size === "small" ? "0.125rem" : "0.25rem";
    const sepNudge = size === "small" ? "0em" : "-0.05em";

    const root = document.createElement("div");
    root.className = "bc " + size;

    items.forEach((item, i) => {
        const active = !allDisabled && item.page;
        const el = document.createElement(active ? "a" : "span");
        if (active) {
            el.setAttribute("href", item.page);
            el.setAttribute("target", "_self");
        } else {
            el.className = "bc-link";
            el.setAttribute("aria-disabled", "true");
        }
        el.style.fontSize = labelSize;
        el.textContent = item.label;
        root.appendChild(el);

        if (i < items.length - 1) {
            const sep = document.createElement("span");
            sep.className = "bc-sep";
            sep.style.fontSize = sepSize;
            sep.style.margin = "0 " + sepMargin;
            const inner = document.createElement("span");
            inner.style.display = "block";
            inner.style.transform = "translateY(" + sepNudge + ")";
            inner.textContent = separator;
            sep.appendChild(inner);
            root.appendChild(sep);
        }
    });

    parentElement.appendChild(root);
    return () => { root.remove(); };
}
"""

_breadcrumbs_component = st.components.v2.component(
    name="breadcrumbs",
    css=_BREADCRUMBS_CSS,
    js=_BREADCRUMBS_JS,
)


def breadcrumbs(
    items: List[Dict[str, Any]],
    *,
    size: Literal["small", "medium"] = "small",
    separator: str = "\u203a",
    all_links_disabled: bool = False,
    key: Optional[str] = None,
    width: Width = "stretch",
) -> None:
    """Render a horizontal breadcrumb navigation.

    Args:
        items: Ordered items, each ``{"label": str, "page": str|None}``. An
            item with a ``page`` URL navigates in the current tab; one without
            renders as plain text.
        size: Text size, ``"small"`` (default) or ``"medium"``.
        separator: Character or string shown between items. Defaults to ``"›"``.
        all_links_disabled: Disables navigation for every item.
        key: Optional Streamlit widget key.
        width: Width of the widget.
    """
    if size not in ("small", "medium"):
        raise ValueError(f"Invalid size {size!r}. Expected 'small' or 'medium'.")
    data = json.dumps(
        {
            "items": items,
            "size": size,
            "separator": separator,
            "allDisabled": all_links_disabled,
        }
    )
    with st.container(width=width):
        _breadcrumbs_component(data=data, key=key)


# ---------------------------------------------------------------------------
# Persona custom component (Custom Components v2)
# ---------------------------------------------------------------------------

_PERSONA_CSS = """
.persona {
    display: flex;
    align-items: center;
    gap: 0.625rem;
    font-family: var(--st-font);
    color: var(--st-text-color);
}
.persona.bottom { flex-direction: column; }
.persona.left { flex-direction: row-reverse; }
.persona .avatar {
    flex: 0 0 auto;
    object-fit: cover;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
    background: var(--st-secondary-background-color);
    color: var(--st-text-color);
}
.persona .lines { display: flex; flex-direction: column; gap: 0.125rem; }
.persona .name { font-weight: 600; line-height: 1.2; }
.persona .role { line-height: 1.2; }
.persona .status { line-height: 1.2; opacity: 0.6; }
.persona .status.active {
    opacity: 1;
    color: var(--st-primary-color);
    font-weight: 600;
}
"""

_PERSONA_JS = r"""
export default function(component) {
    const { data, parentElement } = component;
    parentElement.querySelectorAll(".persona").forEach((el) => el.remove());

    const model = JSON.parse(data || "{}");
    const name = model.name || "";
    const avatarUrl = model.avatarUrl || "";
    const role = model.role || "";
    const status = model.status || "";
    const textAlign = model.textAlign || "right";
    const statusColor = model.statusColor || "inactive";
    const size = model.size || "small";
    const shape = model.imageShape || "circle";

    const avatarSize =
        size === "small" ? "3rem" : size === "medium" ? "6rem" : "9rem";
    const radius = shape === "circle"
        ? "50%"
        : "var(--st-base-radius, 0.5rem)";
    const sizes = {
        small: ["0.8125rem", "0.75rem"],
        medium: ["1.25rem", "0.875rem"],
        large: ["1.5rem", "1rem"],
    }[size];
    const nameSize = sizes[0];
    const roleSize = sizes[1];

    function initials(n) {
        if (!n) return "?";
        const parts = n.split(/\s+/).filter(Boolean);
        if (!parts.length) return "?";
        if (parts.length === 1) return parts[0][0].toUpperCase();
        return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }

    const root = document.createElement("div");
    root.className = "persona " + textAlign;

    // Avatar (image or initials fallback).
    let avatar;
    if (avatarUrl) {
        avatar = document.createElement("img");
        avatar.src = avatarUrl;
        avatar.alt = name;
    } else {
        avatar = document.createElement("div");
        avatar.textContent = initials(name);
    }
    avatar.className = "avatar";
    avatar.style.width = avatarSize;
    avatar.style.height = avatarSize;
    avatar.style.borderRadius = radius;
    root.appendChild(avatar);

    // Text lines.
    const lines = document.createElement("div");
    lines.className = "lines";
    lines.style.textAlign =
        textAlign === "bottom" ? "center" : textAlign === "left" ? "right" : "left";
    if (name) {
        const el = document.createElement("div");
        el.className = "name";
        el.style.fontSize = nameSize;
        el.textContent = name;
        lines.appendChild(el);
    }
    if (role) {
        const el = document.createElement("div");
        el.className = "role";
        el.style.fontSize = roleSize;
        el.textContent = role;
        lines.appendChild(el);
    }
    if (status) {
        const el = document.createElement("div");
        el.className = "status " + (statusColor === "active" ? "active" : "");
        el.style.fontSize = roleSize;
        el.textContent = status;
        lines.appendChild(el);
    }
    root.appendChild(lines);

    parentElement.appendChild(root);
    return () => { root.remove(); };
}
"""

_persona_component = st.components.v2.component(
    name="persona",
    css=_PERSONA_CSS,
    js=_PERSONA_JS,
)


def persona(
    name: Optional[str] = None,
    avatar_url: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    *,
    text_align: Literal["left", "right", "bottom"] = "right",
    status_color: Literal["active", "inactive"] = "inactive",
    size: Literal["small", "medium", "large"] = "small",
    image_shape: Literal["circle", "none"] = "circle",
    key: Optional[str] = None,
    width: Width = "stretch",
) -> None:
    """Render a persona (avatar + name/role/status).

    When no ``avatar_url`` is given, the initials derived from ``name`` are
    shown. Only the fields that are provided are rendered.

    Args:
        name: Name of the person.
        avatar_url: URL of the avatar image.
        role: Role or title.
        status: Short status text.
        text_align: ``"right"`` (default), ``"left"`` or ``"bottom"``.
        status_color: ``"active"`` (primary) or ``"inactive"`` (default).
        size: ``"small"`` (default), ``"medium"`` or ``"large"``.
        image_shape: ``"circle"`` (default) or ``"none"``.
        key: Optional Streamlit widget key.
        width: Width of the widget.
    """

    if not name and not avatar_url and not status and not role:
        raise ValueError(
            "At least one of 'name', 'avatar_url', 'status' or 'role' must be "
            "provided."
        )
    if text_align not in ("left", "right", "bottom"):
        raise ValueError(
            f"Invalid text_align {text_align!r}. Expected 'left', 'right' or "
            "'bottom'."
        )
    if status_color not in ("active", "inactive"):
        raise ValueError(
            f"Invalid status_color {status_color!r}. Expected 'active' or "
            "'inactive'."
        )
    if size not in ("small", "medium", "large"):
        raise ValueError(
            f"Invalid size {size!r}. Expected 'small', 'medium' or 'large'."
        )
    if image_shape not in ("circle", "none"):
        raise ValueError(
            f"Invalid image_shape {image_shape!r}. Expected 'circle' or " "'none'."
        )
    data = json.dumps(
        {
            "name": name,
            "avatarUrl": avatar_url,
            "role": role,
            "status": status,
            "textAlign": text_align,
            "statusColor": status_color,
            "size": size,
            "imageShape": image_shape,
        }
    )
    with st.container(width=width):
        _persona_component(data=data, key=key)


# ---------------------------------------------------------------------------
# Cart custom component (Custom Components v2)
# ---------------------------------------------------------------------------

_CART_CSS = """
.cart-widget {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2.5rem;
    height: 2.5rem;
    color: var(--st-text-color);
}
.cart-widget.small {
    width: 2rem;
    height: 2rem;
}
.cart-widget.medium {
    height: 2.5rem;
}
.cart-widget.large {
    width: 3rem;
    height: 3rem;
}
.cart-widget .material-symbols-rounded {
    font-family: 'Material Symbols Rounded';
    font-size: 1.75rem;
    font-weight: 400;
    line-height: 1;
    font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
}
.cart-widget.small .material-symbols-rounded { font-size: 1.4rem; }
.cart-widget.medium .material-symbols-rounded { font-size: 1.75rem; }
.cart-widget.large .material-symbols-rounded { font-size: 2.1rem; }
.cart-widget .cart-count {
    position: absolute;
    top: -0.1rem;
    right: -0.1rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 1.1rem;
    height: 1.1rem;
    padding: 0 0.2rem;
    border-radius: 999px;
    background: var(--st-primary-color);
    color: var(--st-primary-text-color, white);
    font-size: 0.7rem;
    font-weight: 600;
    line-height: 1;
}
.cart-widget.small .cart-count {
    min-width: 0.95rem;
    height: 0.95rem;
    font-size: 0.625rem;
}
.cart-widget.large .cart-count {
    min-width: 1.25rem;
    height: 1.25rem;
    font-size: 0.75rem;
}
.cart-widget.clickable { cursor: pointer; }
.cart-widget.clickable:hover .material-symbols-rounded {
    color: var(--st-primary-color);
}
"""

_CART_JS = r"""
export default function(component) {
    const { data, parentElement, setTriggerValue } = component;
    parentElement.querySelectorAll(".cart-widget, link.cart-font")
        .forEach((el) => el.remove());

    const model = JSON.parse(data || "{}");
    const root = document.createElement("div");
    root.className = "cart-widget " + (model.size || "medium") +
        (model.clickable ? " clickable" : "");
    root.title = "Shopping cart";

    const icon = document.createElement("span");
    icon.className = "material-symbols-rounded";
    icon.textContent = "shopping_cart";
    root.appendChild(icon);

    const count = document.createElement("span");
    count.className = "cart-count";
    count.textContent = String(model.count || 0);
    root.appendChild(count);

    const onClick = () => setTriggerValue("clicked", Date.now());
    if (model.clickable) root.addEventListener("click", onClick);

    const fontLink = document.createElement("link");
    fontLink.className = "cart-font";
    fontLink.rel = "stylesheet";
    fontLink.href =
        "https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded";
    parentElement.appendChild(fontLink);
    parentElement.appendChild(root);

    return () => {
        root.removeEventListener("click", onClick);
        root.remove();
        fontLink.remove();
    };
}
"""

_cart_component = st.components.v2.component(
    name="cart",
    css=_CART_CSS,
    js=_CART_JS,
)


def cart(
    size: Literal["small", "medium", "large"] = "medium",
    count: int = 0,
    *,
    on_click: Optional[Callable[[], None]] = None,
    key: Optional[str] = None,
    width: Width = "content",
) -> None:
    """Render a shopping-cart icon with an item-count badge.

    ``on_click``, if provided, is called once per click on the icon; while
    set, the icon also shows a pointer cursor and switches to the theme's
    primary color on hover.
    """

    if size not in ("small", "medium", "large"):
        raise ValueError("'size' must be 'small', 'medium' or 'large'.")
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError("'count' must be a non-negative integer.")
    data = json.dumps({"size": size, "count": count, "clickable": on_click is not None})
    event_key, callback = _wire_icon_click("cart", key, on_click)
    with st.container(width=width):
        _cart_component(data=data, key=event_key, on_clicked_change=callback)


# ---------------------------------------------------------------------------
# Box custom component (Custom Components v2)
# ---------------------------------------------------------------------------

_BOX_CSS = _CART_CSS.replace(".cart-widget", ".box-widget")
_BOX_CSS = _BOX_CSS.replace(".cart-count", ".box-count")

_BOX_JS = r"""
export default function(component) {
    const { data, parentElement, setTriggerValue } = component;
    parentElement.querySelectorAll(".box-widget, link.box-font")
        .forEach((el) => el.remove());

    const model = JSON.parse(data || "{}");
    const root = document.createElement("div");
    root.className = "box-widget " + (model.size || "medium") +
        (model.clickable ? " clickable" : "");
    root.title = "Box";

    const icon = document.createElement("span");
    icon.className = "material-symbols-rounded";
    icon.textContent = "inventory_2";
    root.appendChild(icon);

    const count = document.createElement("span");
    count.className = "box-count";
    count.textContent = String(model.count || 0);
    root.appendChild(count);

    const onClick = () => setTriggerValue("clicked", Date.now());
    if (model.clickable) root.addEventListener("click", onClick);

    const fontLink = document.createElement("link");
    fontLink.className = "box-font";
    fontLink.rel = "stylesheet";
    fontLink.href =
        "https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded";
    parentElement.appendChild(fontLink);
    parentElement.appendChild(root);

    return () => {
        root.removeEventListener("click", onClick);
        root.remove();
        fontLink.remove();
    };
}
"""

_box_component = st.components.v2.component(
    name="box",
    css=_BOX_CSS,
    js=_BOX_JS,
)


def box(
    size: Literal["small", "medium", "large"] = "medium",
    count: int = 0,
    *,
    on_click: Optional[Callable[[], None]] = None,
    key: Optional[str] = None,
    width: Width = "content",
) -> None:
    """Render a box icon with a count badge.

    ``on_click``, if provided, is called once per click on the icon; while
    set, the icon also shows a pointer cursor and switches to the theme's
    primary color on hover.
    """

    if size not in ("small", "medium", "large"):
        raise ValueError("'size' must be 'small', 'medium' or 'large'.")
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError("'count' must be a non-negative integer.")
    data = json.dumps({"size": size, "count": count, "clickable": on_click is not None})
    event_key, callback = _wire_icon_click("box", key, on_click)
    with st.container(width=width):
        _box_component(data=data, key=event_key, on_clicked_change=callback)


# ---------------------------------------------------------------------------
# Email custom component (Custom Components v2)
# ---------------------------------------------------------------------------

_EMAIL_CSS = _CART_CSS.replace(".cart-widget", ".email-widget")
_EMAIL_CSS = _EMAIL_CSS.replace(".cart-count", ".email-count")

_EMAIL_JS = r"""
export default function(component) {
    const { data, parentElement, setTriggerValue } = component;
    parentElement.querySelectorAll(".email-widget, link.email-font")
        .forEach((el) => el.remove());

    const model = JSON.parse(data || "{}");
    const root = document.createElement("div");
    root.className = "email-widget " + (model.size || "medium") +
        (model.clickable ? " clickable" : "");
    root.title = "Email";

    const icon = document.createElement("span");
    icon.className = "material-symbols-rounded";
    icon.textContent = "mail";
    root.appendChild(icon);

    const count = document.createElement("span");
    count.className = "email-count";
    count.textContent = String(model.count || 0);
    root.appendChild(count);

    const onClick = () => setTriggerValue("clicked", Date.now());
    if (model.clickable) root.addEventListener("click", onClick);

    const fontLink = document.createElement("link");
    fontLink.className = "email-font";
    fontLink.rel = "stylesheet";
    fontLink.href =
        "https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded";
    parentElement.appendChild(fontLink);
    parentElement.appendChild(root);

    return () => {
        root.removeEventListener("click", onClick);
        root.remove();
        fontLink.remove();
    };
}
"""

_email_component = st.components.v2.component(
    name="email",
    css=_EMAIL_CSS,
    js=_EMAIL_JS,
)


def email(
    size: Literal["small", "medium", "large"] = "medium",
    count: int = 0,
    *,
    on_click: Optional[Callable[[], None]] = None,
    key: Optional[str] = None,
    width: Width = "content",
) -> None:
    """Render an email icon with an unread-count badge.

    ``on_click``, if provided, is called once per click on the icon; while
    set, the icon also shows a pointer cursor and switches to the theme's
    primary color on hover.
    """

    if size not in ("small", "medium", "large"):
        raise ValueError("'size' must be 'small', 'medium' or 'large'.")
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError("'count' must be a non-negative integer.")
    data = json.dumps({"size": size, "count": count, "clickable": on_click is not None})
    event_key, callback = _wire_icon_click("email", key, on_click)
    with st.container(width=width):
        _email_component(data=data, key=event_key, on_clicked_change=callback)


# ---------------------------------------------------------------------------
# Chat message custom component (Custom Components v2)
# ---------------------------------------------------------------------------

_CHAT_MESSAGE_CSS = _CART_CSS.replace(".cart-widget", ".chat-message-widget")
_CHAT_MESSAGE_CSS = _CHAT_MESSAGE_CSS.replace(".cart-count", ".chat-message-count")

_CHAT_MESSAGE_JS = r"""
export default function(component) {
    const { data, parentElement, setTriggerValue } = component;
    parentElement.querySelectorAll(
        ".chat-message-widget, link.chat-message-font"
    ).forEach((el) => el.remove());

    const model = JSON.parse(data || "{}");
    const root = document.createElement("div");
    root.className = "chat-message-widget " + (model.size || "medium") +
        (model.clickable ? " clickable" : "");
    root.title = "Chat messages";

    const icon = document.createElement("span");
    icon.className = "material-symbols-rounded";
    icon.textContent = "chat";
    root.appendChild(icon);

    const count = document.createElement("span");
    count.className = "chat-message-count";
    count.textContent = String(model.count || 0);
    root.appendChild(count);

    const onClick = () => setTriggerValue("clicked", Date.now());
    if (model.clickable) root.addEventListener("click", onClick);

    const fontLink = document.createElement("link");
    fontLink.className = "chat-message-font";
    fontLink.rel = "stylesheet";
    fontLink.href =
        "https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded";
    parentElement.appendChild(fontLink);
    parentElement.appendChild(root);

    return () => {
        root.removeEventListener("click", onClick);
        root.remove();
        fontLink.remove();
    };
}
"""

_chat_message_component = st.components.v2.component(
    name="chat_message",
    css=_CHAT_MESSAGE_CSS,
    js=_CHAT_MESSAGE_JS,
)


def chat_message(
    size: Literal["small", "medium", "large"] = "medium",
    count: int = 0,
    *,
    on_click: Optional[Callable[[], None]] = None,
    key: Optional[str] = None,
    width: Width = "content",
) -> None:
    """Render a chat-message icon with an unread-count badge.

    ``on_click``, if provided, is called once per click on the icon; while
    set, the icon also shows a pointer cursor and switches to the theme's
    primary color on hover.
    """

    if size not in ("small", "medium", "large"):
        raise ValueError("'size' must be 'small', 'medium' or 'large'.")
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError("'count' must be a non-negative integer.")
    data = json.dumps({"size": size, "count": count, "clickable": on_click is not None})
    event_key, callback = _wire_icon_click("chat_message", key, on_click)
    with st.container(width=width):
        _chat_message_component(data=data, key=event_key, on_clicked_change=callback)


# ---------------------------------------------------------------------------
# Clickable custom component (Custom Components v2)
# ---------------------------------------------------------------------------

_CLICKABLE_JS = r"""
export default function(component) {
    const { data, parentElement, setTriggerValue } = component;
    const model = JSON.parse(data || "{}");
    const containerClass = "st-key-" + (model.key || "clickable");
    const container = parentElement.ownerDocument.querySelector(
        "." + CSS.escape(containerClass)
    );
    const interactiveSelector = [
        "a",
        "button",
        "input",
        "textarea",
        "select",
        "option",
        "[contenteditable='true']",
        "[role='button']",
        "[role='checkbox']",
        "[role='radio']",
        "[data-testid='stComponentV2']",
    ].join(", ");
    const onContainerClick = (event) => {
        if (event.target.closest(interactiveSelector)) return;
        setTriggerValue("clicked", Date.now());
    };

    if (container) {
        container.addEventListener("click", onContainerClick);
        container.style.cursor = "pointer";
    }

    return () => {
        if (container) {
            container.removeEventListener("click", onContainerClick);
            container.style.cursor = "";
        }
    };
}
"""

_clickable_component = st.components.v2.component(
    name="clickable",
    js=_CLICKABLE_JS,
)


class _ClickableContext:
    def __init__(
        self,
        on_click: Optional[Callable[[], None]],
        key: Optional[str],
    ):
        self._key = key
        self._on_click = on_click
        self._last_click_state_key = f"{self._key}_last_click"
        self._container = None

    def _on_clicked(self):
        component_state = st.session_state.get(f"{self._key}_event", {})
        click_value = component_state.get("clicked")
        if click_value is not None and click_value != st.session_state.get(
            self._last_click_state_key
        ):
            st.session_state[self._last_click_state_key] = click_value
            if self._on_click is not None:
                self._on_click()

    def __enter__(self):
        self._container = st.container(key=self._key)
        self._container.__enter__()
        _clickable_component(
            data=json.dumps({"key": self._key}),
            key=f"{self._key}_event",
            on_clicked_change=self._on_clicked,
        )
        return self._container

    def __exit__(self, exc_type, exc_value, traceback):
        return self._container.__exit__(exc_type, exc_value, traceback)


def clickable(
    *,
    on_click: Optional[Callable[[], None]] = None,
    key: Optional[str] = None,
) -> _ClickableContext:
    """Render a clickable container for Streamlit content.

    ``on_click`` is called once for each click on the container background.
    Child controls and nested custom components retain their own click events.
    """

    return _ClickableContext(on_click, key or _default_key("clickable"))


# ---------------------------------------------------------------------------
# Tile custom component (Custom Components v2)
# ---------------------------------------------------------------------------

_TILE_CSS = """
.tile-header {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 0.25rem 0.75rem;
    align-items: start;
    padding: 0.75rem 0.875rem 0.5rem;
    color: var(--st-text-color);
}
.tile-heading { min-width: 0; }
.tile-title {
    overflow: hidden;
    font-weight: 600;
    line-height: 1.25;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.tile-caption {
    overflow: hidden;
    margin-top: 0.2rem;
    color: var(--st-text-color);
    opacity: 0.7;
    font-size: 0.8125rem;
    line-height: 1.3;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.tile-icon {
    color: var(--st-primary-color);
    font-family: 'Material Symbols Rounded';
    font-size: 1.5rem;
    line-height: 1;
}
"""

_TILE_JS = r"""
export default function(component) {
    const { data, parentElement, setTriggerValue } = component;
    parentElement.querySelectorAll(".tile-header, link.tile-font")
        .forEach((el) => el.remove());

    const model = JSON.parse(data || "{}");
    const header = document.createElement("div");
    header.className = "tile-header";

    const heading = document.createElement("div");
    heading.className = "tile-heading";
    const title = document.createElement("div");
    title.className = "tile-title";
    title.textContent = model.title || "";
    heading.appendChild(title);
    if (model.caption) {
        const caption = document.createElement("div");
        caption.className = "tile-caption";
        caption.textContent = model.caption;
        heading.appendChild(caption);
    }
    header.appendChild(heading);

    const icon = document.createElement("span");
    icon.className = "tile-icon";
    const materialIcon = /^:material\/([a-z0-9_]+):$/.exec(model.icon || "");
    if (materialIcon) {
        icon.textContent = materialIcon[1];
    } else {
        icon.textContent = model.icon || "";
    }
    header.appendChild(icon);

    const fontLink = document.createElement("link");
    fontLink.className = "tile-font";
    fontLink.rel = "stylesheet";
    fontLink.href =
        "https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded";
    parentElement.appendChild(fontLink);
    parentElement.appendChild(header);

    const tileKey = model.key || "tile";
    const tileClass = "st-key-" + tileKey;
    const tileContainer = parentElement.ownerDocument.querySelector(
        "." + CSS.escape(tileClass)
    );
    const onTileClick = (event) => {
        event.preventDefault();
        event.stopPropagation();
        setTriggerValue("clicked", Date.now());
    };
    if (tileContainer) {
        const originalBorderColor = tileContainer.style.borderColor;
        const primaryColor = getComputedStyle(parentElement.host ?? parentElement)
            .getPropertyValue("--st-primary-color")
            .trim();
        const onTileEnter = () => {
            tileContainer.style.borderColor = primaryColor;
        };
        const onTileLeave = () => {
            tileContainer.style.borderColor = originalBorderColor;
        };
        tileContainer.addEventListener("click", onTileClick, true);
        tileContainer.addEventListener("mouseenter", onTileEnter);
        tileContainer.addEventListener("mouseleave", onTileLeave);
        tileContainer.style.cursor = "pointer";

        return () => {
            tileContainer.removeEventListener("click", onTileClick, true);
            tileContainer.removeEventListener("mouseenter", onTileEnter);
            tileContainer.removeEventListener("mouseleave", onTileLeave);
            tileContainer.style.borderColor = originalBorderColor;
            tileContainer.style.cursor = "";
            header.remove();
            fontLink.remove();
        };
    }

    return () => {
        header.remove();
        fontLink.remove();
    };
}
"""

_tile_component = st.components.v2.component(
    name="tile",
    css=_TILE_CSS,
    js=_TILE_JS,
)


class _TileContext:
    def __init__(
        self,
        title: str,
        caption: str,
        icon: str,
        width: Width,
        height: Optional[Height],
        border: bool,
        bg_color: Optional[str],
        scrollable: bool,
        on_click: Optional[Callable[[], None]],
        key: Optional[str],
    ):
        self._data = json.dumps(
            {"title": title, "caption": caption, "icon": icon, "key": key or "tile"}
        )
        self._width = width
        self._height = height
        self._border = border
        self._bg_color = bg_color
        self._scrollable = scrollable
        self._on_click = on_click
        self._key = key
        self._last_click_state_key = f"{key}_last_click"
        self._container = None

    def _on_clicked(self):
        component_state = st.session_state.get(f"{self._key}_event", {})
        click_value = component_state.get("clicked")
        if click_value is not None and click_value != st.session_state.get(
            self._last_click_state_key
        ):
            st.session_state[self._last_click_state_key] = click_value
            if self._on_click is not None:
                self._on_click()

    def __enter__(self):
        tile_styles = []
        if self._bg_color is not None:
            tile_styles.append(
                f".st-key-{self._key} {{ background: {self._bg_color}; }}"
            )
        if not self._scrollable:
            tile_styles.append(
                f'.st-key-{self._key}[data-testid="stVerticalBlock"], '
                f'.st-key-{self._key} [data-testid="stVerticalBlock"] '
                "{ overflow-y: hidden !important; }"
            )
        if tile_styles:
            st.markdown(
                f"<style>{''.join(tile_styles)}</style>",
                unsafe_allow_html=True,
            )
        container_args = {
            "width": cast(Width, self._width),
            "border": self._border,
            "key": self._key,
        }
        if self._height is not None:
            container_args["height"] = cast(Height, self._height)
        self._container = st.container(**container_args)
        self._container.__enter__()
        _tile_component(
            data=self._data,
            key=f"{self._key}_event",
            on_clicked_change=self._on_clicked,
        )
        return self._container

    def __exit__(self, exc_type, exc_value, traceback):
        return self._container.__exit__(exc_type, exc_value, traceback)


def tile(
    title: str,
    caption: str = "",
    icon: str = "",
    *,
    width: Width = "stretch",
    height: Optional[Height] = None,
    border: bool = False,
    shape: Literal["square", "flexible"] = "flexible",
    bg_color: Optional[str] = None,
    scrollable: bool = True,
    on_click: Optional[Callable[[], None]] = None,
    key: Optional[str] = None,
) -> _TileContext:
    """Render a clickable tile and return a context for Streamlit content.

    ``border`` is passed directly to the underlying Streamlit container.
    ``shape="square"`` uses the numeric width as the height and ignores
    ``height``; ``shape="flexible"`` uses the supplied height.
    ``bg_color`` accepts hex or ``rgb(...)``/``rgba(...)`` colors.
    Set ``scrollable=False`` to hide vertical overflow in a fixed-height tile.
    ``on_click`` is called once for each tile click.
    """

    if not isinstance(border, bool):
        raise ValueError("'border' must be a boolean.")
    if not isinstance(scrollable, bool):
        raise ValueError("'scrollable' must be a boolean.")
    if bg_color is not None and not re.fullmatch(
        r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})"
        r"|rgba?\(\s*(?:\d{1,3}%?\s*,\s*){2}"
        r"\d{1,3}%?(?:\s*,\s*(?:0|1|0?\.\d+))?\s*\)",
        bg_color,
    ):
        raise ValueError("'bg_color' must be a hex or rgb/rgba color.")
    if shape not in ("square", "flexible"):
        raise ValueError("'shape' must be 'square' or 'flexible'.")
    if shape == "square":
        if not isinstance(width, int) or isinstance(width, bool):
            raise ValueError("'width' must be an integer when shape='square'.")
        height = width
    tile_key = key or _default_key("tile")
    return _TileContext(
        title,
        caption,
        icon,
        width,
        height,
        border,
        bg_color,
        scrollable,
        on_click,
        tile_key,
    )


# ---------------------------------------------------------------------------
# Calendar custom component (Custom Components v2)
# ---------------------------------------------------------------------------
#
# A month calendar for picking a single day or a date range, shown as one
# month or two consecutive months side by side.
#
# Data contract (passed as a JSON string via the ``data`` mount parameter):
#   {
#     "month": int,            # 1-12, the anchor month shown first
#     "year": int,
#     "selection": "single" | "range",
#     "selected": [int, ...],  # date.toordinal() values, 0-2 entries
#     "layout": "single" | "double",
#     "today": int             # date.today().toordinal()
#   }

_CALENDAR_CSS = """
.cal {
    display: inline-block;
    font-family: var(--st-font);
    color: var(--st-text-color);
}
.cal.with-border {
    border: 1px solid var(--st-border-color);
    border-radius: var(--st-base-radius, 0.5rem);
    padding: 0.75rem;
}
.cal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
}
.cal-nav {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.75rem;
    height: 1.75rem;
    border-radius: var(--st-base-radius, 0.5rem);
    cursor: pointer;
    color: var(--st-text-color);
    opacity: 0.7;
}
.cal-nav:hover { opacity: 1; background: var(--st-secondary-background-color); }
.cal-nav .material-symbols-rounded {
    font-family: 'Material Symbols Rounded';
    font-size: 1.125rem;
}
.cal-title {
    font-weight: 600;
    font-size: 0.875rem;
    text-align: center;
    flex: 1 1 auto;
}
.cal-months {
    display: flex;
    gap: 1.5rem;
}
.cal-month table {
    border-collapse: collapse;
}
.cal-month caption {
    font-weight: 600;
    font-size: 0.8125rem;
    padding-bottom: 0.375rem;
    text-align: center;
}
.cal-month th {
    font-weight: 400;
    font-size: 0.75rem;
    opacity: 0.6;
    padding: 0.25rem 0.4rem;
}
.cal-month td {
    padding: 0.1rem;
    text-align: center;
}
.cal-day {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2rem;
    height: 2rem;
    border-radius: 999px;
    font-size: 0.8125rem;
    cursor: pointer;
}
.cal-day:hover { background: var(--st-secondary-background-color); }
.cal-day.outside { opacity: 0.35; cursor: default; }
.cal-day.outside:hover { background: none; }
.cal-day.today { font-weight: 700; color: var(--st-primary-color); }
.cal-day.selected {
    background: var(--st-primary-color);
    color: var(--st-background-color);
    font-weight: 600;
}
.cal-day.in-range {
    background: color-mix(in srgb, var(--st-primary-color) 20%, transparent);
    border-radius: 0;
}
.cal-day.range-start { border-radius: 999px 0 0 999px; }
.cal-day.range-end { border-radius: 0 999px 999px 0; }
.cal-day.range-start.range-end { border-radius: 999px; }
"""

_CALENDAR_JS = r"""
export default function(component) {
    const { data, parentElement, setTriggerValue } = component;
    parentElement.querySelectorAll(".cal, link.cal-font").forEach((el) => el.remove());

    const model = JSON.parse(data || "{}");
    const selectionMode = model.selection === "range" ? "range" : "single";
    const layout = model.layout === "double" ? "double" : "single";
    const today = model.today;

    // The anchor month/year shown is kept local to the component so
    // navigating with the prev/next arrows doesn't require a Python rerun.
    // It's stored on the host element so it survives a re-mount (e.g. a
    // light/dark theme switch, which does not rerun Python).
    const stateEl = parentElement.host || parentElement;
    const savedView = stateEl.dataset ? stateEl.dataset.calView : undefined;
    let anchorMonth;
    let anchorYear;
    if (savedView !== undefined) {
        const [m, y] = savedView.split("-").map(Number);
        anchorMonth = m;
        anchorYear = y;
    } else {
        anchorMonth = model.month;
        anchorYear = model.year;
    }

    let selected = Array.isArray(model.selected) ? model.selected.slice() : [];

    function saveView() {
        if (stateEl.dataset) {
            stateEl.dataset.calView = anchorMonth + "-" + anchorYear;
        }
    }
    saveView();

    // date.toordinal() counts from 0001-01-01 = day 1; that date is
    // 719163 days before the JS/Unix epoch (1970-01-01).
    function dateToOrdinal(utcDate) {
        return Math.round(
            (Date.UTC(
                utcDate.getUTCFullYear(), utcDate.getUTCMonth(), utcDate.getUTCDate()
            ) - Date.UTC(1970, 0, 1)) / 86400000
        ) + 719163;
    }

    function emit() {
        const val = JSON.stringify(selected);
        if (stateEl.dataset) stateEl.dataset.calSelected = val;
        setTriggerValue("selected", val);
    }

    function onDayClick(ordinal) {
        if (selectionMode === "single") {
            selected = [ordinal];
        } else if (selected.length !== 1) {
            selected = [ordinal];
        } else {
            const start = selected[0];
            selected = start <= ordinal ? [start, ordinal] : [ordinal, start];
        }
        emit();
        render();
    }

    const root = document.createElement("div");
    root.className = "cal" + (model.border !== false ? " with-border" : "");

    const header = document.createElement("div");
    header.className = "cal-header";

    const prevBtn = document.createElement("span");
    prevBtn.className = "cal-nav";
    prevBtn.innerHTML =
        '<span class="material-symbols-rounded">chevron_left</span>';
    prevBtn.onclick = () => {
        anchorMonth -= 1;
        if (anchorMonth < 1) { anchorMonth = 12; anchorYear -= 1; }
        saveView();
        render();
    };

    const nextBtn = document.createElement("span");
    nextBtn.className = "cal-nav";
    nextBtn.innerHTML =
        '<span class="material-symbols-rounded">chevron_right</span>';
    nextBtn.onclick = () => {
        anchorMonth += 1;
        if (anchorMonth > 12) { anchorMonth = 1; anchorYear += 1; }
        saveView();
        render();
    };

    const title = document.createElement("div");
    title.className = "cal-title";

    header.appendChild(prevBtn);
    header.appendChild(title);
    header.appendChild(nextBtn);
    root.appendChild(header);

    const monthsWrap = document.createElement("div");
    monthsWrap.className = "cal-months";
    root.appendChild(monthsWrap);

    const monthNames = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ];
    const weekdayNames = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];

    function buildMonth(month, year) {
        const wrap = document.createElement("div");
        wrap.className = "cal-month";
        const table = document.createElement("table");
        const caption = document.createElement("caption");
        caption.textContent = monthNames[month - 1] + " " + year;
        table.appendChild(caption);

        const thead = document.createElement("thead");
        const headRow = document.createElement("tr");
        weekdayNames.forEach((name) => {
            const th = document.createElement("th");
            th.textContent = name;
            headRow.appendChild(th);
        });
        thead.appendChild(headRow);
        table.appendChild(thead);

        const tbody = document.createElement("tbody");
        const firstOfMonth = new Date(Date.UTC(year, month - 1, 1));
        // Monday-first weekday index (0 = Monday ... 6 = Sunday).
        const firstWeekday = (firstOfMonth.getUTCDay() + 6) % 7;
        const daysInMonth = new Date(Date.UTC(year, month, 0)).getUTCDate();

        const cells = [];
        for (let i = 0; i < firstWeekday; i++) cells.push(null);
        for (let d = 1; d <= daysInMonth; d++) cells.push(d);
        while (cells.length % 7 !== 0) cells.push(null);

        for (let row = 0; row < cells.length / 7; row++) {
            const tr = document.createElement("tr");
            for (let col = 0; col < 7; col++) {
                const day = cells[row * 7 + col];
                const td = document.createElement("td");
                const span = document.createElement("span");
                span.className = "cal-day";
                if (day === null) {
                    span.classList.add("outside");
                } else {
                    const ordinal = dateToOrdinal(
                        new Date(Date.UTC(year, month - 1, day))
                    );
                    span.textContent = String(day);
                    if (ordinal === today) span.classList.add("today");
                    if (selectionMode === "range" && selected.length === 2) {
                        const [start, end] = selected;
                        if (ordinal > start && ordinal < end) {
                            span.classList.add("in-range");
                        }
                        if (ordinal === start) {
                            span.classList.add("selected", "range-start");
                        }
                        if (ordinal === end) {
                            span.classList.add("selected", "range-end");
                        }
                    } else if (selected.includes(ordinal)) {
                        span.classList.add("selected");
                    }
                    span.onclick = () => onDayClick(ordinal);
                }
                td.appendChild(span);
                tr.appendChild(td);
            }
            tbody.appendChild(tr);
        }
        table.appendChild(tbody);
        wrap.appendChild(table);
        return wrap;
    }

    function render() {
        if (layout === "double") {
            let nextMonth = anchorMonth + 1;
            let nextYear = anchorYear;
            if (nextMonth > 12) { nextMonth = 1; nextYear += 1; }
            title.textContent = monthNames[anchorMonth - 1] + " " + anchorYear +
                " \u2013 " + monthNames[nextMonth - 1] + " " + nextYear;
            monthsWrap.textContent = "";
            monthsWrap.appendChild(buildMonth(anchorMonth, anchorYear));
            monthsWrap.appendChild(buildMonth(nextMonth, nextYear));
        } else {
            title.textContent = monthNames[anchorMonth - 1] + " " + anchorYear;
            monthsWrap.textContent = "";
            monthsWrap.appendChild(buildMonth(anchorMonth, anchorYear));
        }
    }
    render();

    const fontLink = document.createElement("link");
    fontLink.className = "cal-font";
    fontLink.rel = "stylesheet";
    fontLink.href =
        "https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded";
    parentElement.appendChild(fontLink);
    parentElement.appendChild(root);

    return () => {
        root.remove();
        fontLink.remove();
    };
}
"""

_calendar_component = st.components.v2.component(
    name="calendar",
    css=_CALENDAR_CSS,
    js=_CALENDAR_JS,
)


def calender(
    month: Optional[int] = None,
    year: Optional[int] = None,
    *,
    selection: Literal["single", "range"] = "single",
    selected: Optional[List[int]] = None,
    layout: Literal["single", "double"] = "single",
    border: bool = True,
    on_select: Optional[Callable[[List[int]], None]] = None,
    key: Optional[str] = None,
    width: Width = "content",
) -> List[int]:
    """Render a month calendar for picking a day or a date range.

    Args:
        month: Month (1-12) initially shown. Defaults to the current month.
        year: Year initially shown. Defaults to the current year.
        selection: ``"single"`` (default) picks one day; ``"range"`` picks a
            start and end day: click a day to start a range, then another to
            complete it; clicking again starts a new range.
        selected: Initially selected day(s), as ``date.toordinal()`` values.
            At most one entry for ``"single"``; zero, one (range start only)
            or two (start, end) entries for ``"range"``.
        layout: ``"single"`` (default) shows one month; ``"double"`` shows the
            given month and the next one side by side. Navigating with the
            prev/next arrows shifts both.
        border: Whether to draw a border around the widget. Defaults to
            ``True``.
        on_select: Optional callback invoked with the current selection
            (``date.toordinal()`` values) whenever it changes.
        key: Optional Streamlit widget key.
        width: Width of the widget. ``"content"`` (default), ``"stretch"``, or
            a fixed pixel width.

    Returns:
        The selected day(s) as ``date.toordinal()`` values.
    """
    if selection not in ("single", "range"):
        raise ValueError(
            f"Invalid selection {selection!r}. Expected 'single' or 'range'."
        )
    if layout not in ("single", "double"):
        raise ValueError(f"Invalid layout {layout!r}. Expected 'single' or 'double'.")
    if not isinstance(border, bool):
        raise ValueError("'border' must be a boolean.")
    today = date.today()
    month = month if month is not None else today.month
    year = year if year is not None else today.year
    if not 1 <= month <= 12:
        raise ValueError("'month' must be between 1 and 12.")
    selected = list(selected) if selected is not None else []
    max_selected = 1 if selection == "single" else 2
    if len(selected) > max_selected:
        raise ValueError(
            f"'selected' must have at most {max_selected} entr"
            f"{'y' if max_selected == 1 else 'ies'} when selection={selection!r}."
        )

    data = json.dumps(
        {
            "month": month,
            "year": year,
            "selection": selection,
            "selected": selected,
            "layout": layout,
            "border": border,
            "today": today.toordinal(),
        }
    )
    with st.container(width=width):
        result = _calendar_component(
            data=data,
            on_selected_change=lambda: None,
            key=key,
        )
    current = json.loads(result.selected) if result.selected is not None else selected
    if on_select is not None:
        on_select(current)
    return current
