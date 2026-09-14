import streamlit as st
from streamlit_plus import (
    Box,
    FormWizard,
    Step,
    breadcrumbs,
    card,
    menu_tree,
    persona,
    smart_table,
)

with st.sidebar:
    st.title("Testing Widgets")

    type = st.selectbox(
        "Component type",
        ["Custom component", "Widgets"],
    )


if type == "Custom component":
    st.subheader("Breadcrumbs", anchor=False)

    breadcrumbs(
        [
            {"label": "Homepage", "page": "http://google.de"},
            {"label": "Settings", "page": None},
            {"label": "Special Keys", "page": None},
        ],
        size="medium",
        all_links_disabled=False,
    )

    st.space()
    st.subheader("Persona", anchor=False)

    persona(
        name="Alex Bork",
        role="Developer",
        status="Offline",
        avatar_url="https://randomuser.me/api/portraits/men/32.jpg",
        text_align="right",
        size="medium",
        status_color="active",
    )

    st.space()
    st.subheader("Card", anchor=False)

    card(
        title="Alex Bork",
        subtitle="Senior Developer",
        status="Online",
        status_color="active",
        image_url="https://randomuser.me/api/portraits/men/32.jpg",
        width=300,
    )

    st.space()
    st.subheader("Menu Tree", anchor=False)

    selected = menu_tree(
        tree=[
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
        # selected_node="db"
    )

    if selected:
        st.write(f"Selected node: {selected}")

    st.space()
    st.subheader("Smart Table", anchor=False)

    mode = st.radio(
        "Selection mode",
        ["none", "single", "multiple", "cell"],
        horizontal=True,
    )

    selected_rows = smart_table(
        columns=["Name", "Role", "Status", "Notes"],
        rows=[
            [
                "Alex Bork",
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
        ],
        selecting=mode,
        filtering="column",
        sorting=True,
        page_size=7,
        column_width="auto",
        banded_rows=True,
        toolbar="both",
        toolbar_align="right",
        custom_toolbar=[
            [":material/delete:", lambda sel: st.toast(f"Delete {sel}")],
            [":material/star:", lambda sel: st.toast(f"Star {sel}")],
        ],
        key="demo_smart_table",
    )

    if selected_rows:
        st.write(f"Selection: {selected_rows}")


else:  # "Widgets"
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

    st.space()
    st.subheader("Box", anchor=False)

    def box_body():
        st.markdown("**Quick summary**")
        st.write("This content sits inside a themed, rounded box.")
        st.button("Action")

    Box(box_body, key="summary_box", width=300)
