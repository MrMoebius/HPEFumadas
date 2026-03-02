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
        background: rgba(28, 131, 225, 0.1);
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
        icon = icons.get(mission, "\u26AA")
        label = mission.replace("_", " ").upper()
        st.info(f"{icon} Mision: **{label}**")
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

    # Force emergency button
    if state and state.get("mission_status") == "disponible":
        if st.button("SIMULAR EMERGENCIA", type="primary"):
            resp = api_post("/api/v1/geo/force-emergency", {})
            if resp and resp.get("status") == "ok":
                st.success("Emergencia enviada!")
                import time as _t
                _t.sleep(1)
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

# Auto-refresh (desactivado en Mapa para no reiniciar la vista)
if auto and page != "Mapa":
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
    st.header("Mapa y Cartografia")

    lat = state.get("latitude", 39.4699)
    lon = state.get("longitude", -0.3763)
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

    m = folium.Map(location=[lat, lon], zoom_start=14)

    # Vehicle marker
    folium.Marker(
        [lat, lon],
        popup=f"BOM-001 | {mission} | {speed:.0f} km/h",
        tooltip="BOM-001 — " + mission.replace("_", " ").upper(),
        icon=folium.Icon(color=color, icon="fire-extinguisher", prefix="fa"),
    ).add_to(m)

    # Base station
    folium.Marker(
        [39.4699, -0.3763],
        popup="Estacion Base — Bomberos Valencia",
        tooltip="Base",
        icon=folium.Icon(color="darkred", icon="home", prefix="fa"),
    ).add_to(m)

    # Traffic zones layer
    traffic_data = api_get("/api/v1/geo/traffic/zones") if show_traffic else None
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
            legend_html = """
            <div style="position: fixed; bottom: 30px; left: 50px; z-index: 1000;
                        background: rgba(0,0,0,0.75); padding: 10px 14px;
                        border-radius: 8px; font-size: 13px; color: white;
                        font-family: sans-serif;">
                <b>Comparacion de rutas</b><br>
                <span style="color: #888; font-size: 16px;">- - -</span>
                &nbsp;Ruta directa (distancia)<br>
                <span style="color: {rc}; font-size: 16px;">___</span>
                &nbsp;Ruta optima (evita trafico)
            </div>
            """.replace("{rc}", route_color)
            m.get_root().html.add_child(folium.Element(legend_html))

    # Hydrants layer
    if show_hydrants:
        hydrants_resp = api_get("/api/v1/geo/poi/hydrants")
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
        stations_resp = api_get("/api/v1/geo/poi/stations")
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
