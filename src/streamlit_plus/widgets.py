import html
import re

from dataclasses import dataclass
from typing import Callable, List, Literal, Optional, Union, cast

import streamlit as st

Width = Union[int, Literal["stretch", "content"]]
Height = Union[int, Literal["stretch", "content"]]


def _validate_css_key(key: str) -> str:
    """Validate a key that gets interpolated into a raw ``<style>`` block.

    The key becomes part of a ``.st-key-<key>`` CSS selector emitted via
    ``unsafe_allow_html``. Restricting it to alphanumerics, underscores and
    hyphens keeps callers from breaking out of the ``<style>`` context (a CSS
    or HTML injection vector) and matches Streamlit's own key conventions.
    """
    if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", key):
        raise ValueError(
            "'key' must be a non-empty string of letters, digits, underscores "
            "or hyphens."
        )
    return key


_CSS_COLOR_RE = re.compile(
    r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})"
    r"|rgba?\(\s*(?:\d{1,3}%?\s*,\s*){2}"
    r"\d{1,3}%?(?:\s*,\s*(?:0|1|0?\.\d+))?\s*\)"
)


def _validate_css_color(color: str) -> str:
    """Validate a color interpolated into a raw ``<style>`` block.

    Only hex or ``rgb()``/``rgba()`` values are accepted, so a caller cannot
    break out of the CSS value and inject arbitrary style or markup. Mirrors
    the ``bg_color`` guard used by the tile component.
    """
    if not isinstance(color, str) or not _CSS_COLOR_RE.fullmatch(color):
        raise ValueError("'bg_color' must be a hex or rgb/rgba color.")
    return color


def _safe_theme_color(value: object, fallback: str) -> str:
    """Return a theme color only when it is safe to interpolate into CSS."""
    if isinstance(value, str) and _CSS_COLOR_RE.fullmatch(value):
        return value
    return fallback


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
        width: Width of the wizard. ``"stretch"`` (default), ``"content"``, or
            a fixed pixel width.

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
        width: Width = "stretch",
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
        self.__width = width
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
        inactive_background = _safe_theme_color(
            st.get_option("theme.secondaryBackgroundColor"),
            "var(--secondary-background-color, rgba(151, 166, 195, 0.25))",
        )
        active_background = _safe_theme_color(
            st.get_option("theme.primaryColor"),
            "var(--primary-color, #FF4B4B)",
        )
        is_last = active == len(self.__steps) - 1

        # One bordered container wrapping the whole widget.
        with st.container(border=True, width=cast(Width, self.__width)):
            if self.__name:
                st.markdown(
                    '<h3 style="text-align: center; margin: 0;">'
                    f"{html.escape(self.__name)}</h3>",
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
                        'font-size: inherit; padding: 0.25rem 0.5rem;">'
                        f"{html.escape(label)}</span>",
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


class Box:
    """Renders a rounded rectangle with a themed background in a Streamlit app.

    The box background matches the sidebar/secondary background color and has
    rounded corners. Its content is supplied as one or more callables that
    render Streamlit widgets inside the box.

    Args:
        contents: One or more callables rendered inside the box.
        key: Unique key used to scope the box styling. Use distinct keys when
            rendering multiple boxes on the same page.
        bg_color: Background color of the box. ``None`` (default) uses the
            standard Streamlit sidebar background color.
        width: Width of the box. ``"stretch"`` (default), ``"content"``, or a
            fixed pixel width.
        height: Height of the box. ``None`` (default) uses Streamlit's standard
            behavior; otherwise ``"stretch"``, ``"content"``, or a fixed pixel
            height.

    Example:
        >>> def body():
        ...     st.write("Hello from inside the box!")
        >>> Box(body)
    """

    def __init__(
        self,
        *contents: Callable[[], None],
        key: str = "box",
        bg_color: Optional[str] = None,
        width: Width = "stretch",
        height: Optional[Height] = None,
    ):
        if not contents:
            raise ValueError("At least one content callable must be provided.")
        self.__contents = contents
        self.__key = _validate_css_key(key)
        self.__bg_color = (
            _validate_css_color(bg_color) if bg_color is not None else None
        )
        self.__width = width
        self.__height = height
        self.__render()

    def __render(self):
        # Match the sidebar background: prefer the sidebar's own configured
        # color, then the secondary background (the sidebar's default), then
        # the CSS-variable fallback.
        background = self.__bg_color
        if background is None:
            background = _safe_theme_color(
                st.get_option("theme.sidebar.backgroundColor"),
                "",
            )
        if not background:
            background = _safe_theme_color(
                st.get_option("theme.secondaryBackgroundColor"),
                "var(--secondary-background-color, rgba(151, 166, 195, 0.25))",
            )
        st.markdown(
            "<style>"
            f".st-key-{self.__key} {{"
            f"background: {background}; "
            "border-radius: 0.75rem; "
            "padding: 1rem;"
            "}"
            "</style>",
            unsafe_allow_html=True,
        )
        with st.container(
            key=self.__key,
            width=cast(Width, self.__width),
            height=cast(
                Height,
                self.__height if self.__height is not None else "content",
            ),
        ):
            for content in self.__contents:
                content()


class Card:

    def __init__(
        self,
        title: Optional[str] = None,
        image_url: Optional[str] = None,
        subtitle: Optional[str] = None,
        status: Optional[str] = None,
        *,
        status_color: Literal["active", "inactive"] = "inactive",
        key: Optional[str] = None,
        width: Width = "stretch",
        image_height: Optional[int] = None,
        content: Callable[[], None],
    ) -> None:
        if image_height is not None and image_height < 1:
            raise ValueError("'image_height' must be a positive integer or None.")
        if status_color not in ("active", "inactive"):
            raise ValueError(
                f"Invalid status_color {status_color!r}. Expected 'active' or "
                "'inactive'."
            )
        self.__title = title
        self.__image_url = image_url
        self.__subtitle = subtitle
        self.__status = status
        self.__status_color = status_color
        self.__key = _validate_css_key(key) if key else f"card_{id(self)}"
        self.__width = width
        self.__image_height = image_height
        self.__content = content
        self.__render()

    def __render(self):
        if self.__image_height is not None:
            st.markdown(
                "<style>"
                f".st-key-{self.__key} img {{"
                f"height: {self.__image_height}px; "
                "width: 100%; "
                "object-fit: cover; "
                "object-position: center;"
                "}"
                "</style>",
                unsafe_allow_html=True,
            )
        with st.container(
            border=True,
            key=self.__key,
            width=cast(Width, self.__width),
        ):
            st.image(self.__image_url, width="stretch") if self.__image_url else None
            st.markdown(self.__title) if self.__title else None
            st.caption(self.__subtitle) if self.__subtitle else None
            st.text(self.__status) if self.__status else None
            self.__content()
