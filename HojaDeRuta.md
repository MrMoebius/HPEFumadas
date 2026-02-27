# Hoja de Ruta — Delegación de Trabajos

**Deadline: 8 de marzo de 2026**
**Días disponibles: 9 (27 feb → 8 mar)**

## Visión General

Desarrollo del Gemelo Digital del Camión de Bomberos, desplegado en Raspberry Pi 5 con Docker Compose. Plan comprimido a 9 días con trabajo en paralelo agresivo entre miembros del equipo.

---

## Calendario Día a Día

```
         27 feb   28 feb   1 mar   2 mar   3 mar   4 mar   5 mar   6 mar   7 mar   8 MAR
          Jue      Vie      Sáb     Dom     Lun     Mar     Mié     Jue     Vie     ENTREGA
         ─────   ─────    ─────   ─────   ─────   ─────   ─────   ─────   ─────   ─────────

BLOQUE 1  ████████████████
(Infra)   Día 1-2

BLOQUE 2       ██████████████████
(Simul.)       Día 2-4

BLOQUE 3            ██████████████████████████
(Motor+IA)          Día 3-6

BLOQUE 4                 ██████████████████████████
(API)                    Día 4-7

BLOQUE 5                           ██████████████████████████
(Dashboard)                        Día 5-8

INTEGR.                                               █████████████
                                                       Día 7-8

DEMO                                                          ██████
                                                               Día 9
```

---

## Bloques de Trabajo

### BLOQUE 1: Infraestructura y DevOps
**Responsable:** _por asignar_
**Plazo:** Días 1-2 (27-28 feb)
**Prioridad:** URGENTE (bloquea todo)

| # | Tarea | Entregable | Día |
|---|-------|------------|-----|
| 1.1 | Configurar Pi 5 (OS 64-bit, Docker, SSD) | Pi operativa con Docker | D1 |
| 1.2 | Escribir Dockerfiles por servicio (ARM64) | 4 Dockerfiles | D1 |
| 1.3 | Escribir `docker-compose.yml` completo | 6 servicios levantando | D1 |
| 1.4 | Configurar Mosquitto + InfluxDB | Broker MQTT + DB operativos | D2 |
| 1.5 | Volúmenes persistentes + `.env.example` | Datos en SSD, config documentada | D2 |

**Criterio de aceptación:** `docker compose up --build` levanta todo en la Pi al final del día 2.

---

### BLOQUE 2: Simulador de Telemetría
**Responsable:** _por asignar_
**Plazo:** Días 2-4 (28 feb → 2 mar)
**Depende de:** 1.4 (Mosquitto funcionando)

| # | Tarea | Entregable | Día |
|---|-------|------------|-----|
| 2.1 | Generador de telemetría completa (motor + GPS + bomberos) | `vehicle_simulator.py` publicando en MQTT | D2-D3 |
| 2.2 | Simulador de misiones (ciclo completo) | `mission_simulator.py` | D3 |
| 2.3 | Motor de escenarios what-if (3 escenarios) | `scenario_engine.py` | D4 |
| 2.4 | Rutas y perfiles de fallo | `routes.json` + `failure_profiles.json` | D3 |

**Criterio de aceptación:** Telemetría realista cada 1-2s verificable con `mosquitto_sub`.

---

### BLOQUE 3: Motor del Gemelo + IA
**Responsable:** _por asignar_
**Plazo:** Días 3-6 (1-4 mar)
**Depende de:** 2.1 (telemetría fluyendo)

| # | Tarea | Entregable | Día |
|---|-------|------------|-----|
| 3.1 | Modelos Pydantic (VehicleState, TelemetryEvent, Alert) | `core/models/` | D3 |
| 3.2 | State Manager + Event Processor | Estado actualizado por MQTT | D3-D4 |
| 3.3 | Rule Engine (umbrales y alertas) | `rule_engine.py` con 6 reglas | D4 |
| 3.4 | Anomaly Detector (Isolation Forest) | `anomaly_detector.py` | D5 |
| 3.5 | Failure Predictor (statsmodels/ARIMA) | `failure_predictor.py` predicción 48h | D5 |
| 3.6 | Decision Assistant (tabla de decisiones) | `decision_assistant.py` | D5 |
| 3.7 | Persistencia SQLite + InfluxDB | Histórico guardado | D6 |

