"""Database connection form.

Wraps ``reveilio.connect_db(...)`` across all four supported backends.
"""

from __future__ import annotations

import streamlit as st

import reveilio

BACKENDS = ["sqlite", "postgresql", "mysql", "mongodb"]

_DEFAULT_PORTS = {
    "postgresql": 5432,
    "mysql": 3306,
    "mongodb": 27017,
}


def render_db_form() -> None:
    """Render the DB connection form and apply it on submit."""
    st.subheader("Database (optional)")
    st.caption(
        "Reveilio stores analyses in SQLite, Postgres, MySQL, or MongoDB. "
        "Connect here to enable the Database and Save-to-DB features."
    )

    backend = st.selectbox("Backend", BACKENDS, index=0)

    with st.form("db_form", clear_on_submit=False):
        kwargs: dict[str, object] = {"backend": backend}

        if backend == "sqlite":
            kwargs["filepath"] = st.text_input(
                "Filepath",
                value="/data/reveilio.db",
                help="Inside the Docker container /data is a persistent named volume.",
            )
        else:
            kwargs["host"] = st.text_input("Host", value="host.docker.internal")
            kwargs["port"] = st.number_input(
                "Port",
                min_value=1,
                max_value=65535,
                value=_DEFAULT_PORTS.get(backend, 5432),
                step=1,
            )
            kwargs["database"] = st.text_input("Database", value="reveilio")
            kwargs["username"] = st.text_input("Username")
            kwargs["password"] = st.text_input("Password", type="password")

        kwargs["table_name"] = st.text_input("Table / collection name", value="reveilio_analyses")
        submitted = st.form_submit_button("Connect")

    if submitted:
        clean = {
            k: v for k, v in kwargs.items() if v not in (None, "") or k in {"backend", "table_name"}
        }
        try:
            cfg = reveilio.connect_db(**clean)  # type: ignore[arg-type]
        except Exception as e:  # noqa: BLE001
            st.error(f"Connection failed: {e}")
            return
        st.session_state.db_connected = True
        st.session_state.db_backend = cfg.backend
        st.success(f"Connected to {cfg.backend} ({cfg.get_connection_string()})")

    if st.session_state.get("db_connected") and st.button("Disconnect"):
        reveilio.disconnect_db()
        st.session_state.db_connected = False
        st.session_state.db_backend = None
        st.info("Disconnected.")
