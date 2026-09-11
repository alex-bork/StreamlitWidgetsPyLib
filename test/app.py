from typing import List
import streamlit as st
from streamlit_widgets import (
    Breadcrumbs,
    BreadcrumbsLink,
    FormWizard,
    Persona,
    Step,
)

with st.sidebar:
    st.title("Testing Widgets")


st.subheader("Breadcrumbs", anchor=False)

Breadcrumbs(
    [
        BreadcrumbsLink("Homepage", "http://google.de"),
        BreadcrumbsLink("Settings", None),
        BreadcrumbsLink("Special Keys", None),
    ],
    size="normal",
    all_links_disabled=False,
)


st.space()
st.subheader("Form Wizard", anchor=False)

def step_account():
    with st.container(horizontal=True, horizontal_alignment="center"):
        st.text_input("Username")
        st.text_input("Password", type="password")

def step_profile():
    st.text_input("Full name")
    st.text_input("Email")

def step_confirm():
    st.checkbox("I accept the terms")

FormWizard(
    steps=[
        Step("Account", step_account),
        Step("Profile", step_profile),
        Step("Confirm", step_confirm),
    ],
    # name="Sign up",
    on_finish=lambda: st.success("Wizard complete!"),
    on_next=lambda step: st.toast(f"Moved to step {step + 1}"),
    use_wizard_width=False,
    inactive_on_finish=True,
)


st.space()
st.subheader("Persona", anchor=False)

Persona(
    name="Alex Bork",
    role="Developer",
    status="Online",
    avatar_url="https://randomuser.me/api/portraits/men/32.jpg",
    text_align="right",
    size="medium",
    status_color="active",
)

Persona(
    name="Alex Bork",
    role="Developer",
    status="Online",
    avatar_url="https://randomuser.me/api/portraits/men/32.jpg",
    text_align="left",
    size="large"
)

Persona(
    name="Alex Bork",
    role="Developer",
    status="Online",
    avatar_url="https://randomuser.me/api/portraits/men/32.jpg",
    text_align="bottom",
)
