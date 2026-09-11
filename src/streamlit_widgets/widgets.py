from typing import List, Optional
import html
from dataclasses import dataclass
from typing import Callable, List, Literal, Optional

import streamlit as st


class BreadcrumbsLink:
    """Describes one item in a breadcrumb navigation.

    Args:
        label: Text displayed for the breadcrumb item.
        page_url: URL opened in the current browser tab. When ``None``, the
            item is rendered as non-interactive text.
    """

    def __init__(self, label: str, page_url: Optional[str]):
        self.label = label
        self.page = page_url


class Breadcrumbs:
    """Renders a horizontal breadcrumb navigation in a Streamlit app.

    Active items navigate to their URL in the current browser tab. Items
    without a URL, or all items when ``link_disabled`` is ``True``, are
    rendered without navigation and hover feedback.

    Args:
        links: Ordered breadcrumb items to display.
        size: Text size of the breadcrumb items. ``"small"`` renders compact
            labels; ``"normal"`` matches the app's default body text size.
        all_links_disabled: Disables navigation and hover feedback for every
            item.
    """

    _LABEL_FONT_SIZE = {"small": "0.75rem", "normal": "0.875rem"}
    _SEPARATOR_FONT_SIZE = {"small": "1rem", "normal": "1.125rem"}

    def __init__(
        self,
        links: List[BreadcrumbsLink],
        size: Literal["small", "normal"] = "small",
        all_links_disabled: bool = False,
    ):
        if size not in self._LABEL_FONT_SIZE:
            raise ValueError(
                f"Invalid size {size!r}. Expected one of "
                f"{sorted(self._LABEL_FONT_SIZE)}."
            )
        self.__items = links
        self.__size = size
        self.__all_links_disabled = all_links_disabled
        self.__render()

    def __render(self):
        """Render breadcrumb items and separators using the active theme."""
        sidebar_background = st.get_option(
            "theme.secondaryBackgroundColor"
        ) or "var(--secondary-background-color, rgba(151, 166, 195, 0.25))"
        label_font_size = self._LABEL_FONT_SIZE[self.__size]
        separator_font_size = self._SEPARATOR_FONT_SIZE[self.__size]
        st.markdown(
            "<style>"
            "a.breadcrumbLink:hover { "
            f"background: {sidebar_background}; }}"
            ".st-key-breadcrumbs p { margin: 0; }"
            "</style>",
            unsafe_allow_html=True,
        )
        with st.container(
            key="breadcrumbs",
            horizontal=True,
            horizontal_alignment="left",
            vertical_alignment="center",
            gap=None,
        ):
            for i, item in enumerate(self.__items):
                is_link_active = not self.__all_links_disabled and item.page is not None
                link_attributes = (
                    'class="breadcrumbLink" ' f'href="{item.page}" target="_self"'
                    if is_link_active
                    else 'class="breadcrumbLink" aria-disabled="true"'
                )
                link_tag = "a" if is_link_active else "span"
                st.markdown(
                    f"<{link_tag} {link_attributes} "
                    'style="display: inline-flex; align-items: center; '
                    "line-height: 1; border-radius: 3rem; "
                    "color: inherit; font-family: inherit; "
                    f"font-size: {label_font_size}; "
                    'padding: 0.25rem 0.375rem; text-decoration: none;">'
                    f"{item.label}</{link_tag}>",
                    unsafe_allow_html=True,
                )
                if i < len(self.__items) - 1:
                    st.markdown(
                        '<span class="breadcrumbSeparator" '
                        'style="display: inline-flex; align-items: center; '
                        "line-height: 1; opacity: 0.6; color: inherit; "
                        f"font-family: inherit; font-size: {separator_font_size}; "
                        'padding: 0.25rem 0; margin: 0 0.25rem;">&rsaquo;</span>',
                        unsafe_allow_html=True,
                    )


@dataclass
class Step:
    """One step of a :class:`FormWizard`.

    Args:
        name: Label shown in the step indicator.
        render: Callable that draws the step's input widgets. It is invoked
            inside the step's form.
    """

    name: str
    render: Callable[[], None]


