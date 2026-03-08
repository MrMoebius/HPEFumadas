"""Dashboard del Gemelo Digital — Camion de Bomberos BOM-001."""

import os
import time
import requests
import plotly.graph_objects as go
import folium
import streamlit as st
from streamlit_folium import st_folium
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

# ── Config / Branding ───────────────────────────────────────────────────────

API_URL = os.getenv("API_URL", "http://localhost:8002")
VEHICLE_ID = os.getenv("VEHICLE_ID", "BOM-001")

FIRE_RED = "#e74c3c"
FIRE_ORANGE = "#e67e22"
FIRE_YELLOW = "#f1c40f"
FIRE_BLUE = "#2980b9"
FIRE_DARK = "#111827"
FIRE_LIGHT = "#f9fafb"

st.set_page_config(
    page_title=f"Gemelo Digital — {VEHICLE_ID}",
    page_icon="\U0001F692",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Tema (oscuro / claro) ──────────────────────────────────────────────────

if "theme_mode" not in st.session_state:
    st.session_state["theme_mode"] = "dark"

theme_mode = st.session_state["theme_mode"]
is_dark = theme_mode == "dark"

bg_color = FIRE_DARK if is_dark else FIRE_LIGHT
card_bg = "#111827" if is_dark else "#ffffff"
card_border = FIRE_RED if is_dark else FIRE_BLUE
text_color = "#f9fafb" if is_dark else "#111827"
muted_text = "#9ca3af" if is_dark else "#6b7280"

# ── CSS ─────────────────────────────────────────────────────────────────────

st.markdown(f"""
<style>
    .block-container {{
        padding-top: 1.5rem;
        padding-bottom: 0.5rem;
    }}
    body {{
        background-color: {bg_color};
        color: {text_color};
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    [data-testid="stMetric"] {{
        background: rgba(37, 99, 235, 0.10);
        border-radius: 10px;
        padding: 12px 16px;
        border-left: 4px solid {FIRE_BLUE};
    }}
    .alert-card {{
        border-radius: 10px;
        padding: 10px 14px;
        margin-bottom: 8px;
        border-left: 4px solid {card_border};
        background: {card_bg};
        box-shadow: 0 8px 16px rgba(15, 23, 42, 0.45);
    }}
    .timeline-dot {{
        width: 10px;
        height: 10px;
        border-radius: 999px;
        display: inline-block;
        margin-right: 6px;
        border: 2px solid {FIRE_YELLOW};
    }}
</style>
""", unsafe_allow_html=True)

# ── API helpers ─────────────────────────────────────────────────────────────


def api_get(path: str):
    try:
        r = requests.get(f"{API_URL}{path}", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def api_post(path: str, body: dict = None):
    try:
        r = requests.post(f"{API_URL}{path}", json=body or {}, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


# ── Gauge helpers ───────────────────────────────────────────────────────────


def gauge(title, value, lo, hi, unit="", steps=None, threshold=None):
    """Gauge where HIGH values are bad (temperature, RPM)."""
    if steps is None:
        steps = [
            {"range": [lo, hi * 0.6], "color": "#2ecc71"},
            {"range": [hi * 0.6, hi * 0.85], "color": "#f39c12"},
            {"range": [hi * 0.85, hi], "color": "#e74c3c"},
        ]
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value,
        title={"text": title, "font": {"size": 14}},
        number={"suffix": f" {unit}", "font": {"size": 22}},
        gauge={
            "axis": {"range": [lo, hi], "tickwidth": 1},
            "bar": {"color": "#2c3e50"},
            "steps": steps,
            "threshold": {
                "line": {"color": "red", "width": 3},
                "thickness": 0.75,
                "value": threshold if threshold is not None else hi * 0.9,
            },
        },
    ))
    fig.update_layout(height=220, margin={"l": 15, "r": 15, "t": 50, "b": 5})
    return fig


def gauge_rev(title, value, lo, hi, unit="", warn=None, crit=None):
    """Gauge where LOW values are bad (fuel, water, battery)."""
    w = warn if warn is not None else hi * 0.3
    c = crit if crit is not None else hi * 0.15
    steps = [
        {"range": [lo, c], "color": "#e74c3c"},
        {"range": [c, w], "color": "#f39c12"},
        {"range": [w, hi], "color": "#2ecc71"},
    ]
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value,
        title={"text": title, "font": {"size": 14}},
        number={"suffix": f" {unit}", "font": {"size": 22}},
        gauge={
            "axis": {"range": [lo, hi], "tickwidth": 1},
            "bar": {"color": "#2c3e50"},
            "steps": steps,
            "threshold": {
                "line": {"color": "red", "width": 3},
                "thickness": 0.75,
                "value": c,
            },
        },
    ))
    fig.update_layout(height=220, margin={"l": 15, "r": 15, "t": 50, "b": 5})
    return fig


# ── Severity helpers ────────────────────────────────────────────────────────

SEVERITY_COLORS = {
    "emergencia": "#c0392b",
    "critica": "#e74c3c",
    "advertencia": "#f39c12",
    "informativa": "#3498db",
    # Compat con severidades antiguas
    "critical": "#e74c3c",
    "warning": "#f39c12",
    "info": "#3498db",
}

SEVERITY_ICONS = {
    "emergencia": "\U0001F6A8",
    "critica": "\U0001F534",
    "advertencia": "\U0001F7E1",
    "informativa": "\U0001F535",
    "critical": "\U0001F534",
    "warning": "\U0001F7E1",
    "info": "\U0001F535",
}

SCENARIO_LABELS = {
    "pump_failure_during_fire": "Fallo de bomba durante incendio",
    "multi_fire_saturation": "Saturacion por multiples incendios",
    "ladder_hydraulic_failure": "Fallo hidraulico de escalera",
}

if "alerts_muted_until" not in st.session_state:
    st.session_state["alerts_muted_until"] = 0.0


def alerts_are_muted() -> bool:
    return time.time() < st.session_state.get("alerts_muted_until", 0.0)


def mute_alerts(minutes: int = 5):
    st.session_state["alerts_muted_until"] = time.time() + minutes * 60


# ── Fetch core data ────────────────────────────────────────────────────────

state = api_get(f"/api/v1/twin/{VEHICLE_ID}/state")
health = api_get(f"/api/v1/twin/{VEHICLE_ID}/health")
alerts_data = api_get(f"/api/v1/alerts/{VEHICLE_ID}")

# ── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## \U0001F692 BOM-001")
    st.caption("Gemelo Digital — Camion de Bomberos")
    # Tema
    theme_choice = st.radio(
        "Tema",
        ["Modo oscuro", "Modo claro"],
        index=0 if is_dark else 1,
        key="theme_selector",
    )
    new_mode = "dark" if theme_choice == "Modo oscuro" else "light"
    if new_mode != st.session_state["theme_mode"]:
        st.session_state["theme_mode"] = new_mode
        st.rerun()
    st.divider()

    # Health
    if health:
        score = health.get("health_score", 0)
        status = health.get("status", "unknown")
        if status == "healthy":
            st.success(f"Salud: {score:.0%} — OPERATIVO")
        elif status == "degraded":
            st.warning(f"Salud: {score:.0%} — DEGRADADO")
        else:
            st.error(f"Salud: {score:.0%} — CRITICO")
    else:
        st.error("Sin conexion con API")

    # Mission
    if state:
        mission = state.get("mission_status", "desconocido")
        icons = {
            "disponible": "\U0001F7E2",
            "en_ruta": "\U0001F535",
            "en_escena": "\U0001F534",
            "regreso_base": "\U0001F7E1",
        }
        icon = icons.get(mission, "\u26AA")
        label = mission.replace("_", " ").upper()
        st.info(f"{icon} Mision: **{label}**")
        st.caption(f"Tick #{state.get('tick', '?')} | {state.get('timestamp', '')}")

    st.divider()

    # Alert count
    if alerts_data and alerts_data.get("count", 0) > 0:
        total_alerts = alerts_data["count"]
        crit_count = 0
        for a in alerts_data.get("alerts", []):
            sev = a.get("severity", "informativa")
            if sev in ("emergencia", "critica", "critical"):
                crit_count += 1
        label = f"{total_alerts} alerta(s) activa(s)"
        if crit_count:
            label += f" | {crit_count} critica(s)"
        if alerts_are_muted():
            label += " · SILENCIADAS"
        st.error(f"\U0001F514 {label}")

    # City selector
    cities_resp = api_get("/api/v1/geo/cities")
    cities = cities_resp.get("cities", ["Valencia"]) if cities_resp else ["Valencia"]
    if "city" not in st.session_state:
        st.session_state["city"] = cities[0]
    city = st.selectbox("Ciudad", cities, index=cities.index(st.session_state["city"]) if st.session_state["city"] in cities else 0)
    if city != st.session_state["city"]:
        st.session_state["city"] = city
        st.session_state.pop("station", None)
        st.rerun()

    # Station selector (filtrado por ciudad)
    stations_resp = api_get(f"/api/v1/geo/poi/stations?city={city}")
    stations_list = stations_resp.get("stations", []) if stations_resp else []
    if stations_list:
        station_names = [s["name"] for s in stations_list]
        current_station_name = None
        if "station" in st.session_state and st.session_state["station"]:
            current_station_name = st.session_state["station"].get("name")
        default_idx = 0
        if current_station_name and current_station_name in station_names:
            default_idx = station_names.index(current_station_name)
        selected_station_name = st.selectbox("Estacion base", station_names, index=default_idx)
        selected_station = next((s for s in stations_list if s["name"] == selected_station_name), stations_list[0])
        st.session_state["station"] = selected_station

    # Navigation
    page = st.radio(
        "Navegacion",
        [
            "Centro de Mando",
            "Estado en Tiempo Real",
            "Alertas",
            "Telemetria",
            "Mapa",
            "Simulacion",
            "Predicciones",
            "IA Avanzada",
        ],
        label_visibility="collapsed",
    )

    st.divider()

    # Force emergency button (atajo desde sidebar)
    if state and state.get("mission_status") == "disponible":
        if st.button("SIMULAR EMERGENCIA", type="primary"):
            resp = api_post("/api/v1/geo/force-emergency", {})
            if resp and resp.get("status") == "ok":
                st.success("Emergencia enviada!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Error enviando comando")
    elif state:
        st.button("SIMULAR EMERGENCIA", disabled=True,
                  help="El vehiculo ya esta en mision")

    st.divider()

    # Auto-refresh toggle
    auto = st.checkbox("Auto-refresh (5s)", value=True)
    if st.button("Actualizar ahora"):
        st.rerun()

# Auto-refresh (desactivado en Mapa y Simulacion para no perder resultados)
if auto and page not in ("Mapa", "Simulacion"):
    st_autorefresh(interval=5000, key="auto_refresh")

# ── Guard / banner de conectividad ─────────────────────────────────────────

if not state:
    st.error("SIN DATOS — posible problema de conexion con API o MQTT")
    st.info(f"API: {API_URL}")
    st.stop()


# ── Header global ───────────────────────────────────────────────────────────

severity_order = ["emergencia", "critica", "critical", "advertencia", "warning", "informativa", "info"]
top_severity = None
if alerts_data and alerts_data.get("alerts"):
    for sev in severity_order:
        if any(a.get("severity") == sev for a in alerts_data["alerts"]):
            top_severity = sev
            break

mission = state.get("mission_status", "disponible")
mission_labels = {
    "disponible": "DISPONIBLE",
    "en_ruta": "EN RUTA",
    "en_escena": "EN ESCENA",
    "regreso_base": "REGRESO A BASE",
}
mission_label = mission_labels.get(mission, mission.replace("_", " ").upper())

mission_ticks = state.get("mission_ticks", state.get("tick", 0) or 0)
mission_seconds = int(mission_ticks * 2)
mission_min = mission_seconds // 60
mission_sec = mission_seconds % 60

header = st.container()
with header:
    h1, h2, h3 = st.columns([2, 2, 2])
    with h1:
        st.markdown(
            f"### \U0001F692 Gemelo Digital — **{VEHICLE_ID}**",
        )
        st.caption(f"Centro de mando operacional · {st.session_state.get('city', 'Valencia')}")
    with h2:
        icons = {
            "disponible": "\U0001F7E2",
            "en_ruta": "\U0001F535",
            "en_escena": "\U0001F534",
            "regreso_base": "\U0001F7E1",
        }
        icon = icons.get(mission, "\u26AA")
        st.markdown(f"**Estado mision:** {icon} {mission_label}")
        st.caption(f"Tick actual: {state.get('tick', '?')} · {state.get('timestamp', '')}")
    with h3:
        sev_icon = ""
        if top_severity:
            sev_icon = SEVERITY_ICONS.get(top_severity, "")
        st.markdown(
            f"**Tiempo de mision:** {mission_min}m {mission_sec:02d}s"
        )
        if top_severity:
            st.caption(f"Severidad actual: {sev_icon} {top_severity.upper()}")
        else:
            st.caption("Severidad actual: SIN ALERTAS")

# ── Salud del sistema / observabilidad ─────────────────────────────────────

sys_col1, sys_col2, sys_col3, sys_col4 = st.columns(4)

# Edad de la ultima telemetria
age_seconds = None
ts_str = state.get("timestamp")
if ts_str:
    try:
        # Timestamp en formato ISO UTC "2026-03-02T22:30:00Z"
        if ts_str.endswith("Z"):
            ts_str_clean = ts_str[:-1]
        else:
            ts_str_clean = ts_str
        last_dt = datetime.fromisoformat(ts_str_clean)
        now_dt = datetime.utcnow()
        age_seconds = max(0, (now_dt - last_dt).total_seconds())
    except Exception:
        age_seconds = None

with sys_col1:
    if health:
        st.metric("API / Twin", "OK", help="Respuesta de /health recibida")
    else:
        st.metric("API / Twin", "ERROR")
with sys_col2:
    if age_seconds is not None:
        label = f"{int(age_seconds)}s"
        if age_seconds < 5:
            st.success(f"Ultima telemetria: {label}")
        elif age_seconds < 20:
            st.warning(f"Ultima telemetria: {label}")
        else:
            st.error(f"Ultima telemetria: {label}")
    else:
        st.metric("Ultima telemetria", "N/D")
with sys_col3:
    # Heuristica: si hay telemetria reciente, MQTT OK
    if age_seconds is not None and age_seconds < 20:
        st.metric("MQTT", "OK")
    else:
        st.metric("MQTT", "SOSPECHOSO")
with sys_col4:
    # Placeholder: asumimos InfluxDB OK si API responde health
    if health:
        st.metric("InfluxDB", "OK")
    else:
        st.metric("InfluxDB", "DESCONOCIDO")

if age_seconds is not None and age_seconds > 20:
    st.error("Sin telemetria reciente — revisa simulador y conexion MQTT.")

# ════════════════════════════════════════════════════════════════════════════
#  CENTRO DE MANDO
# ════════════════════════════════════════════════════════════════════════════