**Criterio de aceptación:** Twin-engine consume telemetría, detecta anomalías y genera alertas automáticas.

> **Nota:** Usar `statsmodels` (ARIMA) en vez de Prophet para evitar problemas de compilación en ARM64 y ahorrar tiempo.

---

### BLOQUE 4: API REST + WebSocket
**Responsable:** _por asignar_
**Plazo:** Días 4-7 (2-5 mar)
**Depende de:** 3.1, 3.2 (modelos y state manager)

| # | Tarea | Entregable | Día |
|---|-------|------------|-----|
| 4.1 | FastAPI base + endpoints de estado | `/twin/{id}/state`, `/health` | D4 |
| 4.2 | Endpoints de alertas + anomalías | `/alerts/{id}`, `/anomalies/{id}` | D5 |
| 4.3 | Endpoints de simulación + predicción | `/simulate/scenario`, `/predict/failures` | D6 |
| 4.4 | WebSocket streaming | `/twin/{id}/stream` | D6 |
| 4.5 | Endpoints de ecosistema | `/ecosystem/status`, `/twins` | D7 |

**Criterio de aceptación:** Todos los endpoints documentados en Swagger.

---

### BLOQUE 5: Dashboard
**Responsable:** _por asignar_
**Plazo:** Días 5-8 (3-6 mar)
**Depende de:** 4.1 (API disponible)

| # | Tarea | Entregable | Día |
|---|-------|------------|-----|
| 5.1 | Layout Streamlit + panel de estado (gauges) | Estado en tiempo real | D5 |
| 5.2 | Panel de alertas + gráficas de telemetría | Alertas + Plotly charts | D6 |
| 5.3 | Mapa en tiempo real (Folium) | Posición del camión en mapa | D7 |
| 5.4 | Panel de simulación + predicciones | Lanzar what-if desde dashboard | D8 |

**Criterio de aceptación:** Dashboard accesible desde cualquier navegador en la red local.

---

## Día a Día — Resumen Ejecutivo

| Día | Fecha | Persona A (Infra+Sim) | Persona B (Motor+IA) | Persona C (API+Dash) |
|-----|-------|----------------------|---------------------|---------------------|
| D1 | 27 feb (Jue) | Pi + Docker + Compose + Dockerfiles | Modelos Pydantic (adelantar) | Estructura FastAPI (adelantar) |
| D2 | 28 feb (Vie) | Mosquitto + InfluxDB + telemetría base | Modelos Pydantic | Estructura FastAPI |
| D3 | 1 mar (Sáb) | Simulador completo + misiones + rutas | State Manager + Event Processor | -- |
| D4 | 2 mar (Dom) | Escenarios what-if | Rule Engine + alertas | Endpoints de estado |
| D5 | 3 mar (Lun) | Testing simulador + soporte | Anomaly Detector + Predictor + Decision | Endpoints alertas + dashboard base |
| D6 | 4 mar (Mar) | Soporte integración | Persistencia SQLite/InfluxDB | WebSocket + dashboard alertas/graficas |
| D7 | 5 mar (Mié) | **Integración** contenedores | **Integración** motor ↔ API | Mapa + endpoints ecosistema |
| D8 | 6 mar (Jue) | **Testing E2E** en Pi | **Testing E2E** anomalías | Dashboard simulación + predicciones |
| D9 | 7 mar (Vie) | **Buffer** — bugs, pulir, preparar demo | **Buffer** — bugs, pulir | **Buffer** — bugs, pulir |
| -- | **8 mar (Sáb)** | **ENTREGA** | **ENTREGA** | **ENTREGA** |