class FormWizard:
    """Renders a multi-step form wizard in a Streamlit app.

    The wizard owns form creation: it renders a step indicator and a single
    form for the currently active step only. Pass the ordered steps to the
    constructor, then call :meth:`render`. The active step is tracked in
    ``st.session_state`` so it persists across reruns.

    Args:
        steps: Ordered wizard steps.
        name: Optional title shown at the top of the wizard.
        key: Session-state key used to remember the active step.
        on_finish: Optional callable invoked when the final step is submitted.
        on_next: Optional callable invoked when the user advances to the next
            step. It receives the index of the step being moved to.
        use_wizard_width: When ``True`` (default), the navigation buttons
            stretch across the full width of the widget. When ``False``, they
            keep their natural size and are centered.
        inactive_on_finish: When ``True``, submitting the final step marks the
            wizard finished: no step is highlighted and both navigation
            buttons are disabled. When ``False`` (default), the wizard stays
            interactive after ``on_finish`` runs.

    Example:
        >>> def account():
        ...     st.text_input("Username")
        >>> def profile():
        ...     st.text_input("Email")
        >>> FormWizard(
        ...     steps=[
        ...         Step("Account", account),
        ...         Step("Profile", profile),
        ...     ]
        ... )
    """

    def __init__(
        self,
        steps: List[Step],
        name: Optional[str] = None,
        key: str = "form_wizard",
        on_finish: Optional[Callable[[], None]] = None,
        on_next: Optional[Callable[[int], None]] = None,
        use_wizard_width: bool = True,
        inactive_on_finish: bool = False,
    ):
        if not steps:
            raise ValueError("'steps' must contain at least one step.")
        self.__steps = steps
        self.__name = name
        self.__key = key
        self.__on_finish = on_finish
        self.__on_next = on_next
        self.__use_wizard_width = use_wizard_width
        self.__inactive_on_finish = inactive_on_finish
        self.__render()

    def __render(self):
        """Render the step indicator and the active step's form."""
        if self.__key not in st.session_state:
            st.session_state[self.__key] = 0
        finished_key = f"{self.__key}_finished"
        finished = self.__inactive_on_finish and st.session_state.get(
            finished_key, False
        )
        active = st.session_state[self.__key]
        inactive_background = st.get_option(
            "theme.secondaryBackgroundColor"
        ) or "var(--secondary-background-color, rgba(151, 166, 195, 0.25))"
        active_background = st.get_option(
            "theme.primaryColor"
        ) or "var(--primary-color, #FF4B4B)"
        is_last = active == len(self.__steps) - 1

        # One bordered container wrapping the whole widget.
        with st.container(border=True):
            if self.__name:
                st.markdown(
                    f'<h3 style="text-align: center; margin: 0;">{self.__name}</h3>',
                    unsafe_allow_html=True,
                )

            # Step indicator
            with st.container(
                key="wizard",
                horizontal=True,
                horizontal_alignment="center",
                vertical_alignment="center",
                gap="xsmall",
            ):
                for i, step in enumerate(self.__steps):
                    is_active = i == active and not finished
                    background = (
                        active_background if is_active else inactive_background
                    )
                    # Active step text matches the primary button's text
                    # color (white on the primary background). Inactive text
                    # uses the app background color, falling back to the CSS
                    # system ``canvas`` color so it tracks light/dark mode.
                    color = (
                        "var(--primary-content-color, white)"
                        if is_active
                        else "var(--background-color, canvas)"
                    )
                    label = step.name or str(i + 1)
                    st.markdown(
                        f'<span class="wizardStep" style="background: {background}; '
                        f"border-radius: 0.25rem; color: {color}; font-family: inherit; "
                        'font-size: 0.875rem; padding: 0.25rem 0.5rem;">'
                        f"{label}</span>",
                        unsafe_allow_html=True,
                    )
                    if i < len(self.__steps) - 1:
                        st.markdown(":material/chevron_right:")

            st.space()

            # Active step's form (no border of its own)
            with st.form(key=f"{self.__key}_step_{active}", border=False):
                self.__steps[active].render()
                st.space()
                next_label = "Finish" if is_last else "Next"
                back_disabled = finished or active == 0
                advance_disabled = finished
                if self.__use_wizard_width:
                    back_col, next_col = st.columns(2)
                    back = back_col.form_submit_button(
                        "Back",
                        disabled=back_disabled,
                        use_container_width=True,
                    )
                    advance = next_col.form_submit_button(
                        next_label,
                        type="primary",
                        disabled=advance_disabled,
                        use_container_width=True,
                    )
                else:
                    with st.container(
                        horizontal=True,
                        horizontal_alignment="center",
                        gap="small",
                    ):
                        back = st.form_submit_button(
                            "Back", disabled=back_disabled, width=100
                        )
                        advance = st.form_submit_button(
                            next_label,
                            type="primary",
                            disabled=advance_disabled,
                            width=100,
                        )

        if finished:
            if self.__on_finish is not None:
                self.__on_finish()
            return
        if back:
            st.session_state[self.__key] = active - 1
            st.rerun()
        elif advance:
            if is_last:
                if self.__inactive_on_finish:
                    st.session_state[finished_key] = True
                    st.rerun()
                elif self.__on_finish is not None:
                    self.__on_finish()
            else:
                next_step = active + 1
                st.session_state[self.__key] = next_step
                if self.__on_next is not None:
                    self.__on_next(next_step)
                st.rerun()


