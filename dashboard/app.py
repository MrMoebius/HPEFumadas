"""Dashboard del Gemelo Digital — Camion de Bomberos BOM-001."""

import os
import requests
import plotly.graph_objects as go
import folium
import streamlit as st
from streamlit_folium import st_folium
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

# ── Config ──────────────────────────────────────────────────────────────────

API_URL = os.getenv("API_URL", "http://localhost:8002")
VEHICLE_ID = os.getenv("VEHICLE_ID", "BOM-001")

st.set_page_config(
    page_title=f"Gemelo Digital — {VEHICLE_ID}",
    page_icon="\U0001F692",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ─────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    [data-testid="stMetric"] {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 12px 16px;
        border-left: 4px solid #3498db;
    }
    .block-container { padding-top: 1.5rem; }
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


def api_post(path: str, body: dict):
    try:
        r = requests.post(f"{API_URL}{path}", json=body, timeout=10)
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


# ── Fetch core data ────────────────────────────────────────────────────────

state = api_get(f"/api/v1/twin/{VEHICLE_ID}/state")
health = api_get(f"/api/v1/twin/{VEHICLE_ID}/health")
alerts_data = api_get(f"/api/v1/alerts/{VEHICLE_ID}")

# ── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## \U0001F692 BOM-001")
    st.caption("Gemelo Digital — Camion de Bomberos")
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
        st.info(f"{icons.get(mission, '\u26AA')} Mision: **{mission.replace('_', ' ').upper()}**")
        st.caption(f"Tick #{state.get('tick', '?')} | {state.get('timestamp', '')}")

    st.divider()

    # Alert count
    if alerts_data and alerts_data.get("count", 0) > 0:
        st.error(f"\U0001F514 {alerts_data['count']} alerta(s) activa(s)")

    # Navigation
    page = st.radio("Navegacion", [
        "Estado en Tiempo Real",
        "Alertas",
        "Telemetria",
        "Mapa",
        "Simulacion",
        "Predicciones",
    ], label_visibility="collapsed")

    st.divider()

    # Auto-refresh toggle
    auto = st.checkbox("Auto-refresh (5s)", value=True)
    if st.button("Actualizar ahora"):
        st.rerun()

# Auto-refresh
if auto:
    st_autorefresh(interval=5000, key="auto_refresh")

# ── Guard ───────────────────────────────────────────────────────────────────

if not state:
    st.warning("Esperando datos de telemetria del vehiculo...")
    st.info(f"API: {API_URL}")
    st.stop()

# ════════════════════════════════════════════════════════════════════════════
#  ESTADO EN TIEMPO REAL
# ════════════════════════════════════════════════════════════════════════════

if page == "Estado en Tiempo Real":
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

    tab_act, tab_hist, tab_anom = st.tabs(["Activas", "Historico", "Anomalias"])

    with tab_act:
        if alerts_data and alerts_data.get("count", 0) > 0:
            for a in alerts_data["alerts"]:
                sev = a.get("severity", "info")
                msg = a.get("message", a.get("metric", "Sin detalle"))
                cat = a.get("category", "alerta")
                if sev == "critical":
                    st.error(f"**{cat}** — {msg}")
                elif sev == "warning":
                    st.warning(f"**{cat}** — {msg}")
                else:
                    st.info(f"**{cat}** — {msg}")
                with st.expander("Detalles"):
                    st.json(a)
        else:
            st.success("Sin alertas activas")

    with tab_hist:
        hist = api_get(f"/api/v1/alerts/{VEHICLE_ID}/history")
        if hist and hist.get("count", 0) > 0:
            for a in hist["alerts"]:
                sev = a.get("severity", "info")
                icon = "\U0001F534" if sev == "critical" else "\U0001F7E1" if sev == "warning" else "\U0001F535"
                cat = a.get("category", "")
                msg = a.get("message", a.get("metric", ""))
                st.markdown(f"{icon} **{cat}** — {msg}")
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

    history_resp = api_get(f"/api/v1/twin/{VEHICLE_ID}/history?limit=200")

    if history_resp and history_resp.get("count", 0) > 5:
        data = history_resp["history"]
        ticks = list(range(len(data)))

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
                fig.add_trace(go.Scatter(
                    x=ticks, y=values, name=metric.replace("_", " ").title(),
                    mode="lines",
                ))
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
    st.header("Posicion del Vehiculo")

    lat = state.get("latitude", 39.4699)
    lon = state.get("longitude", -0.3763)
    speed = state.get("speed_kmh", 0)
    mission = state.get("mission_status", "disponible")

    color_map = {
        "disponible": "green",
        "en_ruta": "blue",
        "en_escena": "red",
        "regreso_base": "orange",
    }
    color = color_map.get(mission, "gray")

    m = folium.Map(location=[lat, lon], zoom_start=14)

    # Vehicle marker
    folium.Marker(
        [lat, lon],
        popup=f"BOM-001 | {mission} | {speed:.0f} km/h",
        tooltip=f"BOM-001 — {mission.replace('_', ' ').upper()}",
        icon=folium.Icon(color=color, icon="fire-extinguisher", prefix="fa"),
    ).add_to(m)

    # Base station
    folium.Marker(
        [39.4699, -0.3763],
        popup="Estacion Base — Bomberos Valencia",
        tooltip="Base",
        icon=folium.Icon(color="darkred", icon="home", prefix="fa"),
    ).add_to(m)

    # Trail from history
    trail_resp = api_get(f"/api/v1/twin/{VEHICLE_ID}/history?limit=60")
    if trail_resp and trail_resp.get("count", 0) > 1:
        trail = [
            [d.get("latitude", lat), d.get("longitude", lon)]
            for d in trail_resp["history"]
            if d.get("speed_kmh", 0) > 0
        ]
        if len(trail) > 1:
            folium.PolyLine(trail, color=color, weight=3, opacity=0.7).add_to(m)

    st_folium(m, width=None, height=500)

    # Info below map
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Latitud", f"{lat:.6f}")
    mc2.metric("Longitud", f"{lon:.6f}")
    mc3.metric("Velocidad", f"{speed:.0f} km/h")
    mc4.metric("Rumbo", f"{state.get('heading', 0):.0f}\u00b0")

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
                format_func=lambda x: x.replace("_", " ").title(),
            )
            st.info(f"**Descripcion:** {scenario_dict[selected]}")

            if st.button("Ejecutar Escenario", type="primary"):
                with st.spinner("Ejecutando simulacion..."):
                    result = api_post("/api/v1/simulate/scenario", {"scenario": selected})

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

# ── Footer ──────────────────────────────────────────────────────────────────

st.divider()
st.caption(f"Gemelo Digital BOM-001 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