---

## Dependencias Críticas

```
Día 1-2: Bloque 1 (Infra)
              │
              ├──► Día 2-4: Bloque 2 (Simulador) ─── necesita MQTT
              │         │
              │         └──► Día 3-6: Bloque 3 (Motor) ─── necesita telemetría
              │                   │
              │                   ├──► Día 4-7: Bloque 4 (API) ─── necesita modelos
              │                   │         │
              │                   │         └──► Día 5-8: Bloque 5 (Dashboard) ─── necesita API
              │                   │
              │                   └──► Día 7-8: Integración + Tests E2E
              │
              └──► Día 9: Buffer + Demo final
```

---

## Asignación por Perfil

| Perfil | Bloques | Competencias necesarias |
|--------|---------|------------------------|
| **Persona A — DevOps + Backend** | Bloques 1 + 2 | Docker ARM64, Linux, MQTT, Python |
| **Persona B — Data/Backend** | Bloque 3 | scikit-learn, statsmodels, pandas, Pydantic |
| **Persona C — Backend + Frontend** | Bloques 4 + 5 | FastAPI, WebSockets, Streamlit, Plotly, Folium |

> Para equipo de 2 personas:
> - **Persona A:** Bloques 1 + 2 + parte de 3 (modelos, state manager)
> - **Persona B:** Resto de Bloque 3 + Bloques 4 + 5

---

## Hitos de Control

| Hito | Descripción | Fecha | Checkpoint |
|------|-------------|-------|------------|
| M1 | Pi con Docker Compose levantando servicios | 28 feb | Compose up funciona |
| M2 | Simulador publicando telemetría en MQTT | 1 mar | `mosquitto_sub` muestra datos |
| M3 | Twin-engine detectando anomalías | 4 mar | Alertas generadas automáticamente |
| M4 | API con Swagger completo | 5 mar | Todos los endpoints responden |
| M5 | Dashboard funcional | 6 mar | Dashboard visible en navegador |
| M6 | **Demo E2E completa** | **7 mar** | Incendio simulado → alerta → dashboard |
| -- | **ENTREGA** | **8 mar** | Todo empaquetado y funcionando |

---

## Riesgos y Mitigación

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Prophet no compila en ARM64 | Bloque 3.5 | Usar `statsmodels` (ARIMA) directamente |
| Pi con 4GB RAM | Todos | Eliminar InfluxDB, usar solo SQLite |
| SD card lenta | Rendimiento | SSD USB 3.0 desde el día 1 |
| Persona se bloquea | Retraso en cadena | Día de buffer (D9) + tareas adelantables |
| Integración falla al juntar | Días 7-8 | Definir interfaces MQTT/API el día 1, no al final |
| Falta de tiempo para dashboard | Bloque 5 | MVP: solo panel de estado + alertas (sin mapa ni simulación) |

---

## MVP — Qué recortar si no da tiempo

Si el día 6 se ve que no llega todo, priorizar este **mínimo demostrable**:

| Componente | Imprescindible | Recortable |
|------------|:--------------:|:----------:|
| Docker Compose en Pi | SI | -- |
| Simulador de telemetría | SI | Escenarios what-if |
| State Manager + Event Processor | SI | -- |
| Anomaly Detector | SI | Failure Predictor |
| Rule Engine + Decision Assistant | SI | -- |
| API REST (estado + alertas) | SI | Endpoints ecosistema |
| WebSocket streaming | SI | -- |
| Dashboard — estado + alertas | SI | -- |
| Dashboard — mapa Folium | NO | Recortable |
| Dashboard — simulación | NO | Recortable |
| Dashboard — predicciones | NO | Recortable |
| Persistencia InfluxDB | NO | Recortable (usar solo SQLite) |

> **MVP = simulador + motor + anomalías + API + dashboard básico, todo en Docker sobre la Pi.**
> Si se consigue el MVP el día 6, los días 7-8 se usan para añadir mapa, predicciones y pulir.