class Persona:
    """Renders a persona card in a Streamlit app.

    Shows an avatar next to the person's name, role and status. When no
    avatar URL is given, the person's initials are shown in a circle instead.
    Only the fields that are provided are rendered.

    Args:
        name: Name of the person.
        avatar_url: URL of the person's avatar image. When omitted, the
            initials derived from ``name`` are shown.
        role: Role or title of the person.
        status: Short status text shown below the role (e.g. "Online").
        text_align: Placement of the text relative to the avatar. ``"right"``
            (default) puts the text to the right, ``"left"`` to the left, and
            ``"bottom"`` centers the text below the avatar.
        status_color: Color of the status text. ``"active"`` uses the primary
            color (same as ``st.button(type="primary")``); ``"inactive"``
            (default) uses a muted color.
        size: Avatar size. ``"small"`` (default), ``"medium"`` or ``"large"``.
    """

    _TEXT_ALIGNS = ("left", "right", "bottom")
    _STATUS_COLORS = ("active", "inactive")
    _AVATAR_SIZE = {"small": "3rem", "medium": "6rem", "large": "9rem"}

    def __init__(
        self,
        name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        role: Optional[str] = None,
        status: Optional[str] = None,
        text_align: Literal["left", "right", "bottom"] = "right",
        status_color: Literal["active", "inactive"] = "inactive",
        size: Literal["small", "medium", "large"] = "small",
    ):
        if not name and not avatar_url and not status and not role:
            raise ValueError(
                "At least one of 'name', 'avatar_url', 'status' or 'role' "
                "must be provided."
            )
        if text_align not in self._TEXT_ALIGNS:
            raise ValueError(
                f"Invalid text_align {text_align!r}. Expected one of "
                f"{list(self._TEXT_ALIGNS)}."
            )
        if status_color not in self._STATUS_COLORS:
            raise ValueError(
                f"Invalid status_color {status_color!r}. Expected one of "
                f"{list(self._STATUS_COLORS)}."
            )
        if size not in self._AVATAR_SIZE:
            raise ValueError(
                f"Invalid size {size!r}. Expected one of "
                f"{sorted(self._AVATAR_SIZE)}."
            )
        self.__name = name
        self.__avatar_url = avatar_url
        self.__role = role
        self.__status = status
        self.__text_align = text_align
        self.__status_color = status_color
        self.__size = size
        self.__render()

    @staticmethod
    def __initials(name: Optional[str]) -> str:
        if not name:
            return "?"
        parts = [p for p in name.split() if p]
        if not parts:
            return "?"
        if len(parts) == 1:
            return parts[0][0].upper()
        return (parts[0][0] + parts[-1][0]).upper()

    def __avatar_html(self) -> str:
        size = self._AVATAR_SIZE[self.__size]
        if self.__avatar_url:
            src = html.escape(self.__avatar_url, quote=True)
            alt = html.escape(self.__name or "", quote=True)
            return (
                f'<img src="{src}" alt="{alt}" '
                f'style="width: {size}; height: {size}; border-radius: 50%; '
                'object-fit: cover; flex: 0 0 auto;" />'
            )
        # Fallback: initials in a themed circle.
        initials = html.escape(self.__initials(self.__name))
        return (
            f'<div style="width: {size}; height: {size}; border-radius: 50%; '
            "flex: 0 0 auto; display: flex; align-items: center; "
            "justify-content: center; font-weight: 600; "
            "background: var(--secondary-background-color, rgba(151, 166, 195, 0.25)); "
            f'color: inherit;">{initials}</div>'
        )

    def __render(self):
        name_size, role_size = {
            "small": ("0.8125rem", "0.75rem"),
            "medium": ("1rem", "0.875rem"),
            "large": ("1.25rem", "1rem"),
        }[self.__size]
        status_size = role_size

        lines = []
        if self.__name:
            lines.append(
                f'<div style="font-weight: 600; line-height: 1.2; '
                f'font-size: {name_size};">{html.escape(self.__name)}</div>'
            )
        if self.__role:
            lines.append(
                f'<div style="font-size: {role_size}; opacity: 0.75; '
                f'line-height: 1.2;">{html.escape(self.__role)}</div>'
            )
        if self.__status:
            if self.__status_color == "active":
                status_style = (
                    "color: var(--primary-color, #FF4B4B); font-weight: 600;"
                )
            else:
                status_style = "opacity: 0.6;"
            lines.append(
                f'<div style="font-size: {status_size}; line-height: 1.2; '
                f'{status_style}">{html.escape(self.__status)}</div>'
            )
        if self.__text_align == "bottom":
            text_css_align = "center"
            container_style = (
                "display: flex; flex-direction: column; align-items: center; "
                "gap: 0.5rem;"
            )
        elif self.__text_align == "left":
            text_css_align = "right"
            container_style = (
                "display: flex; flex-direction: row-reverse; "
                "align-items: center; gap: 0.625rem;"
            )
        else:  # "right"
            text_css_align = "left"
            container_style = (
                "display: flex; flex-direction: row; align-items: center; "
                "gap: 0.625rem;"
            )
        text_block = (
            '<div style="display: flex; flex-direction: column; '
            f'gap: 0.125rem; text-align: {text_css_align};">'
            + "".join(lines)
            + "</div>"
        )
        st.markdown(
            f'<div class="persona" style="{container_style}">'
            f"{self.__avatar_html()}{text_block}</div>",
            unsafe_allow_html=True,
        )