if page == "Centro de Mando":
    st.header("Centro de Mando")

    # Panel de acciones rapidas
    ac1, ac2, ac3, ac4 = st.columns([1.2, 1.2, 1.2, 1.5])
    with ac1:
        if st.button("Forzar emergencia"):
            resp = api_post("/api/v1/geo/force-emergency", {})
            if resp and resp.get("status") == "ok":
                st.success("Emergencia enviada")
            else:
                st.error("No se pudo forzar la emergencia")
    with ac2:
        scenarios_resp = api_get("/api/v1/simulate/scenarios")
        scenario_name = None
        if scenarios_resp and scenarios_resp.get("scenarios"):
            scenario_dict = scenarios_resp["scenarios"]
            names = list(scenario_dict.keys())
            scenario_name = st.selectbox(
                "Escenario what-if",
                names,
                format_func=lambda x: SCENARIO_LABELS.get(x, x.replace("_", " ").title()),
                key="cm_scenario",
            )
        if scenario_name and st.button("Lanzar escenario"):
            st.session_state["last_scenario"] = scenario_name
            result = api_post("/api/v1/simulate/scenario", {"scenario": scenario_name})
            if result and "error" not in result:
                st.success("Escenario ejecutado")
            else:
                st.error("Error al ejecutar escenario")
    with ac3:
        if st.button("Resetear mision"):
            resp = api_post("/api/v1/geo/control", {"command": "reset_mission"})
            if resp and resp.get("status") == "ok":
                st.success("Mision reseteada")
            else:
                st.error("No se pudo resetear la mision")
    with ac4:
        if st.button("Repetir ultima mision"):
            last = st.session_state.get("last_scenario")
            if last:
                result = api_post("/api/v1/simulate/scenario", {"scenario": last})
                if result and "error" not in result:
                    st.success(f"Repetido escenario: {last}")
                else:
                    st.error("Error repitiendo escenario")
            else:
                st.info("Aun no se ha ejecutado ningun escenario")

    st.divider()

    col_timeline, col_alerts, col_chat = st.columns(3)

    # ── Col 1: Linea de tiempo ──────────────────────────────────────────
    with col_timeline:
        st.subheader("Linea de Tiempo")
        timeline = api_get(f"/api/v1/twin/{VEHICLE_ID}/timeline")
        if timeline and timeline.get("count", 0) > 0:
            for evt in timeline["events"][:20]:
                ts = evt.get("timestamp", "")
                if isinstance(ts, str) and len(ts) > 16:
                    ts = ts[11:19]
                if evt["type"] == "mission":
                    icon_from = icons.get(evt.get("from", ""), "\u26AA")
                    icon_to = icons.get(evt.get("to", ""), "\u26AA")
                    st.markdown(
                        f"`{ts}` {icon_from} -> {icon_to} "
                        f"**{evt.get('from', '?')}** -> **{evt.get('to', '?')}**"
                    )
                elif evt["type"] == "alert":
                    sev = evt.get("severity", "informativa")
                    sev_icon = SEVERITY_ICONS.get(sev, "\U0001F535")
                    st.markdown(
                        f"`{ts}` {sev_icon} [{sev.upper()}] {evt.get('message', '')}"
                    )
        else:
            st.info("Sin eventos aun")

    # ── Col 2: Alertas activas ──────────────────────────────────────────
    with col_alerts:
        st.subheader("Alertas Activas")
        if alerts_data and alerts_data.get("count", 0) > 0:
            alerts_list = alerts_data["alerts"]

            # Contadores por severidad
            counts = {}
            for a in alerts_list:
                sev = a.get("severity", "informativa")
                counts[sev] = counts.get(sev, 0) + 1

            cols_sev = st.columns(len(counts)) if counts else []
            for i, (sev, cnt) in enumerate(counts.items()):
                color = SEVERITY_COLORS.get(sev, "#888")
                cols_sev[i].markdown(
                    f"<div style='text-align:center;padding:4px;background:{color}20;"
                    f"border-radius:6px;border-left:3px solid {color}'>"
                    f"<b>{cnt}</b><br><small>{sev.upper()}</small></div>",
                    unsafe_allow_html=True,
                )

            st.markdown("---")

            # Lista de alertas con botones
            for a in alerts_list:
                sev = a.get("severity", "informativa")
                sev_icon = SEVERITY_ICONS.get(sev, "\U0001F535")
                msg = a.get("message", a.get("metric", "Sin detalle"))
                aid = a.get("alert_id", "?")
                status = a.get("status", "activa")

                st.markdown(f"{sev_icon} **{msg}** `{status}`")

                bc1, bc2, bc3 = st.columns(3)
                with bc1:
                    if st.button("ACK", key=f"ack_{aid}", type="primary"):
                        api_post(f"/api/v1/alerts/{VEHICLE_ID}/{aid}/confirm")
                        st.rerun()
                with bc2:
                    if st.button("ESC", key=f"esc_{aid}"):
                        api_post(f"/api/v1/alerts/{VEHICLE_ID}/{aid}/escalate")
                        st.rerun()
                with bc3:
                    if st.button("OFF", key=f"off_{aid}"):
                        api_post(f"/api/v1/alerts/{VEHICLE_ID}/{aid}/dismiss")
                        st.rerun()
        else:
            st.success("Sin alertas activas")

    # ── Col 3: Chat ─────────────────────────────────────────────────────
    with col_chat:
        st.subheader("Comunicaciones")

        chat_data = api_get(f"/api/v1/chat/{VEHICLE_ID}/messages")
        if chat_data and chat_data.get("count", 0) > 0:
            for msg in chat_data["messages"][-15:]:
                ts = msg.get("timestamp", "")
                if isinstance(ts, str) and len(ts) > 16:
                    ts = ts[11:19]
                sender = msg.get("sender", "?")
                text = msg.get("message", "")
                role = msg.get("role", "operador")
                if role == "sistema":
                    st.markdown(f"`{ts}` **[SIS]** {text}")
                else:
                    st.markdown(f"`{ts}` **{sender}:** {text}")
        else:
            st.caption("Sin mensajes")

        # Formulario de envio
        with st.form("chat_form", clear_on_submit=True):
            chat_input = st.text_input("Mensaje", placeholder="Escribe un mensaje...")
            chat_send = st.form_submit_button("Enviar")
            if chat_send and chat_input:
                api_post(f"/api/v1/chat/{VEHICLE_ID}/send", {
                    "sender": "operador",
                    "message": chat_input,
                    "role": "operador",
                })
                st.rerun()

    # ── Fila inferior: metricas clave ───────────────────────────────────
    st.divider()
    st.subheader("Metricas Clave")
    km1, km2, km3, km4, km5, km6 = st.columns(6)
    km1.metric("Motor", f"{state.get('engine_temp', 0):.0f} C")
    km2.metric("Agua", f"{state.get('water_tank_level', 0):.0f} %")
    km3.metric("Combustible", f"{state.get('fuel_level', 0):.0f} %")
    km4.metric("Velocidad", f"{state.get('speed_kmh', 0):.0f} km/h")
    km5.metric("Tripulacion", f"{state.get('crew_count', 0)}")
    km6.metric("Bomba", f"{state.get('pump_pressure', 0):.0f} PSI")

# ════════════════════════════════════════════════════════════════════════════
#  ESTADO EN TIEMPO REAL
# ════════════════════════════════════════════════════════════════════════════

