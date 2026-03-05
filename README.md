# Gemelo Digital — Camion de Bomberos BOM-001

**Proyecto:** Horizonte Cero — Realidad Simulada
**Alianza HPE GreenLake — CDS Tech Challenge**

---

## Descripcion

Prototipo funcional (POC) de un **Gemelo Digital de un camion de bomberos**, desplegado en edge computing (Raspberry Pi 5), capaz de:

- **Simular** comportamiento vehicular completo en tiempo real (motor, GPS, equipamiento contra incendios)
- **Detectar anomalias** automaticamente con Isolation Forest (sin entrenamiento supervisado)
- **Predecir fallos mecanicos** con modelos ARIMA de series temporales
- **Calcular rutas optimas** por calles reales de Valencia usando grafos OSM, evitando trafico
- **Visualizar** todo en un dashboard interactivo con mapa en tiempo real
- **Coordinar** con otros vehiculos de emergencia en un ecosistema de gemelos digitales

---

## Arquitectura

```
+-----------------------------------------------------------------------+
|           RASPBERRY PI 5 (8GB) + SSD USB 3.0                          |
|           Docker Compose (6 servicios, ARM64)                         |
|                                                                       |
|   +-------------------+        +------------------+                   |
|   |    simulator       |  MQTT  |   twin-engine    |                   |
|   |                   |------->|                  |                   |
|   | vehicle_simulator |        | state_manager    |                   |
|   | mission_simulator |        | rule_engine      |                   |
|   | GeoEngine (OSM)   |        | anomaly_detector |                   |
|   | RouteSimulator    |        | failure_predictor|                   |
|   | TrafficProvider   |        | decision_assist  |                   |
|   +-------------------+        +--------+---------+                   |
|          |                              |                             |
|          | MQTT                         | SQLite + InfluxDB           |
|          v                              v                             |
|   +------------------+         +------------------+                   |
|   |   mosquitto      |         |      api         |                   |
|   |   (MQTT broker)  |         |   FastAPI REST   |                   |
|   |   puerto 1883    |         |   WebSocket      |                   |
|   +------------------+         |   puerto 8002    |                   |
|                                +--------+---------+                   |
|                                         |                             |
|                                         v                             |
|                                +------------------+                   |
|                                |    dashboard     |                   |
|                                |    Streamlit     |                   |
|                                |    puerto 8501   |                   |
|                                +------------------+                   |
|                                                                       |
|   Red interna Docker: bomberos-net (bridge)                           |
+-----------------------------------------------------------------------+
```

---

## Stack Tecnologico

| Capa | Tecnologia | Justificacion |
|------|-----------|---------------|
| Lenguaje | Python 3.11+ | Ecosistema ML maduro, prototipado rapido |
| Simulacion | Generadores custom + OSM | Telemetria realista + rutas por calles reales |
| Cartografia | osmnx + networkx | Grafo vial de Valencia, Dijkstra optimizado |
| Mensajeria | MQTT (Mosquitto) | Protocolo estandar IoT, pub/sub, ligero |
| Backend/API | FastAPI | Async, alto rendimiento, OpenAPI auto |
| Base de datos | SQLite + InfluxDB | Persistencia ligera + series temporales |
| IA — Anomalias | scikit-learn (Isolation Forest) | Sin entrenamiento supervisado |
| IA — Prediccion | statsmodels (ARIMA) | Series temporales en edge |
| Dashboard | Streamlit + Plotly + Folium | Dashboards interactivos en Python |
| Tiempo real | WebSockets + MQTT | Streaming bidireccional |
| Contenedores | Docker Compose | Despliegue reproducible |
| Infraestructura | Raspberry Pi 5 (8GB) + SSD | Edge computing, bajo coste |

---

## Funcionalidades Implementadas

### 1. Simulador de Telemetria

El simulador genera datos realistas cada 2 segundos para un camion de bomberos BUP:

- **Motor:** temperatura, RPM, combustible, aceite, bateria, frenos, neumaticos
- **GPS:** posicion en coordenadas reales de Valencia, velocidad, rumbo
- **Equipamiento:** tanque de agua/espuma, bomba de presion, escalera hidraulica, manguera
- **Mision:** ciclo completo disponible → en_ruta → en_escena → regreso_base

### 2. Motor de Gemelo Digital (Twin Engine)

- **Gestion de estado** con persistencia en SQLite cada 10 ticks
- **Motor de reglas** con umbrales configurables para alertas automaticas
- **Procesador de eventos** que enruta telemetria a los modulos de IA

