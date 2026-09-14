from typing import List, Optional
from dataclasses import dataclass
from typing import Callable, List, Literal, Optional, Union

import streamlit as st

Width = Union[int, Literal["stretch", "content"]]
Height = Union[int, Literal["stretch", "content"]]


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
        inactive_background = st.get_option(
            "theme.secondaryBackgroundColor"
        ) or "var(--secondary-background-color, rgba(151, 166, 195, 0.25))"
        active_background = st.get_option(
            "theme.primaryColor"
        ) or "var(--primary-color, #FF4B4B)"
        is_last = active == len(self.__steps) - 1

        # One bordered container wrapping the whole widget.
        with st.container(border=True, width=self.__width):
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


class Box:
    """Renders a rounded rectangle with a themed background in a Streamlit app.

    The box background matches the sidebar/secondary background color and has
    rounded corners. Its content is supplied as one or more callables that
    render Streamlit widgets inside the box.

    Args:
        contents: One or more callables rendered inside the box.
        key: Unique key used to scope the box styling. Use distinct keys when
            rendering multiple boxes on the same page.
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
        width: Width = "stretch",
        height: Optional[Height] = None,
    ):
        if not contents:
            raise ValueError("At least one content callable must be provided.")
        self.__contents = contents
        self.__key = key
        self.__width = width
        self.__height = height
        self.__render()

    def __render(self):
        # Match the sidebar background: prefer the sidebar's own configured
        # color, then the secondary background (the sidebar's default), then
        # the CSS-variable fallback.
        background = (
            st.get_option("theme.sidebar.backgroundColor")
            or st.get_option("theme.secondaryBackgroundColor")
            or "var(--secondary-background-color, rgba(151, 166, 195, 0.25))"
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
            width=self.__width,
            height=self.__height if self.__height is not None else "content",
        ):
            for content in self.__contents:
                content()
