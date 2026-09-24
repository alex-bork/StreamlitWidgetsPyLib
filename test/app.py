import streamlit as st
from streamlit_plus import (
    Box,
    FormWizard,
    Step,
    breadcrumbs,
    calendar,
    persona,
    table,
    tree,
)
from streamlit_plus.custom_components import (
    clickable,
    icon,
    tile,
)

SPACE_HEIGHT = 50

with st.sidebar:
    st.title("Testing st.Plus")

    type = st.selectbox(
        label="Component type",
        label_visibility="collapsed",
        options=["Custom components", "Widgets"],
    )


if type == "Custom components":
    st.subheader("Icon components", anchor=False)

    with st.container(horizontal=True, horizontal_alignment="left"):

        icon(
            material_name=":material/box:",
            size="medium",
            status=3,
            on_click=lambda: st.toast("Icon clicked"),
        )
        icon(
            label="Empty Box",
            # label_visibility="collapsed",
            material_name=":material/box:",
            size="large",
            status="1000",
            # on_click=lambda: st.toast("Icon clicked"),
        )

    st.container(height=SPACE_HEIGHT, border=False)
    st.subheader("Breadcrumbs", anchor=False)
    breadcrumbs(
        [
            {"label": "Homepage", "page": "http://google.de"},
            {"label": "Settings", "page": None},
            {"label": "Special Keys", "page": None},
        ],
        size="medium",
        all_links_disabled=False,
        # bg_color=None,
    )

    st.container(height=SPACE_HEIGHT, border=False)
    st.subheader("Clickable", anchor=False)

    with st.container(horizontal=True, horizontal_alignment="left", border=True):
        with clickable(
            key="demo_clickable",
            width_inheritance="child",
            on_click=lambda: st.toast("Container clicked"),
        ):
            st.write("Click this container, or use its button.")
            if st.button("Child action", key="demo_clickable_child_action"):
                st.toast("Child action clicked")

    st.container(height=SPACE_HEIGHT, border=False)
    st.subheader("Tile", anchor=False)

    with tile(
        title="Team activity",
        caption="Latest updates",
        icon=":material/insights:",
        width=200,
        height="content",
        # icon_position="left",
        # border=True,
        # shape="square",
        # bg_color="rgb(245, 247, 250)",
        # key="demo_tile",
        # scrollable=False,
        on_click=lambda: st.toast("Tile clicked"),
    ):
        # st.metric("Active users", 128, delta="12%")
        st.write("This is regular Streamlit content inside the tile.")
        # st.button("hi")

    st.container(height=SPACE_HEIGHT, border=False)
    st.subheader("Persona", anchor=False)

    def on_popover():
        st.subheader("Popover Content")
        st.write("This is the content inside the popover.")

    with st.container(
        horizontal=True,
        horizontal_alignment="distribute",
        border=True,
        # height=380,
        # vertical_alignment="center",
    ):
        persona(
            name="Jordan Reyes",
            role="Developer",
            status="Offline",
            avatar_url="https://randomuser.me/api/portraits/men/32.jpg",
            text_align="right",
            size="small",
            image_shape="circle",
            status_color="active",
            popover=on_popover,
            popover_width=300,
            width="content",
        )

        persona(
            name="Jordan Reyes",
            role="Developer",
            status="Offline",
            avatar_url="https://randomuser.me/api/portraits/men/32.jpg",
            text_align="right",
            size="medium",
            image_shape="circle",
            status_color="active",
            popover=on_popover,
            popover_width=300,
            width="content",
        )

        persona(
            name="Jordan Reyes",
            role="Developer",
            status="Offline",
            avatar_url="https://randomuser.me/api/portraits/men/32.jpg",
            text_align="right",
            size="large",
            image_shape="circle",
            status_color="active",
            popover=on_popover,
            popover_width=200,
            width="content",
        )

    st.container(height=SPACE_HEIGHT, border=False)
    st.subheader("Tree", anchor=False)

    selected = tree(
        nodes=[
            {
                "id": "backend",
                "label": "Backend",
                "icon": ":material/dns:",
                "children": [
                    {"id": "api", "label": "API", "icon": ":material/api:"},
                    {"id": "db", "label": "Database", "icon": "🗄️"},
                ],
            },
            {"id": "frontend", "label": "Frontend", "icon": ":material/web:"},
        ],
        key="demo_menu_tree",
        width=200,
        selected_node="backend",
        spacing="small",
    )

    previous_menu_selection = st.session_state.get("demo_menu_selection")
    if selected and selected != previous_menu_selection:
        st.toast(f"Selected node: {selected}")
    st.session_state.demo_menu_selection = selected

    st.container(height=SPACE_HEIGHT, border=False)
    st.subheader("Calendar", anchor=False)

    cal_mode = st.radio(
        "Calendar selection",
        [None, "single", "range"],
        label_visibility="collapsed",
        horizontal=True,
    )

    cal_selected = calendar(
        selection=cal_mode,
        active_days=[["23", "24"]],
        layout="double" if cal_mode == "range" else "single",
        key="demo_calendar",
        navigation=None if cal_mode is None else "arrow",
    )

    if cal_selected:
        st.toast(f"Selected date(s): {cal_selected}")

    st.container(height=SPACE_HEIGHT, border=False)
    st.subheader("Table", anchor=False)

    smart_table_section = st.container(gap=None)
    mode = smart_table_section.radio(
        "Selection mode",
        ["none", "single", "multiple", "cell"],
        label_visibility="collapsed",
        horizontal=True,
    )

    def on_columns_change(column_order):
        st.toast(f"Columns reordered: {', '.join(column_order)}")

    with smart_table_section:
        selected_rows = table(
            columns=["Name", "Role", "Status", "Notes"],
            rows=[
                [
                    "Jordan Reyes",
                    "Developer",
                    "Online",
                    "Leads the backend platform team and maintains the shared "
                    "API gateway used across all services. Owns the authentication "
                    "layer, the rate limiter and the service mesh configuration, "
                    "and mentors two junior engineers while reviewing the majority "
                    "of the backend pull requests every single week.",
                ],
                [
                    "Sam Lee",
                    "Designer",
                    "Away",
                    "Owns the design system and is currently reworking the "
                    "component library tokens for the upcoming theme refresh, "
                    "including color, spacing and typography scales, while also "
                    "auditing every existing screen for consistency and preparing "
                    "detailed handoff specifications for the engineering team.",
                ],
                [
                    "Jo Diaz",
                    "Product Manager",
                    "Offline",
                    "Coordinates the roadmap between engineering, design and "
                    "external stakeholders for the customer portal, runs the "
                    "quarterly planning sessions, maintains the prioritized "
                    "backlog, and gathers feedback from dozens of enterprise "
                    "customers to shape the direction of the product over time.",
                ],
                [
                    "Priya Nair",
                    "Data Scientist",
                    "Online",
                    "Builds forecasting models and the anomaly-detection pipeline "
                    "for the analytics dashboard, owns the feature store, and "
                    "collaborates with the platform team to productionize models, "
                    "monitor drift, and continuously retrain them as new labelled "
                    "data arrives from the ever growing customer base each month.",
                ],
                [
                    "Marcus O'Sullivan",
                    "DevOps Engineer",
                    "Busy",
                    "Runs the CI/CD infrastructure and the on-call rotation, is "
                    "migrating the entire cluster to a new region this quarter, "
                    "and is hardening the deployment pipeline with automated "
                    "rollbacks, canary releases and much more thorough "
                    "observability across every environment the company operates.",
                ],
                [
                    "Yuki Tanaka",
                    "QA Lead",
                    "Online",
                    "Defines the automated test strategy and manages the "
                    "regression suite across web and mobile, maintains the "
                    "end-to-end testing framework, triages flaky tests, and works "
                    "closely with developers to build a culture where quality is "
                    "everyone's responsibility rather than a final gate at the end.",
                ],
                [
                    "Fatima Al-Rashid",
                    "Frontend Developer",
                    "Away",
                    "Implements the new dashboard views and steadily improves "
                    "accessibility across the whole application, refactoring older "
                    "components to the shared design system, adding keyboard "
                    "navigation and screen-reader support, and measuring real user "
                    "performance to keep the interface fast on lower-end devices.",
                ],
                [
                    "Tom Becker",
                    "Support Engineer",
                    "Offline",
                    "First point of contact for enterprise customers, triages "
                    "incidents, escalates critical bugs to engineering, and writes "
                    "the internal troubleshooting guides and public help-center "
                    "articles that reduce ticket volume, while also collecting "
                    "recurring pain points to feed back into the product roadmap.",
                ],
                [
                    "Nina Kowalski",
                    "Security Engineer",
                    "Online",
                    "Owns the security review process, runs penetration tests and "
                    "manages the bug-bounty program for the whole platform.",
                ],
                [
                    "Diego Fernandez",
                    "Mobile Developer",
                    "Busy",
                    "Builds the iOS and Android apps, maintains the shared React "
                    "Native codebase and coordinates store releases each sprint.",
                ],
                [
                    "Aisha Mohammed",
                    "Technical Writer",
                    "Online",
                    "Writes and maintains the developer documentation, API "
                    "references and onboarding tutorials for new integrators.",
                ],
                [
                    "Lars Andersen",
                    "Site Reliability Engineer",
                    "Away",
                    "Keeps the production systems healthy, tunes autoscaling and "
                    "leads incident post-mortems to prevent repeat outages.",
                ],
                [
                    "Mei Chen",
                    "Machine Learning Engineer",
                    "Online",
                    "Productionizes recommendation models and builds the feature "
                    "pipelines that feed the personalization engine.",
                ],
                [
                    "Oliver Schmidt",
                    "Backend Developer",
                    "Offline",
                    "Implements the billing and subscription services and keeps "
                    "the payment-provider integrations up to date.",
                ],
                [
                    "Grace Okoro",
                    "UX Researcher",
                    "Busy",
                    "Runs usability studies and customer interviews, turning "
                    "findings into actionable design and product recommendations.",
                ],
                [
                    "Hiroshi Sato",
                    "Database Administrator",
                    "Online",
                    "Manages the primary and replica databases, plans capacity "
                    "and owns the backup and disaster-recovery procedures.",
                ],
                [
                    "Elena Popova",
                    "Engineering Manager",
                    "Away",
                    "Leads two feature teams, runs one-on-ones and hiring, and "
                    "keeps delivery aligned with the quarterly product goals.",
                ],
                [
                    "Carlos Mendez",
                    "Solutions Architect",
                    "Online",
                    "Designs integrations for large enterprise customers and "
                    "advises on scalable, secure reference architectures.",
                ],
                [
                    "Rachel Kim",
                    "Platform Engineer",
                    "Online",
                    "Builds internal developer tooling and improves service "
                    "reliability across the shared platform infrastructure.",
                ],
                [
                    "Noah Williams",
                    "Data Engineer",
                    "Away",
                    "Maintains ingestion pipelines and data-quality checks for "
                    "the analytics and reporting systems.",
                ],
                [
                    "Sofia Rossi",
                    "Product Designer",
                    "Busy",
                    "Designs workflow improvements and contributes patterns to "
                    "the shared product design system.",
                ],
                [
                    "Daniel Okafor",
                    "QA Engineer",
                    "Online",
                    "Expands automated coverage and monitors regression quality "
                    "across the customer-facing applications.",
                ],
                *[
                    [
                        f"Demo User {index:02d}",
                        ["Developer", "Designer", "Analyst", "Engineer"][index % 4],
                        ["Online", "Away", "Busy", "Offline"][index % 4],
                        f"Temporary generated record {index} for pagination "
                        "and table interaction testing.",
                    ]
                    for index in range(1, 31)
                ],
            ],
            selecting=mode,
            filtering="column",
            sorting=True,
            draggable_columns=True,
            page_size=7,
            switch_page="selectbox",
            column_width="auto",
            active_columns=["Name", "Role", "Status"],
            # zebra_stripping=True,
            standard_toolbar=True,
            standard_toolbar_exclude=["export_csv"],
            toolbar_align="right",
            custom_toolbar=[
                [":material/delete:", lambda sel: st.toast(f"Delete {sel}")],
                [":material/star:", lambda sel: st.toast(f"Star {sel}")],
            ],
            on_columns_change=on_columns_change,
            key="demo_smart_table",
        )

    if selected_rows:
        st.toast(f"Selection: {selected_rows}")


else:  # "Widgets"
    st.container(height=SPACE_HEIGHT, border=False)
    st.subheader("FormWizard", anchor=False)

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
        width=300,
        # name="Sign up",
        on_finish=lambda: st.success("Wizard complete!"),
        on_next=lambda step: st.toast(f"Moved to step {step + 1}"),
        use_wizard_width=False,
        inactive_on_finish=True,
    )

    st.container(height=SPACE_HEIGHT, border=False)
    st.subheader("Box", anchor=False)

    def box_body():
        st.markdown("**Quick summary**")
        st.write("This content sits inside a themed, rounded box.")
        st.button("Action")

    Box(box_body, key="summary_box", width=300)