### 3. Inteligencia Artificial

- **Deteccion de Anomalias:** Isolation Forest sobre 8 metricas simultaneas. Detecta patrones anormales sin necesidad de datos etiquetados.
- **Prediccion de Fallos:** ARIMA para predecir tendencias de degradacion (horizonte 200s). Identifica componentes en riesgo con probabilidad y tiempo estimado.
- **Asistente de Decisiones:** Sistema basado en reglas que genera recomendaciones accionables (solicitar cisterna, reducir operacion de bomba, alertar HAZMAT).

### 4. Simulacion What-If

Escenarios de simulacion ejecutables desde el dashboard:

| Escenario | Descripcion |
|-----------|-------------|
| `pump_failure_during_fire` | Fallo de bomba durante incendio activo |
| `multi_fire_saturation` | 3 incendios simultaneos con 2 unidades |
| `ladder_hydraulic_failure` | Fallo hidraulico durante rescate en altura |

### 5. Modulo de Cartografia y Trafico

**Routing real por calles de Valencia** usando grafos OpenStreetMap:

- **GeoEngine:** Descarga y cachea el grafo vial de Valencia (18.000+ nodos, 34.000+ aristas, radio 8km). Calcula rutas con Dijkstra.
- **Rutas optimas vs directas:** Calcula dos rutas simultaneas:
  - *Ruta directa:* camino mas corto por distancia (Dijkstra con peso `length`)
  - *Ruta optima:* camino mas rapido evitando trafico (Dijkstra con peso `traffic_time`)
  - Ambas se muestran en el mapa para comparacion visual
- **Trafico simulado:** 12 zonas de trafico en calles principales de Valencia con modelo de congestion por hora punta (7-9h, 13-14h, 17-19h). Factor 1.0 (fluido) a 2.0 (muy congestionado).
- **POIs:** 30 hidrantes + 5 estaciones de bomberos con posiciones reales
- **RouteSimulator:** Interpolacion tick-a-tick por coordenadas reales con velocidad variable y factor de congestion
- **Fallback:** Si el GeoEngine no esta disponible (sin red, error OSM), el simulador usa waypoints predefinidos

### 6. Dashboard Interactivo

6 paginas con visualizacion en tiempo real:

- **Estado en Tiempo Real:** 8 gauges (motor, agua, combustible, bateria, bomba, espuma, hidraulica, RPM) + metricas instantaneas
- **Alertas:** Activas, historico, anomalias con risk score
- **Telemetria:** Graficos historicos multi-metrica, velocidad/RPM dual axis, niveles de tanques
- **Mapa:** Mapa interactivo Folium con:
  - Posicion del vehiculo en tiempo real
  - Ruta optima (linea solida coloreada segun congestion)
  - Ruta directa (linea gris discontinua para comparacion)
  - Zonas de trafico con circulos coloreados (verde/amarillo/naranja/rojo)
  - Hidrantes (circulos azules) y estaciones de bomberos (marcadores rojos)
  - Leyenda visual + metricas de comparacion (distancia, tiempo ahorrado)
  - ETA, progreso, distancia restante con barra de progreso
- **Simulacion:** Ejecutar escenarios what-if con graficos de resultados
- **Predicciones:** Prediccion de fallos y mantenimiento preventivo

### 7. Boton de Emergencia

Boton "SIMULAR EMERGENCIA" en el dashboard que envia un comando MQTT al simulador para forzar una emergencia inmediata, permitiendo demostrar el sistema en vivo.

---

## Protocolo MQTT

### Topics

```
bomberos/telemetria/BOM-001    → Telemetria cada 2s (JSON completo)
bomberos/alertas/BOM-001       → Alertas del twin-engine
bomberos/comandos/BOM-001      → Comandos externos (force_emergency)
bomberos/estado/BOM-001        → Estado resumido de mision
bomberos/ruta/BOM-001          → Datos de ruta activa
```

### Mensaje de ruta (route_started)

```json
{
  "type": "route_started",
  "coords": [[39.47, -0.37], ...],
  "direct_coords": [[39.47, -0.38], ...],
  "destination": "Puerto de Valencia",
  "total_distance_m": 3776,
  "direct_distance_m": 3226,
  "eta_seconds": 227,
  "congestion_factor": 1.3
}
```

### Telemetria (cada tick)

