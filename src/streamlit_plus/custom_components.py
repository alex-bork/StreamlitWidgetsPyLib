import json
from typing import Any, Callable, Dict, List, Literal, Optional, Union

import streamlit as st

Width = Union[int, Literal["stretch", "content"]]


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
    background: var(--st-primary-color);
    color: var(--st-background-color);
}
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
    gap: 2px;
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
    padding: 0.5rem;
    min-width: 12rem;
    background: var(--st-background-color);
    border: 1px solid var(--st-border-color);
    border-radius: var(--st-base-radius, 0.5rem);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}
.stbl .filter-pop .stbl-filter { margin-bottom: 0.4rem; }
.stbl .filter-clear {
    margin-top: 0.5rem;
    width: 100%;
    padding: 0.3rem 0.5rem;
    font: inherit;
    color: var(--st-text-color);
    background: var(--st-secondary-background-color);
    border: 1px solid var(--st-border-color);
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
    border-color: var(--st-primary-color);
    color: var(--st-primary-color);
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
.stbl tbody tr { cursor: pointer; }
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
}
/* Outline the whole row of the selected cell with the primary color. */
.stbl tr.row-selected td {
    border-top: 1px solid var(--st-primary-color);
    border-bottom: 1px solid var(--st-primary-color);
}
.stbl tr.row-selected td:first-child {
    border-left: 1px solid var(--st-primary-color);
}
.stbl tr.row-selected td:last-child {
    border-right: 1px solid var(--st-primary-color);
}
/* Outline the whole column (header included) with the primary color. */
.stbl th.col-selected, .stbl td.col-selected {
    border-left: 1px solid var(--st-primary-color);
    border-right: 1px solid var(--st-primary-color);
}
.stbl thead th.col-selected {
    border-top: 1px solid var(--st-primary-color);
}
.stbl tbody tr:last-child td.col-selected {
    border-bottom: 1px solid var(--st-primary-color);
}
.stbl input[type="checkbox"], .stbl input[type="radio"] {
    cursor: pointer;
    accent-color: var(--st-primary-color);
}
.stbl-toolbar {
    display: flex;
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
.stbl-toolbar .toolbar-btn:hover {
    color: var(--st-primary-color);
    opacity: 1;
}
.stbl-toolbar .toolbar-btn .material-symbols-rounded {
    font-family: 'Material Symbols Rounded';
    font-size: 1.125rem;
    font-weight: 300;
    font-variation-settings: 'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 24;
}
.stbl-pager {
    display: flex;
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
.stbl-pager .pager-btn:disabled { opacity: 0.3; cursor: default; }
.stbl-pager .pager-btn svg { display: block; }
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
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    white-space: normal;
    pointer-events: none;
}
.stbl-filter {
    width: 100%;
    box-sizing: border-box;
    margin-bottom: 0.5rem;
    padding: 0.35rem 0.5rem;
    font: inherit;
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
        : (model.selected || []);
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
    let currentPage = 0;
    // toolbar: false | true (standard) | "custom" | "both".
    const toolbarMode = model.toolbar;
    const showToolbar = toolbarMode !== false && toolbarMode !== undefined;
    const showStandard = toolbarMode === true || toolbarMode === "both";
    const showCustom = toolbarMode === "custom" || toolbarMode === "both";
    const toolbarAlign = model.toolbarAlign === "left"
        ? "flex-start"
        : model.toolbarAlign === "center"
            ? "center"
            : "flex-end";
    // Custom toolbar icons (Material name / ":material/x:" / emoji).
    const customIcons = Array.isArray(model.customToolbar)
        ? model.customToolbar
        : [];
    // Preselected cell as [rowIndex, colIndex] or null (restored from a
    // previous mount when present).
    const savedCell =
        modeMatches && stateEl.dataset
            ? stateEl.dataset.stblSelectedCell
            : undefined;
    let selectedCell = savedCell !== undefined
        ? JSON.parse(savedCell)
        : (Array.isArray(model.selectedCell) ? model.selectedCell : null);

    // Per-column filter state: { value: string, exclude: bool }.
    const colFilters = columns.map(() => ({ value: "", exclude: false }));
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
            tbody.querySelectorAll(".selected, .row-selected, .col-selected")
                .forEach((el) => {
                    el.classList.remove(
                        "selected", "row-selected", "col-selected"
                    );
                });
            tbody.querySelectorAll("input[type='checkbox'], input[type='radio']")
                .forEach((el) => { el.checked = false; });
        }
        if (thead) {
            thead.querySelectorAll(".col-selected")
                .forEach((el) => el.classList.remove("col-selected"));
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
            const exportBtn = document.createElement("button");
            exportBtn.type = "button";
            exportBtn.className = "toolbar-btn";
            exportBtn.title = "Export as CSV";
            const exportIcon = document.createElement("span");
            exportIcon.className = "material-symbols-rounded";
            exportIcon.textContent = "download";
            exportBtn.appendChild(exportIcon);
            exportBtn.onclick = () => exportCsv();
            bar.appendChild(exportBtn);
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
    const bandedRows = model.bandedRows === true;

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
        if (cellMode && selectedCell && selectedCell[1] === colIndex) {
            th.classList.add("col-selected");
        }
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

            const apply = () => {
                colFilters[colIndex] = {
                    value: valInput.value.trim().toLowerCase(),
                    exclude: exCb.checked,
                };
                icon.classList.toggle("active", colFilters[colIndex].value !== "");
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
                    // Position the fixed popover just under the icon, kept
                    // within the viewport horizontally.
                    const r = icon.getBoundingClientRect();
                    const popWidth = pop.offsetWidth || 192;
                    let left = r.right - popWidth;
                    if (left < 8) left = 8;
                    const maxLeft = window.innerWidth - popWidth - 8;
                    if (left > maxLeft) left = maxLeft;
                    pop.style.left = left + "px";
                    pop.style.top = r.bottom + 4 + "px";
                    // Focus the value input for immediate typing.
                    valInput.focus();
                }
            };
            // Prevent clicks inside the popover from closing it.
            pop.onclick = (e) => e.stopPropagation();

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
                    tr.classList.add("row-selected");
                }
                if (selectedCell && selectedCell[1] === i) {
                    td.classList.add("col-selected");
                }
                td.onclick = () => {
                    tbody
                        .querySelectorAll("td.cell-selectable.selected")
                        .forEach((el) => el.classList.remove("selected"));
                    tbody
                        .querySelectorAll("tr.row-selected")
                        .forEach((el) => el.classList.remove("row-selected"));
                    table
                        .querySelectorAll(".col-selected")
                        .forEach((el) => el.classList.remove("col-selected"));
                    td.classList.add("selected");
                    tr.classList.add("row-selected");
                    table
                        .querySelectorAll('[data-col="' + i + '"]')
                        .forEach((el) => el.classList.add("col-selected"));
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
            }
            tbody.appendChild(tr);
            fillerRows.push(tr);
        }
    }

    // Pagination controls (only rendered when pageSize > 0).
    const pager = document.createElement("div");
    pager.className = "stbl-pager";
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
        pager.textContent = "";
        if (pageSize <= 0 || totalPages <= 1) return;

        // Inline SVG chevron (points left or right), aligns cleanly with the
        // page numbers unlike the text glyphs.
        const chevron = (dir) =>
            '<svg viewBox="0 0 24 24" width="10" height="10" ' +
            'fill="none" stroke="currentColor" stroke-width="3" ' +
            'stroke-linecap="round" stroke-linejoin="round">' +
            '<polyline points="' +
            (dir === "left" ? "15 6 9 12 15 18" : "9 6 15 12 9 18") +
            '"></polyline></svg>';

        const mkBtn = (content, page, opts) => {
            opts = opts || {};
            const b = document.createElement("button");
            b.type = "button";
            b.className = "pager-btn" + (opts.active ? " active" : "");
            if (opts.html) b.innerHTML = content;
            else b.textContent = content;
            if (opts.disabled) b.disabled = true;
            else b.onclick = () => {
                clearSelection(false);  // changing page drops the selection
                currentPage = page;
                applyFilters();
            };
            return b;
        };

        pager.appendChild(mkBtn(chevron("left"), currentPage - 1, {
            disabled: currentPage === 0,
            html: true,
        }));
        for (let p = 0; p < totalPages; p++) {
            pager.appendChild(mkBtn(String(p + 1), p, {
                active: p === currentPage,
            }));
        }
        pager.appendChild(mkBtn(chevron("right"), currentPage + 1, {
            disabled: currentPage >= totalPages - 1,
            html: true,
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
            if (bandedRows) tr.classList.toggle("banded", i % 2 === 1);
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
    }

    if (filterInput) {
        filterInput.oninput = () => {
            currentPage = 0;  // reset to first page on a new search
            applyFilters();
        };
    }

    // Close open column-filter popovers when clicking elsewhere.
    const onDocClick = () => {
        if (!columnFilter) return;
        thead.querySelectorAll(".filter-pop").forEach((p) => {
            p.style.display = "none";
        });
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


def smart_table(
    columns: List[str],
    rows: List[List[Any]],
    *,
    selecting: Literal["single", "multiple", "cell", "none"] = "none",
    selected: Optional[List[str]] = None,
    selected_cell: Optional[List[int]] = None,
    on_select: Optional[Callable[[Any], None]] = None,
    key: Optional[str] = None,
    width: Width = "stretch",
    filtering: Union[bool, Literal["table", "column", "both"]] = False,
    sorting: Union[bool, Literal["ascending", "descending"]] = False,
    page_size: Union[bool, int] = False,
    column_width: Literal["auto", "content"] = "auto",
    banded_rows: bool = False,
    toolbar: Union[bool, Literal["custom", "both"]] = False,
    toolbar_align: Literal["left", "center", "right"] = "right",
    custom_toolbar: Optional[List[List[Any]]] = None,
) -> Any:
    """Render a table with configurable selection.

    Args:
        columns: Column labels. A column's position is its key.
        rows: A list of rows, each a list of cell values aligned to
            ``columns`` by position. A row's id is its index (as a string).
        selecting: ``"single"`` (one row), ``"multiple"`` (many rows),
            ``"cell"`` (one cell) or ``"none"`` (default, not selectable).
        selected: Row ids (index strings) selected by default (row modes).
        selected_cell: ``[row_index, col_index]`` selected by default (cell
            mode).
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
        column_width: How columns are sized. ``"auto"`` (default) gives evenly
            sized columns and truncates overflowing text with an ellipsis.
            ``"content"`` sizes each column to its content without truncation.
        banded_rows: When ``True``, alternating rows get a subtle background
            tint (zebra striping). Defaults to ``False``.
        toolbar: Toolbar above the table. ``True`` shows the standard buttons
            (export to CSV). ``"custom"`` shows only the buttons defined in
            ``custom_toolbar``. ``"both"`` shows the standard buttons plus the
            custom ones. ``False`` (default) hides the toolbar.
        toolbar_align: Horizontal alignment of the toolbar buttons: ``"left"``,
            ``"center"`` or ``"right"`` (default).
        custom_toolbar: A list of ``[icon, callback]`` pairs. ``icon`` is an
            emoji or Material symbol (``"download"`` or ``":material/x:"``).
            Clicking the button calls ``callback(selection)`` with the current
            selection (row ids, or the ``[row, col]`` cell in cell mode).

    Returns:
        Row modes: the list of selected row ids (empty when none). Cell mode:
        the selected ``[row_index, col_index]`` or ``None``.
    """

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
        not isinstance(page_size, int)
        or isinstance(page_size, bool)
        or page_size < 1
    ):
        raise ValueError(
            f"Invalid page_size {page_size!r}. Expected a positive integer or "
            "False."
        )
    if column_width not in ("auto", "content"):
        raise ValueError(
            f"Invalid column_width {column_width!r}. Expected 'auto' or "
            "'content'."
        )
    if toolbar not in (True, False, "custom", "both"):
        raise ValueError(
            f"Invalid toolbar {toolbar!r}. Expected True, False, 'custom' "
            "or 'both'."
        )
    if toolbar_align not in ("left", "center", "right"):
        raise ValueError(
            f"Invalid toolbar_align {toolbar_align!r}. Expected 'left', "
            "'center' or 'right'."
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
        init_cell = stored if stored is not None else selected_cell
        default_selected = []
    else:
        default_selected = (
            list(stored) if stored is not None else list(selected or [])
        )
        init_cell = None

    data = json.dumps(
        {
            "columns": columns,
            "rows": rows,
            "selectionMode": selecting,
            "selected": default_selected,
            "selectedCell": init_cell,
            "filtering": filtering,
            "sorting": sorting,
            "pageSize": page_size if page_size is not False else 0,
            "columnWidth": column_width,
            "bandedRows": banded_rows,
            "toolbar": toolbar,
            "toolbarAlign": toolbar_align,
            "customToolbar": [item[0] for item in custom_toolbar],
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
    const { data, parentElement } = component;
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
# Card custom component (Custom Components v2)
# ---------------------------------------------------------------------------

_CARD_CSS = """
.pcard {
    border: 1px solid var(--st-border-color);
    border-radius: var(--st-base-radius, 0.5rem);
    padding: 1rem;
    font-family: var(--st-font);
    color: var(--st-text-color);
    background: var(--st-background-color);
    box-sizing: border-box;
}
.pcard .header {
    display: flex;
    align-items: center;
    gap: 0.625rem;
}
.pcard .avatar {
    width: 6rem;
    height: 6rem;
    border-radius: 0.5rem;
    flex: 0 0 auto;
    object-fit: cover;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
    background: var(--st-secondary-background-color);
}
.pcard .title { font-weight: 600; font-size: 1.25rem; line-height: 1.2; }
.pcard .subtitle { font-size: 0.875rem; line-height: 1.2; }
.pcard .status { font-size: 0.875rem; line-height: 1.2; opacity: 0.6; }
.pcard .status.active {
    opacity: 1;
    color: var(--st-primary-color);
    font-weight: 600;
}
.pcard hr {
    margin: 0.75rem 0;
    border: none;
    border-top: 1px solid var(--st-border-color);
}
"""

_CARD_JS = r"""
export default function(component) {
    const { data, parentElement } = component;
    parentElement.querySelectorAll(".pcard").forEach((el) => el.remove());

    const model = JSON.parse(data || "{}");
    const title = model.title || "";
    const imageUrl = model.imageUrl || "";
    const subtitle = model.subtitle || "";
    const status = model.status || "";
    const statusColor = model.statusColor || "inactive";

    function initials(n) {
        if (!n) return "?";
        const parts = n.split(/\s+/).filter(Boolean);
        if (!parts.length) return "?";
        if (parts.length === 1) return parts[0][0].toUpperCase();
        return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }

    const root = document.createElement("div");
    root.className = "pcard";

    const header = document.createElement("div");
    header.className = "header";

    let avatar;
    if (imageUrl) {
        avatar = document.createElement("img");
        avatar.src = imageUrl;
        avatar.alt = title;
    } else {
        avatar = document.createElement("div");
        avatar.textContent = initials(title);
    }
    avatar.className = "avatar";
    header.appendChild(avatar);

    const lines = document.createElement("div");
    if (title) {
        const el = document.createElement("div");
        el.className = "title";
        el.textContent = title;
        lines.appendChild(el);
    }
    if (subtitle) {
        const el = document.createElement("div");
        el.className = "subtitle";
        el.textContent = subtitle;
        lines.appendChild(el);
    }
    if (status) {
        const el = document.createElement("div");
        el.className = "status " + (statusColor === "active" ? "active" : "");
        el.textContent = status;
        lines.appendChild(el);
    }
    header.appendChild(lines);
    root.appendChild(header);

    parentElement.appendChild(root);
    return () => { root.remove(); };
}
"""

_card_component = st.components.v2.component(
    name="card",
    css=_CARD_CSS,
    js=_CARD_JS,
)


def card(
    title: Optional[str] = None,
    image_url: Optional[str] = None,
    subtitle: Optional[str] = None,
    status: Optional[str] = None,
    *,
    status_color: Literal["active", "inactive"] = "inactive",
    key: Optional[str] = None,
    width: Width = "stretch",
) -> None:
    """Render a card with an image and a title/subtitle/status header.

    It can represent anything (a person, a product, a place, ...). Only the
    fields that are provided are rendered.

    Args:
        title: Main heading of the card.
        image_url: URL of the card's image. When omitted, the initials
            derived from ``title`` are shown.
        subtitle: Secondary line shown below the title.
        status: Short status text (e.g. "In stock", "Online").
        status_color: ``"active"`` (primary) or ``"inactive"`` (default).
        key: Optional Streamlit widget key.
        width: Width of the card.
    """
    if not title and not image_url and not subtitle and not status:
        raise ValueError(
            "At least one of 'title', 'image_url', 'subtitle' or 'status' "
            "must be provided."
        )
    data = json.dumps(
        {
            "title": title,
            "imageUrl": image_url,
            "subtitle": subtitle,
            "status": status,
            "statusColor": status_color,
        }
    )
    with st.container(width=width):
        _card_component(data=data, key=key)