elif page == "Estado en Tiempo Real":
    st.header("Estado en Tiempo Real")

    # Row 1 — main gauges
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.plotly_chart(gauge(
            "Motor", state.get("engine_temp", 0), 0, 150, "\u00b0C",
            steps=[
                {"range": [0, 100], "color": "#2ecc71"},
                {"range": [100, 115], "color": "#f39c12"},
                {"range": [115, 150], "color": "#e74c3c"},
            ], threshold=115,
        ), use_container_width=True)
    with c2:
        st.plotly_chart(gauge_rev(
            "Agua", state.get("water_tank_level", 0), 0, 100, "%",
            warn=20, crit=10,
        ), use_container_width=True)
    with c3:
        st.plotly_chart(gauge_rev(
            "Combustible", state.get("fuel_level", 0), 0, 100, "%",
            warn=20, crit=15,
        ), use_container_width=True)
    with c4:
        st.plotly_chart(gauge_rev(
            "Bateria", state.get("battery_voltage", 0), 10, 15, "V",
            warn=12.0, crit=11.5,
        ), use_container_width=True)

    # Row 2 — secondary gauges
    c5, c6, c7, c8 = st.columns(4)
    pump = state.get("pump_pressure", 0)
    with c5:
        pump_steps = ([
            {"range": [0, 30], "color": "#e74c3c"},
            {"range": [30, 80], "color": "#f39c12"},
            {"range": [80, 200], "color": "#2ecc71"},
        ] if pump > 0 else [
            {"range": [0, 200], "color": "#bdc3c7"},
        ])
        st.plotly_chart(gauge(
            "Bomba", pump, 0, 200, "PSI",
            steps=pump_steps, threshold=30,
        ), use_container_width=True)
    with c6:
        st.plotly_chart(gauge_rev(
            "Espuma", state.get("foam_tank_level", 0), 0, 100, "%",
            warn=20, crit=10,
        ), use_container_width=True)
    with c7:
        st.plotly_chart(gauge_rev(
            "Hidraulica", state.get("hydraulic_pressure", 0), 0, 200, "PSI",
            warn=100, crit=60,
        ), use_container_width=True)
    with c8:
        st.plotly_chart(gauge(
            "RPM", state.get("engine_rpm", 0), 0, 5000, "",
            steps=[
                {"range": [0, 3000], "color": "#2ecc71"},
                {"range": [3000, 4000], "color": "#f39c12"},
                {"range": [4000, 5000], "color": "#e74c3c"},
            ], threshold=4000,
        ), use_container_width=True)

    st.divider()

    # Row 3 — quick metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Velocidad", f"{state.get('speed_kmh', 0):.0f} km/h")
    m2.metric("Tripulacion", f"{state.get('crew_count', 0)} bomberos")
    ladder = state.get("ladder_status", "retracted")
    angle = state.get("ladder_angle", 0)
    m3.metric("Escalera", ladder.upper(),
              delta=f"{angle:.0f}\u00b0" if ladder == "extended" else None)
    m4.metric("Kilometraje", f"{state.get('mileage_km', 0):,.0f} km")

    m5, m6, m7, m8 = st.columns(4)
    m5.metric("Aceite", f"{state.get('oil_pressure', 0):.1f} PSI")
    m6.metric("Manguera", "DESPLEGADA" if state.get("hose_deployed") else "Recogida")
    m7.metric("Sirenas", "ACTIVAS" if state.get("sirens_active") else "Apagadas")
    m8.metric("Luces", "ACTIVAS" if state.get("lights_active") else "Apagadas")

# ════════════════════════════════════════════════════════════════════════════
#  ALERTAS
# ════════════════════════════════════════════════════════════════════════════