```json
{
  "vehicle_id": "BOM-001",
  "engine_temp": 95.3,
  "speed_kmh": 65.0,
  "water_tank_level": 87.5,
  "pump_pressure": 130.0,
  "route_progress": 0.45,
  "eta_seconds": 102,
  "distance_remaining_m": 1350,
  "on_route": true,
  "mission_status": "en_ruta",
  "timestamp": "2026-03-02T22:30:00Z"
}
```

---

## API Endpoints

### Estado del Gemelo (`/api/v1/twin`)
| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| GET | `/{vehicle_id}/state` | Estado actual completo |
| GET | `/{vehicle_id}/history` | Historico de estados |
| GET | `/{vehicle_id}/health` | Salud del vehiculo |
| WS | `/{vehicle_id}/stream` | WebSocket tiempo real |

### Alertas y Anomalias
| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| GET | `/alerts/{vehicle_id}` | Alertas activas |
| GET | `/alerts/{vehicle_id}/history` | Historico de alertas |
| GET | `/anomalies/{vehicle_id}` | Anomalias + risk score |

### Simulacion (`/api/v1/simulate`)
| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| GET | `/scenarios` | Escenarios disponibles |
| POST | `/scenario` | Ejecutar what-if |
| POST | `/failure` | Simular fallo |

### Prediccion IA (`/api/v1/predict`)
| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| GET | `/{vehicle_id}/failures` | Prediccion de fallos |
| GET | `/{vehicle_id}/maintenance` | Mantenimiento preventivo |

### Cartografia y Trafico (`/api/v1/geo`)
| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| GET | `/{vehicle_id}/route` | Ruta activa (optima + directa) |
| GET | `/poi/hydrants` | Hidrantes de Valencia |
| GET | `/poi/stations` | Estaciones de bomberos |
| GET | `/traffic/current` | Factor de congestion global |
| GET | `/traffic/zones` | Congestion por zona (12 zonas) |
| POST | `/force-emergency` | Forzar emergencia |

### Ecosistema (`/api/v1/ecosystem`)
| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| GET | `/status` | Estado de gemelos conectados |
| GET | `/twins` | Lista de gemelos registrados |
| POST | `/event` | Enviar evento inter-gemelo |

---

## Despliegue

### Requisitos

- Docker + Docker Compose v2+
- Raspberry Pi 5 (8GB) con SSD USB 3.0, o cualquier maquina x86/ARM64

### Arranque rapido

```bash
git clone https://github.com/tu-equipo/HPEFumadas.git
cd HPEFumadas
cp .env.example .env
docker compose up --build -d
```

### Acceso

| Servicio | Puerto | URL |
|----------|--------|-----|
| Dashboard | 8501 | http://localhost:8501 |
| API REST | 8002 | http://localhost:8002 |
| API Docs | 8002 | http://localhost:8002/docs |
| MQTT Broker | 1883 | mqtt://localhost:1883 |
| InfluxDB | 8086 | http://localhost:8086 |

### Recursos estimados

| Contenedor | RAM | CPU |
|------------|-----|-----|
| mosquitto | ~20 MB | Minimo |
| simulator | ~300 MB | Medio (osmnx) |
| twin-engine | ~200 MB | Medio (IA) |
| api | ~100 MB | Bajo |
| dashboard | ~150 MB | Bajo |
| influxdb | ~150 MB | Bajo |
| **Total** | **~920 MB** | **Holgado en Pi 5** |

---

## Estructura del Proyecto

```
HPEFumadas/
|
|-- docker-compose.yml
|-- .env / .env.example
|-- README.md
|
|-- config/
|   +-- settings.py                  # Configuracion centralizada (MQTT, IDs, topics)
|
|-- simulator/
|   |-- Dockerfile
|   |-- requirements.txt             # paho-mqtt, osmnx, networkx, scikit-learn
|   |-- vehicle_simulator.py         # Generador de telemetria + GeoEngine
|   |-- mission_simulator.py         # Ciclo de vida de misiones
|   |-- scenario_engine.py           # Motor what-if
|   +-- data/
|       |-- routes.json              # 4 rutas predefinidas (fallback)
|       +-- failure_profiles.json    # Perfiles de fallo
|
|-- core/
|   |-- Dockerfile
|   |-- requirements.txt
|   |-- twin_engine.py               # Motor principal del gemelo
|   |-- state_manager.py             # Estado + persistencia SQLite
|   |-- event_processor.py           # Procesador de eventos MQTT
|   |-- rule_engine.py               # Reglas y alertas
|   +-- models/
|       |-- vehicle.py               # VehicleState (45+ campos)
|       |-- mission.py               # Modelo de mision
|       +-- telemetry.py             # Evento de telemetria
|
|-- ai/
|   |-- anomaly_detector.py          # Isolation Forest
|   |-- failure_predictor.py         # ARIMA prediccion
|   +-- decision_assistant.py        # Asistente de decisiones
|
|-- geo/
|   |-- __init__.py
|   |-- engine.py                    # GeoEngine: grafo OSM, shortest_route, fastest_route
|   |-- route_simulator.py           # Interpolacion tick-a-tick por ruta real
|   |-- traffic.py                   # Modelo de congestion + zonas de trafico
|   |-- poi.py                       # Cargador de POIs (hidrantes, estaciones)
|   |-- data/
|   |   |-- hydrants.json            # 30 hidrantes de Valencia
|   |   +-- stations.json            # 5 estaciones de bomberos
|   +-- cache/
|       +-- .gitkeep                 # Cache del grafo .graphml (Docker volume)
|
|-- api/
|   |-- Dockerfile
|   |-- requirements.txt
|   |-- main.py                      # FastAPI app
|   |-- state.py                     # Estado compartido (MQTT subscriber)
|   |-- websocket.py                 # WebSocket handler
|   +-- routes/
|       |-- twin.py                  # /twin endpoints
|       |-- alerts.py                # /alerts + /anomalies
|       |-- simulation.py            # /simulate endpoints
|       |-- prediction.py            # /predict endpoints
|       |-- geo.py                   # /geo endpoints (rutas, POIs, trafico)
|       +-- ecosystem.py            # /ecosystem endpoints
|
|-- dashboard/
|   |-- Dockerfile
|   |-- requirements.txt
|   +-- app.py                       # Streamlit dashboard (6 paginas)
|
|-- ecosystem/
|   |-- connector.py                 # Conexion con otros gemelos
|   |-- event_bus.py                 # Bus de eventos inter-gemelos
|   +-- protocols.py                 # Protocolos de comunicacion
|
|-- mosquitto/
|   +-- mosquitto.conf               # Config del broker MQTT
|
+-- data/                            # Volumenes persistentes
    |-- sqlite/
    +-- influxdb/
```

---

## Roadmap — Proximas Fases

### Fase 1: Centro de Mando Interactivo (Prioridad ALTA)

Transformar el dashboard de "monitor pasivo" a **centro de control operativo**:

| Funcionalidad | Descripcion | Impacto |
|---------------|-------------|---------|
| **Dispatch manual** | Arrastrar-y-soltar vehiculos a emergencias desde el mapa | El operador asigna misiones, no solo las observa |
| **Chat de mando** | Canal de texto en tiempo real entre centro y vehiculos via MQTT | Comunicacion bidireccional integrada |
| **Alertas con acciones** | Cada alerta presenta botones de accion (confirmar, escalar, descartar) | Gestion activa de alertas, no solo visualizacion |
| **Timeline de mision** | Linea temporal visual del ciclo de mision con marcas de eventos | Trazabilidad completa de cada intervencion |
| **Modo pantalla completa** | Vista optimizada para pantalla grande en sala de control | Presentacion profesional para demo |

### Fase 2: Gestion Inteligente de Alarmas

Evolucionar de alertas simples a un **sistema de gestion de alarmas industrial**:

```
Nivel 1: INFORMATIVA
  |  (log, no accion)
  v
Nivel 2: ADVERTENCIA
  |  (notificacion al operador, confirmar en 60s)
  v
Nivel 3: CRITICA
  |  (sirena visual/sonora, accion requerida en 30s)
  v
Nivel 4: EMERGENCIA
     (accion automatica + notificacion a toda la cadena de mando)
```

| Tipo de Alarma | Trigger | Accion Automatica |
|----------------|---------|-------------------|
| Mecanica | Motor > 115C, bomba < 30 PSI | Reducir operacion, solicitar relevo |
| Operativa | Agua < 15% en escena | Despachar cisterna |
| Seguridad | 2+ anomalias simultaneas | Evacuacion del vehiculo |
| Coordinacion | Vehiculo no responde en 30s | Alertar centro de mando |
| Escalado | Incendio > capacidad | Solicitar refuerzos automaticamente |