elif page == "Alertas":
    st.header("Alertas y Anomalias")

    active_total = alerts_data.get("count", 0) if alerts_data else 0
    active_list = alerts_data.get("alerts", []) if alerts_data else []
    crit_count = sum(
        1 for a in active_list
        if a.get("severity") in ("emergencia", "critica", "critical")
    )
    tab_labels = [
        f"Activas ({crit_count} criticas / {active_total} total)"
        if active_total else "Activas",
        "Historico",
        "Anomalias",
    ]

    tab_act, tab_hist, tab_anom = st.tabs(tab_labels)

    with tab_act:
        if alerts_data and alerts_data.get("count", 0) > 0:
            mute_col1, mute_col2 = st.columns([1, 3])
            with mute_col1:
                if st.button("Silenciar 5 min"):
                    mute_alerts(5)
                    st.success("Alertas silenciadas durante 5 minutos")
            with mute_col2:
                if alerts_are_muted():
                    st.caption("Alertas silenciadas temporalmente; siguen mostrandose en la lista, pero el contador se marca como silenciado.")

            for idx, a in enumerate(alerts_data["alerts"]):
                sev = a.get("severity", "informativa")
                msg = a.get("message", a.get("metric", "Sin detalle"))
                cat = a.get("category", "alerta")
                aid = a.get("alert_id", "?")
                status = a.get("status", "activa")
                sev_icon = SEVERITY_ICONS.get(sev, "\U0001F535")
                color = SEVERITY_COLORS.get(sev, "#4b5563")

                card_html = f"""
                <div class="alert-card" style="border-left-color:{color};">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <span style="font-size:18px;margin-right:6px;">{sev_icon}</span>
                            <strong>{cat}</strong>
                            <span style="color:{muted_text};font-size:12px;margin-left:4px;">
                                [{status.upper()}]
                            </span>
                        </div>
                        <span style="background:{color}33;color:{color};font-size:11px;
                                     padding:2px 8px;border-radius:999px;text-transform:uppercase;">
                            {sev}
                        </span>
                    </div>
                    <div style="margin-top:4px;font-size:13px;">{msg}</div>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)

                # Botones de accion
                ac1, ac2, ac3, ac4 = st.columns([1, 1, 1, 3])
                with ac1:
                    if st.button("Confirmar", key=f"conf_{aid}_{idx}"):
                        api_post(f"/api/v1/alerts/{VEHICLE_ID}/{aid}/confirm")
                        st.rerun()
                with ac2:
                    if st.button("Escalar", key=f"esc2_{aid}_{idx}"):
                        api_post(f"/api/v1/alerts/{VEHICLE_ID}/{aid}/escalate")
                        st.rerun()
                with ac3:
                    if st.button("Descartar", key=f"dis_{aid}_{idx}"):
                        api_post(f"/api/v1/alerts/{VEHICLE_ID}/{aid}/dismiss")
                        st.rerun()

                with st.expander("Detalles"):
                    st.json(a)
        else:
            st.success("Sin alertas activas")

    with tab_hist:
        hist = api_get(f"/api/v1/alerts/{VEHICLE_ID}/history")
        if hist and hist.get("count", 0) > 0:
            sev_filter = st.multiselect(
                "Filtrar por severidad",
                options=["emergencia", "critica", "advertencia", "informativa"],
                default=["emergencia", "critica", "advertencia", "informativa"],
            )
            for a in hist["alerts"]:
                sev = a.get("severity", "informativa")
                if sev_filter and sev not in sev_filter:
                    continue
                sev_icon = SEVERITY_ICONS.get(sev, "\U0001F535")
                cat = a.get("category", "")
                msg = a.get("message", a.get("metric", ""))
                status = a.get("status", "activa")
                esc_count = a.get("escalation_count", 0)
                extra = f" (escalada x{esc_count})" if esc_count > 0 else ""
                st.markdown(f"{sev_icon} **{cat}** — {msg} `[{status}]{extra}`")
        else:
            st.info("Sin historial de alertas")

    with tab_anom:
        anomalies = api_get(f"/api/v1/anomalies/{VEHICLE_ID}")
        if anomalies:
            risk = anomalies.get("risk_score", 0)
            col_r, col_n = st.columns([1, 3])
            with col_r:
                st.metric("Risk Score", f"{risk:.2f}")
            with col_n:
                if risk > 0.7:
                    st.error("Nivel de riesgo ALTO")
                elif risk > 0.3:
                    st.warning("Nivel de riesgo MEDIO")
                else:
                    st.success("Nivel de riesgo BAJO")

            anom_list = anomalies.get("anomalies", [])
            if anom_list:
                for item in anom_list:
                    if isinstance(item, dict):
                        st.warning(f"Anomalia: {item.get('metric', item)}")
                    else:
                        st.warning(f"Anomalia: {item}")
            else:
                st.success("Sin anomalias detectadas")

# ════════════════════════════════════════════════════════════════════════════
#  TELEMETRIA
# ════════════════════════════════════════════════════════════════════════════

elif page == "Telemetria":
    st.header("Telemetria Historica")

    history_resp = api_get(f"/api/v1/twin/{VEHICLE_ID}/history?limit=400")

    if history_resp and history_resp.get("count", 0) > 5:
        full_data = history_resp["history"]
        full_ticks = list(range(len(full_data)))

        max_tick = len(full_data) - 1
        default_start = max(0, max_tick - 200)
        start_tick, end_tick = st.slider(
            "Rango de tiempo (ticks)",
            0, max_tick,
            (default_start, max_tick),
        )
        data = full_data[start_tick:end_tick + 1]
        ticks = list(range(start_tick, end_tick + 1))

        # Metric selector
        all_metrics = [
            "engine_temp", "water_tank_level", "fuel_level",
            "battery_voltage", "pump_pressure", "hydraulic_pressure",
            "foam_tank_level", "speed_kmh", "engine_rpm", "oil_pressure",
        ]
        selected = st.multiselect(
            "Metricas a visualizar", all_metrics,
            default=["engine_temp", "water_tank_level", "pump_pressure"],
        )

        if selected:
            fig = go.Figure()
            for metric in selected:
                values = [d.get(metric, 0) for d in data]
                nice_name = metric.replace("_", " ").title()
                fig.add_trace(go.Scatter(
                    x=ticks, y=values, name=nice_name,
                    mode="lines",
                ))

            # Umbrales de zona peligrosa
            thresholds = {
                "engine_temp": {"crit": 115, "label": "Motor caliente 115°C"},
                "pump_pressure": {"crit": 30, "label": "Baja presion bomba 30 PSI"},
                "hydraulic_pressure": {"crit": 60, "label": "Baja presion hidraulica 60 PSI"},
                "water_tank_level": {"crit": 10, "label": "Agua <10%"},
                "foam_tank_level": {"crit": 10, "label": "Espuma <10%"},
                "fuel_level": {"crit": 15, "label": "Combustible <15%"},
                "battery_voltage": {"crit": 11.5, "label": "Bateria <11.5V"},
            }
            for metric, info in thresholds.items():
                if metric in selected:
                    fig.add_hline(
                        y=info["crit"],
                        line_dash="dot",
                        line_color=FIRE_RED,
                        annotation_text=info["label"],
                        annotation_position="top left",
                        opacity=0.7,
                    )

            fig.update_layout(
                height=420,
                xaxis_title="Ticks",
                yaxis_title="Valor",
                legend={"orientation": "h", "y": -0.15},
                hovermode="x unified",
            )
            st.plotly_chart(fig, use_container_width=True)

        # Speed + RPM dual axis
        st.subheader("Velocidad y RPM")
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=ticks, y=[d.get("speed_kmh", 0) for d in data],
            name="Velocidad (km/h)", line={"color": "#3498db"},
        ))
        fig2.add_trace(go.Scatter(
            x=ticks, y=[d.get("engine_rpm", 0) for d in data],
            name="RPM", line={"color": "#e74c3c"}, yaxis="y2",
        ))
        fig2.update_layout(
            height=320,
            yaxis={"title": "km/h"},
            yaxis2={"title": "RPM", "overlaying": "y", "side": "right"},
            legend={"orientation": "h", "y": -0.2},
            hovermode="x unified",
        )
        st.plotly_chart(fig2, use_container_width=True)

        # Tanks
        st.subheader("Niveles de Tanques")
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=ticks, y=[d.get("water_tank_level", 0) for d in data],
            name="Agua %", fill="tozeroy",
            line={"color": "#3498db"},
        ))
        fig3.add_trace(go.Scatter(
            x=ticks, y=[d.get("foam_tank_level", 0) for d in data],
            name="Espuma %", fill="tozeroy",
            line={"color": "#9b59b6"},
        ))
        fig3.add_trace(go.Scatter(
            x=ticks, y=[d.get("fuel_level", 0) for d in data],
            name="Combustible %",
            line={"color": "#f39c12", "dash": "dash"},
        ))
        fig3.update_layout(
            height=300,
            yaxis={"title": "%", "range": [0, 105]},
            legend={"orientation": "h", "y": -0.2},
            hovermode="x unified",
        )
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Acumulando datos de telemetria... (se necesitan al menos 5 muestras)")

# ════════════════════════════════════════════════════════════════════════════
#  MAPA
# ════════════════════════════════════════════════════════════════════════════

elif page == "Mapa":
    st.header("Mapa y Cartografia")

    _station = st.session_state.get("station", {})
    _station_lat = _station.get("lat", 39.4699)
    _station_lon = _station.get("lon", -0.3763)
    _station_name = _station.get("name", "Estacion Base")
    lat = state.get("latitude", _station_lat)
    lon = state.get("longitude", _station_lon)
    speed = state.get("speed_kmh", 0)
    mission = state.get("mission_status", "disponible")

    # Sidebar layer controls
    with st.sidebar:
        st.markdown("### Capas del mapa")
        show_route = st.checkbox("Ruta activa", value=True)
        show_compare = st.checkbox("Comparar rutas (directa vs optima)", value=True)
        show_traffic = st.checkbox("Trafico", value=True)
        show_hydrants = st.checkbox("Hidrantes", value=True)
        show_stations = st.checkbox("Estaciones de bomberos", value=True)
        show_trail = st.checkbox("Recorrido historico", value=False)

    color_map = {
        "disponible": "green",
        "en_ruta": "blue",
        "en_escena": "red",
        "regreso_base": "orange",
    }
    color = color_map.get(mission, "gray")

    if "map_zoom" not in st.session_state:
        st.session_state["map_zoom"] = 14

    ctrl1, ctrl2, ctrl3 = st.columns(3)
    with ctrl1:
        if st.button("Centrar en el vehiculo"):
            st.session_state["map_zoom"] = 15
            st.rerun()
    with ctrl2:
        if st.button("Vista ciudad"):
            st.session_state["map_zoom"] = 12
            st.rerun()
    with ctrl3:
        st.caption("Ajusta la vista del mapa para la mision.")

    m = folium.Map(location=[lat, lon], zoom_start=st.session_state["map_zoom"])

    # Vehicle marker
    folium.Marker(
        [lat, lon],
        popup=f"BOM-001 | {mission} | {speed:.0f} km/h",
        tooltip="BOM-001 — " + mission.replace("_", " ").upper(),
        icon=folium.Icon(color=color, icon="fire-extinguisher", prefix="fa"),
    ).add_to(m)

    # Base station
    folium.Marker(
        [_station_lat, _station_lon],
        popup=f"Estacion Base — {_station_name}",
        tooltip="Base",
        icon=folium.Icon(color="darkred", icon="home", prefix="fa"),
    ).add_to(m)

    # Traffic zones layer
    _current_city = st.session_state.get("city", "Valencia")
    traffic_data = api_get(f"/api/v1/geo/traffic/zones?city={_current_city}") if show_traffic else None
    if traffic_data:
        for z in traffic_data.get("zones", []):
            cf = z.get("congestion_factor", 1.0)
            # Color: verde (fluido) → amarillo → naranja → rojo (congestionado)
            if cf < 1.15:
                tc = "#2ecc71"  # verde
            elif cf < 1.35:
                tc = "#f1c40f"  # amarillo
            elif cf < 1.55:
                tc = "#e67e22"  # naranja
            else:
                tc = "#e74c3c"  # rojo
            folium.CircleMarker(
                [z["lat"], z["lon"]],
                radius=z.get("radius", 150) / 10,
                color=tc,
                fill=True,
                fill_color=tc,
                fill_opacity=0.25,
                weight=1,
                popup=f"{z['name']}: {z['description']} ({cf:.2f}x)",
                tooltip=f"{z['name']}: {z['description']}",
            ).add_to(m)

    # Active route from geo API
    route_data = api_get(f"/api/v1/geo/{VEHICLE_ID}/route")
    if show_route and route_data and route_data.get("active"):
        route_coords = route_data.get("coords", [])
        direct_coords = route_data.get("direct_coords", [])

        # Ruta directa (gris, discontinua) — si hay comparación
        if show_compare and len(direct_coords) > 1:
            folium.PolyLine(
                direct_coords, color="#888888", weight=4, opacity=0.6,
                dash_array="10 8",
                popup="Ruta directa (mas corta por distancia)",
                tooltip="Ruta directa",
            ).add_to(m)

        # Ruta óptima (coloreada según congestión)
        if len(route_coords) > 1:
            congestion = (traffic_data or {}).get("global_factor", 1.0)
            if congestion < 1.15:
                route_color = "#2ecc71"  # verde
            elif congestion < 1.35:
                route_color = "#3498db"  # azul
            elif congestion < 1.55:
                route_color = "#e67e22"  # naranja
            else:
                route_color = "#e74c3c"  # rojo

            folium.PolyLine(
                route_coords, color=route_color, weight=5, opacity=0.85,
                popup="Ruta optima (evita trafico)",
                tooltip="Ruta optima",
            ).add_to(m)

            # Destination marker (last coord)
            dest = route_coords[-1]
            dest_name = route_data.get("destination", "Destino")
            folium.Marker(
                dest,
                popup=f"Destino: {dest_name}",
                tooltip=dest_name,
                icon=folium.Icon(color="orange", icon="fire", prefix="fa"),
            ).add_to(m)

        # Leyenda del mapa
        if show_compare and len(direct_coords) > 1 and len(route_coords) > 1:
            legend_html = f"""
            <div style="position: fixed; bottom: 30px; left: 50px; z-index: 1000;
                        background: rgba(15,23,42,0.92); padding: 10px 16px;
                        border-radius: 10px; font-size: 13px; color: #f9fafb;
                        font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                        box-shadow: 0 10px 30px rgba(15,23,42,0.85);">
                <b>Leyenda del mapa</b><br>
                <span style="color: #888; font-size: 14px; font-weight:bold;">- - - -</span>
                &nbsp;Ruta directa (distancia)<br>
                <span style="color: {route_color}; font-size: 14px; font-weight:bold;">━━━</span>
                &nbsp;Ruta optima (evita trafico)<br>
                <span style="color: #2ecc71;">●</span> Trafico fluido &nbsp;
                <span style="color: #f1c40f;">●</span> Trafico medio &nbsp;
                <span style="color: #e67e22;">●</span> Trafico denso &nbsp;
                <span style="color: #e74c3c;">●</span> Trafico critico<br>
                <span style="color: #3498db;">●</span> Hidrantes &nbsp;
                <span style="color: #ff0000;">■</span> Estaciones de bomberos
            </div>
            """
            m.get_root().html.add_child(folium.Element(legend_html))

    # Hydrants layer
    if show_hydrants:
        hydrants_resp = api_get(f"/api/v1/geo/poi/hydrants?city={_current_city}")
        if hydrants_resp:
            for h in hydrants_resp.get("hydrants", []):
                folium.CircleMarker(
                    [h["lat"], h["lon"]],
                    radius=5,
                    color="#3498db",
                    fill=True,
                    fill_color="#3498db",
                    fill_opacity=0.7,
                    popup=h.get("name", h.get("id", "Hidrante")),
                    tooltip=h.get("id", "H"),
                ).add_to(m)

    # Fire stations layer
    if show_stations:
        stations_resp = api_get(f"/api/v1/geo/poi/stations?city={_current_city}")
        if stations_resp:
            for s in stations_resp.get("stations", []):
                folium.Marker(
                    [s["lat"], s["lon"]],
                    popup=f"{s['name']} — {s.get('address', '')}",
                    tooltip=s["name"],
                    icon=folium.Icon(color="red", icon="building", prefix="fa"),
                ).add_to(m)

    # Trail from history
    if show_trail:
        trail_resp = api_get(f"/api/v1/twin/{VEHICLE_ID}/history?limit=60")
        if trail_resp and trail_resp.get("count", 0) > 1:
            trail = [
                [d.get("latitude", lat), d.get("longitude", lon)]
                for d in trail_resp["history"]
                if d.get("speed_kmh", 0) > 0
            ]
            if len(trail) > 1:
                folium.PolyLine(trail, color=color, weight=3, opacity=0.5).add_to(m)

    st_folium(m, width=None, height=550, returned_objects=[])

    # Metrics below map
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Latitud", f"{lat:.6f}")
    mc2.metric("Longitud", f"{lon:.6f}")
    mc3.metric("Velocidad", f"{speed:.0f} km/h")

    # Traffic — siempre visible
    traffic_resp = api_get("/api/v1/geo/traffic/current")
    if traffic_resp:
        factor = traffic_resp.get("congestion_factor", 1.0)
        desc = traffic_resp.get("description", "")
        mc4.metric("Trafico", desc.upper(), delta=f"{factor:.2f}x", delta_color="off")
    else:
        mc4.metric("Rumbo", f"{state.get('heading', 0):.0f}\u00b0")

    # Route info (ETA, progress, distance)
    on_route = state.get("on_route", False)
    if on_route:
        st.divider()
        st.subheader("Ruta Activa")

        progress = state.get("route_progress", 0)
        eta = state.get("eta_seconds", 0)
        dist_rem = state.get("distance_remaining_m", 0)

        rc1, rc2, rc3 = st.columns(3)
        rc1.metric("Progreso", f"{progress:.0%}")
        eta_min = int(eta // 60)
        eta_sec = int(eta % 60)
        rc2.metric("ETA", f"{eta_min}m {eta_sec}s")
        if dist_rem > 1000:
            rc3.metric("Distancia restante", f"{dist_rem / 1000:.1f} km")
        else:
            rc3.metric("Distancia restante", f"{dist_rem:.0f} m")

        st.progress(min(progress, 1.0))

        # Comparación de rutas (directa vs óptima)
        if route_data and route_data.get("active"):
            opt_dist = route_data.get("total_distance_m", 0)
            dir_dist = route_data.get("direct_distance_m", 0)
            if dir_dist > 0 and opt_dist > 0 and dir_dist != opt_dist:
                st.divider()
                st.subheader("Comparacion: Directa vs Optima")
                cc1, cc2, cc3 = st.columns(3)
                if dir_dist > 1000:
                    cc1.metric("Ruta directa", f"{dir_dist / 1000:.1f} km")
                else:
                    cc1.metric("Ruta directa", f"{dir_dist:.0f} m")
                if opt_dist > 1000:
                    cc2.metric("Ruta optima", f"{opt_dist / 1000:.1f} km")
                else:
                    cc2.metric("Ruta optima", f"{opt_dist:.0f} m")

                # La ruta óptima puede ser más larga en distancia pero más rápida
                cong = route_data.get("congestion_factor", 1.0)
                avg_speed_ms = 50 / 3.6  # 50 km/h promedio
                time_direct = dir_dist / avg_speed_ms * cong
                time_optima = opt_dist / avg_speed_ms
                saved = time_direct - time_optima
                if saved > 0:
                    cc3.metric(
                        "Tiempo ahorrado",
                        f"{int(saved)}s",
                        delta=f"{saved / time_direct:.0%} mas rapida",
                        delta_color="normal",
                    )
                else:
                    cc3.metric(
                        "Diferencia",
                        f"{abs(int(saved))}s",
                        delta="misma velocidad",
                        delta_color="off",
                    )

    # Vista de ecosistema / otros vehiculos
    st.divider()
    st.subheader("Ecosistema de Vehiculos")
    eco = api_get("/api/v1/ecosystem/status")
    if eco and eco.get("twins"):
        for twin in eco["twins"]:
            cols = st.columns([1, 2, 2, 2])
            with cols[0]:
                st.markdown(f"**{twin.get('twin_id')}**")
            with cols[1]:
                st.caption(twin.get("type", ""))
            with cols[2]:
                st.caption(f"Estado: {twin.get('status', 'unknown')}")
            with cols[3]:
                st.caption(f"Mision: {twin.get('mission_status', 'unknown')}")
    else:
        st.caption("Sin informacion de ecosistema disponible")

# ════════════════════════════════════════════════════════════════════════════
#  SIMULACION
# ════════════════════════════════════════════════════════════════════════════

elif page == "Simulacion":
    st.header("Escenarios What-If")

    scenarios_resp = api_get("/api/v1/simulate/scenarios")

    if scenarios_resp:
        # list_scenarios returns {name: description}
        scenario_dict = scenarios_resp.get("scenarios", {})

        if scenario_dict:
            names = list(scenario_dict.keys())
            selected = st.selectbox(
                "Seleccionar escenario", names,
                format_func=lambda x: SCENARIO_LABELS.get(x, x.replace("_", " ").title()),
            )
            st.info(f"**Descripcion:** {scenario_dict[selected]}")

            col_run, col_repeat = st.columns(2)
            with col_run:
                run_clicked = st.button("Ejecutar Escenario", type="primary")
            with col_repeat:
                repeat_clicked = st.button("Repetir ultimo", type="secondary")

            if run_clicked:
                with st.spinner("Ejecutando simulacion..."):
                    result = api_post("/api/v1/simulate/scenario", {"scenario": selected})
                st.session_state["last_scenario"] = selected
                st.session_state["sim_result"] = result

            elif repeat_clicked:
                last = st.session_state.get("last_scenario")
                if not last:
                    st.info("Aun no se ha ejecutado ningun escenario")
                else:
                    with st.spinner(f"Repitiendo {SCENARIO_LABELS.get(last, last)}..."):
                        result = api_post("/api/v1/simulate/scenario", {"scenario": last})
                    st.session_state["sim_result"] = result

            result = st.session_state.get("sim_result")

            if result is not None:
                if result and "error" not in result:
                    st.success("Simulacion completada")

                    # Summary
                    summary = result.get("summary", {})
                    if summary:
                        st.subheader("Resumen")
                        scols = st.columns(len(summary))
                        for i, (k, v) in enumerate(summary.items()):
                            scols[i].metric(k.replace("_", " ").title(), str(v))

                    # Simulation steps (pump / ladder scenarios)
                    sim_steps = result.get("simulation_steps", [])
                    if sim_steps:
                        st.subheader("Pasos de Simulacion")

                        # Chart: pressure over ticks
                        pressure_key = None
                        for key in ("pump_pressure", "hydraulic_pressure"):
                            if key in sim_steps[0]:
                                pressure_key = key
                                break

                        if pressure_key:
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(
                                x=[s["tick"] for s in sim_steps],
                                y=[s[pressure_key] for s in sim_steps],
                                name=pressure_key.replace("_", " ").title(),
                                mode="lines+markers",
                                line={"color": "#e74c3c"},
                            ))
                            if "water_tank_level" in sim_steps[0]:
                                fig.add_trace(go.Scatter(
                                    x=[s["tick"] for s in sim_steps],
                                    y=[s["water_tank_level"] for s in sim_steps],
                                    name="Nivel de Agua %",
                                    mode="lines",
                                    line={"color": "#3498db"},
                                    yaxis="y2",
                                ))
                                fig.update_layout(
                                    yaxis2={"title": "Agua %", "overlaying": "y", "side": "right"},
                                )
                            fig.update_layout(
                                height=350,
                                xaxis_title="Tick",
                                yaxis_title="PSI",
                                hovermode="x unified",
                            )
                            st.plotly_chart(fig, use_container_width=True)

                        # Alerts and decisions from steps
                        all_decisions = []
                        for step in sim_steps:
                            for d in step.get("decisions", []):
                                if d not in all_decisions:
                                    all_decisions.append(d)
                        if all_decisions:
                            st.subheader("Decisiones del Asistente")
                            for d in all_decisions:
                                st.warning(f"\u26A0\uFE0F {d}")

                    # Multi-fire result
                    sim_result = result.get("simulation_result", {})
                    if sim_result:
                        st.subheader("Detalle de Incendios")
                        fires = sim_result.get("fires", [])
                        for f in fires:
                            st.markdown(
                                f"**Fuego #{f['fire_id']}** — {f['severity']} "
                                f"({f['estimated_units_needed']} unidades necesarias)"
                            )
                        deficit = sim_result.get("deficit", 0)
                        if deficit > 0:
                            st.error(f"Deficit de {deficit} unidades")
                        decisions = sim_result.get("decisions", [])
                        if decisions:
                            st.subheader("Decisiones")
                            for d in decisions:
                                st.warning(f"\u26A0\uFE0F {d}")

                    # Vista comparativa antes/despues (primeros vs ultimos ticks)
                    if sim_steps:
                        st.subheader("Antes vs Despues")
                        n = max(3, min(10, len(sim_steps) // 4))
                        start_window = sim_steps[:n]
                        end_window = sim_steps[-n:]
                        avg_speed_before = sum(s.get("speed_kmh", 0) for s in start_window) / n
                        avg_speed_after = sum(s.get("speed_kmh", 0) for s in end_window) / n
                        before_col, after_col = st.columns(2)
                        with before_col:
                            st.metric("Velocidad media (inicio)", f"{avg_speed_before:.1f} km/h")
                        with after_col:
                            st.metric("Velocidad media (fin)", f"{avg_speed_after:.1f} km/h")

                    with st.expander("JSON completo"):
                        st.json(result)
                else:
                    st.error("Error ejecutando escenario")
                    if result:
                        st.json(result)
        else:
            st.warning("No hay escenarios disponibles")
    else:
        st.error("No se pueden cargar los escenarios desde la API")

# ════════════════════════════════════════════════════════════════════════════
#  PREDICCIONES
# ════════════════════════════════════════════════════════════════════════════

elif page == "Predicciones":
    st.header("Prediccion de Fallos y Mantenimiento")

    tab_fail, tab_maint = st.tabs(["Prediccion de Fallos", "Mantenimiento Preventivo"])

    with tab_fail:
        preds = api_get(f"/api/v1/predict/{VEHICLE_ID}/failures")
        if preds:
            st.caption(
                f"Horizonte: {preds.get('horizon', 'N/A')} | "
                f"Puntos de datos: {preds.get('data_points', 0)}"
            )
            pred_list = preds.get("predictions", [])
            if pred_list:
                for p in pred_list:
                    comp = p.get("component", "N/A").replace("_", " ").title()
                    prob = p.get("probability", 0)
                    trend = p.get("trend", "stable")
                    ticks_left = p.get("ticks_to_failure", "N/A")

                    pc1, pc2, pc3, pc4 = st.columns([3, 1, 1, 1])
                    with pc1:
                        st.markdown(f"**{comp}**")
                    with pc2:
                        if prob > 0.7:
                            st.error(f"{prob:.0%}")
                        elif prob > 0.3:
                            st.warning(f"{prob:.0%}")
                        else:
                            st.success(f"{prob:.0%}")
                    with pc3:
                        st.caption(f"Tendencia: {trend}")
                    with pc4:
                        st.caption(f"Ticks: {ticks_left}")
                    st.divider()
            else:
                st.success("Sin predicciones de fallo inminente")
        else:
            st.info("Acumulando datos para predicciones...")

    with tab_maint:
        maint = api_get(f"/api/v1/predict/{VEHICLE_ID}/maintenance")
        if maint:
            km = maint.get("mileage_km", 0)
            st.caption(f"Kilometraje actual: {km:,.0f} km")

            recs = maint.get("recommendations", [])
            if recs:
                for r in recs:
                    urgency = r.get("urgency", "baja")
                    comp = r.get("component", "N/A").upper()
                    action = r.get("action", "N/A")
                    current = r.get("current_value", "N/A")
                    threshold = r.get("threshold", "N/A")

                    if urgency == "alta":
                        st.error(f"**{comp}** — {action}")
                    elif urgency == "media":
                        st.warning(f"**{comp}** — {action}")
                    else:
                        st.info(f"**{comp}** — {action}")
                    st.caption(f"Actual: {current} | Umbral: {threshold}")
            else:
                st.success("Sin recomendaciones de mantenimiento pendientes")
        else:
            st.info("Sin datos de mantenimiento")

# ════════════════════════════════════════════════════════════════════════════
#  IA AVANZADA
# ════════════════════════════════════════════════════════════════════════════

elif page == "IA Avanzada":
    st.header("IA Avanzada")

    tab_risk, tab_resources, tab_fleet = st.tabs([
        "Mapa de Riesgo",
        "Estimador de Recursos",
        "Optimizacion de Flota",
    ])

    # ── Tab 1: Mapa de Riesgo ──────────────────────────────────────────
    with tab_risk:
        st.subheader("Zonas de Riesgo por Hora")
        risk_hour = st.slider("Hora del dia", 0, 23, 14, key="risk_hour")
        risk_vehicles = st.slider("Vehiculos a posicionar", 1, 6, 3, key="risk_vehicles")

        risk_data = api_get(f"/api/v1/ai/{VEHICLE_ID}/risk-zones?hour={risk_hour}")
        deploy_data = api_get(f"/api/v1/ai/{VEHICLE_ID}/deployment?hour={risk_hour}&vehicles={risk_vehicles}")

        if risk_data and risk_data.get("risk_zones"):
            zones = risk_data["risk_zones"]

            # Metricas
            rm1, rm2, rm3 = st.columns(3)
            rm1.metric("Zonas detectadas", len(zones))
            rm2.metric("Metodo", risk_data.get("method", "?"))
            max_risk = max(z["risk"] for z in zones) if zones else 0
            rm3.metric("Riesgo maximo", f"{max_risk:.0%}")

            # Mapa Folium
            _risk_station = st.session_state.get("station", {})
            m_risk = folium.Map(
                location=[_risk_station.get("lat", 39.4699), _risk_station.get("lon", -0.3763)],
                zoom_start=12,
            )

            # Circulos de riesgo
            for z in zones:
                risk_val = z.get("risk", 0)
                if risk_val > 0.6:
                    color = "#e74c3c"
                elif risk_val > 0.3:
                    color = "#f39c12"
                else:
                    color = "#2ecc71"

                folium.CircleMarker(
                    [z["lat"], z["lon"]],
                    radius=int(risk_val * 25) + 5,
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.35,
                    weight=2,
                    popup=f"{z['zone_name']}: riesgo {risk_val:.0%}",
                    tooltip=f"{z['zone_name']} ({risk_val:.0%})",
                ).add_to(m_risk)

            # Markers de posiciones recomendadas
            if deploy_data and deploy_data.get("positions"):
                for pos in deploy_data["positions"]:
                    folium.Marker(
                        [pos["lat"], pos["lon"]],
                        popup=f"Vehiculo {pos['vehicle_slot']}: {pos['zone_name']} (prioridad: {pos['priority']})",
                        tooltip=f"V{pos['vehicle_slot']} - {pos['zone_name']}",
                        icon=folium.Icon(color="blue", icon="truck", prefix="fa"),
                    ).add_to(m_risk)

            st_folium(m_risk, width=None, height=500, returned_objects=[])

            # Tabla de zonas
            with st.expander("Detalle de zonas de riesgo"):
                for z in zones:
                    risk_val = z.get("risk", 0)
                    if risk_val > 0.6:
                        st.error(f"**{z['zone_name']}** — Riesgo: {risk_val:.0%}")
                    elif risk_val > 0.3:
                        st.warning(f"**{z['zone_name']}** — Riesgo: {risk_val:.0%}")
                    else:
                        st.info(f"**{z['zone_name']}** — Riesgo: {risk_val:.0%}")
        else:
            st.info("Sin datos de riesgo disponibles")

    # ── Tab 2: Estimador de Recursos ───────────────────────────────────
    with tab_resources:
        st.subheader("Estimacion de Recursos por Incidente")

        types_data = api_get(f"/api/v1/ai/{VEHICLE_ID}/estimate-resources/types")
        if types_data:
            type_list = types_data.get("types", [])
            type_names = [t["type"] for t in type_list]
            type_descriptions = {t["type"]: t["description"] for t in type_list}

            rc1, rc2, rc3 = st.columns(3)
            with rc1:
                selected_type = st.selectbox(
                    "Tipo de incidente", type_names,
                    format_func=lambda x: x.replace("_", " ").title(),
                )
            with rc2:
                selected_severity = st.selectbox("Severidad", ["baja", "media", "alta"], index=1)
            with rc3:
                selected_area = st.number_input("Area afectada (m2)", min_value=10, max_value=10000, value=200)

            st.caption(type_descriptions.get(selected_type, ""))

            if st.button("Estimar Recursos", type="primary"):
                est_result = api_post(f"/api/v1/ai/{VEHICLE_ID}/estimate-resources", {
                    "type": selected_type,
                    "severity": selected_severity,
                    "area_m2": selected_area,
                })

                if est_result and "resources" in est_result:
                    res = est_result["resources"]
                    st.success(f"Estimacion completada (metodo: {est_result.get('method', '?')})")

                    ec1, ec2, ec3, ec4, ec5 = st.columns(5)
                    ec1.metric("Bomberos", res.get("bomberos", 0))
                    ec2.metric("Agua (L)", f"{res.get('agua_litros', 0):,}")
                    ec3.metric("Espuma (L)", f"{res.get('espuma_litros', 0):,}")
                    ec4.metric("Vehiculos", res.get("vehiculos", 0))
                    ec5.metric("Tiempo (min)", res.get("tiempo_min", 0))

                    with st.expander("JSON completo"):
                        st.json(est_result)
                elif est_result and "error" in est_result:
                    st.error(est_result["error"])
                else:
                    st.error("Error en la estimacion")
        else:
            st.error("No se pueden cargar tipos de incidente")

    # ── Tab 3: Optimizacion de Flota ───────────────────────────────────
    with tab_fleet:
        st.subheader("Optimizacion de Asignaciones")

        fc1, fc2 = st.columns(2)

        with fc1:
            st.markdown("#### Asignacion Optima")
            opt_result = api_get("/api/v1/ai/fleet/optimize")
            if opt_result and opt_result.get("assignments"):
                assignments = opt_result["assignments"]

                # Metricas resumen
                om1, om2, om3 = st.columns(3)
                om1.metric("Asignaciones", opt_result.get("total_assignments", 0))
                om2.metric("Distancia total", f"{opt_result.get('total_distance_km', 0):.1f} km")
                om3.metric("ETA promedio", f"{opt_result.get('avg_eta_min', 0):.1f} min")

                st.caption(f"Metodo: {opt_result.get('method', '?')}")

                # Tabla de asignaciones
                for a in assignments:
                    priority = a.get("priority", "media")
                    if priority == "alta":
                        st.error(
                            f"**{a['vehicle_id']}** ({a['vehicle_type']}) "
                            f"-> {a['emergency_id']} | "
                            f"{a['distance_km']} km | ETA: {a['eta_min']} min"
                        )
                    else:
                        st.warning(
                            f"**{a['vehicle_id']}** ({a['vehicle_type']}) "
                            f"-> {a['emergency_id']} | "
                            f"{a['distance_km']} km | ETA: {a['eta_min']} min"
                        )
            else:
                st.info("Sin asignaciones pendientes")

        with fc2:
            st.markdown("#### Cobertura de Flota")
            cov_result = api_get("/api/v1/ai/fleet/coverage")
            if cov_result:
                score = cov_result.get("score", 0)

                # Score grande
                if score >= 0.8:
                    st.success(f"Score de cobertura: **{score:.0%}**")
                elif score >= 0.5:
                    st.warning(f"Score de cobertura: **{score:.0%}**")
                else:
                    st.error(f"Score de cobertura: **{score:.0%}**")

                cm1, cm2 = st.columns(2)
                cm1.metric("Zonas cubiertas", f"{cov_result.get('covered_zones', 0)}/{cov_result.get('total_zones', 0)}")
                cm2.metric("Radio cobertura", f"{cov_result.get('coverage_radius_km', 3)} km")

                # Detalle por zona
                details = cov_result.get("details", [])
                if details:
                    for d in details:
                        status = "Cubierta" if d["covered"] else "Sin cobertura"
                        icon = "OK" if d["covered"] else "!!"
                        st.markdown(
                            f"[{icon}] **{d['zone_name']}** — "
                            f"Vehiculo mas cercano: {d['nearest_vehicle']} "
                            f"({d['distance_km']} km) — {status}"
                        )
            else:
                st.info("Sin datos de cobertura")

# ── Footer ──────────────────────────────────────────────────────────────────

st.divider()
st.caption(f"Gemelo Digital BOM-001 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