**Flujo de escalado:**
1. Alerta detectada por twin-engine (reglas + IA)
2. Publicacion en `bomberos/alertas/{ID}` con severity y acciones sugeridas
3. Dashboard muestra alerta con botones de accion
4. Si no hay respuesta en X segundos, auto-escalado al nivel superior
5. Nivel 4: accion automatica + notificacion push al jefe de operaciones

### Fase 3: Protocolos de Interoperabilidad

Integrar estandares reales de emergencias:

| Protocolo | Uso | Implementacion |
|-----------|-----|----------------|
| **CAP** (Common Alerting Protocol) | Formato estandar de alertas OASIS | Wrapper XML/JSON sobre MQTT |
| **NIMS/ICS** | Sistema de Mando de Incidentes | Roles (IC, Operations, Logistics) en el modelo |
| **EMSI** (Emergency Management Shared Information) | Compartir info entre agencias | API REST inter-organizacion |
| **TETRA/P25** | Radio digital de emergencias | Simulacion de canal de voz via WebSocket |

**Mensaje inter-agencia (propuesta CAP simplificado):**

```json
{
  "identifier": "BOM-001-2026-03-02-001",
  "sender": "bomberos-valencia",
  "sent": "2026-03-02T22:30:00+01:00",
  "status": "Actual",
  "msgType": "Alert",
  "scope": "Restricted",
  "info": {
    "category": "Fire",
    "event": "Incendio estructural",
    "urgency": "Immediate",
    "severity": "Severe",
    "certainty": "Observed",
    "area": {
      "description": "Puerto de Valencia, Nave 12",
      "circle": "39.4500,-0.3250 0.5"
    },
    "resources_needed": ["BOM", "AMB", "POL"],
    "units_dispatched": ["BOM-001", "AMB-001"]
  }
}
```

### Fase 4: IA Avanzada

| Capacidad | Algoritmo | Descripcion |
|-----------|-----------|-------------|
| **Despliegue predictivo** | Clustering + series temporales | Pre-posicionar vehiculos en zonas de alto riesgo segun hora/dia |
| **Estimacion de recursos** | Clasificador ML | Dado tipo de emergencia, estimar bomberos/agua/espuma necesarios |
| **Optimizacion de flota** | Programacion lineal | Asignar vehiculos a emergencias minimizando tiempo total de respuesta |
| **NLP para despacho** | LLM (Claude API) | Operador describe emergencia en texto libre, sistema extrae tipo/ubicacion/severidad |
| **Vision por camara** | YOLO/deteccion objetos | Detectar humo/fuego desde camaras del vehiculo (futuro con hardware real) |

### Fase 5: Hardware Real (Post-Hackathon)

| Componente | Proposito | Conexion |
|------------|-----------|----------|
| GPS modulo (NEO-6M) | Posicion real del vehiculo | UART → Raspberry Pi |
| Sensores OBD-II | Telemetria real del motor | Bluetooth → adapter |
| Sensor de flujo | Nivel real de tanque de agua | GPIO → ADC |
| Camara termica | Deteccion de focos de calor | USB → OpenCV |
| LoRa modulo | Comunicacion en zonas sin cobertura | SPI → gateway |

---

## Demo Rapida

```bash
# 1. Levantar todo
docker compose up --build -d

# 2. Abrir dashboard
# http://localhost:8501

# 3. Ir a la pagina "Mapa"

# 4. Pulsar "SIMULAR EMERGENCIA" en el sidebar

# 5. Observar:
#    - Vehiculo se mueve por calles reales de Valencia
#    - Ruta optima (linea solida) vs ruta directa (linea gris discontinua)
#    - Zonas de trafico coloreadas por congestion
#    - ETA y progreso actualizandose
#    - Hidrantes y estaciones de bomberos en el mapa

# 6. Ir a "Estado en Tiempo Real" para ver los gauges del motor

# 7. Ir a "Alertas" para ver anomalias detectadas por IA

# 8. Ir a "Simulacion" para ejecutar escenarios what-if
```

---

## Equipo

| Rol | Responsabilidad |
|-----|----------------|
| Arquitecto | Diseno del sistema, modelo de datos, infraestructura Docker |
| Backend Developer | API, motor del gemelo, GeoEngine, procesamiento MQTT |
| Data Scientist | Modelos de IA (anomalias, prediccion, decisiones) |
| Frontend/Dashboard | Visualizacion Streamlit, mapa interactivo, UX |

---

## Licencia

Proyecto desarrollado para el **CDS Tech Challenge — HPE GreenLake Alliance**.
  