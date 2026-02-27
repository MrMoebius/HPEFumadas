# 🚒 Gemelo Digital — Camión de Bomberos

**Proyecto:** Horizonte Cero — Realidad Simulada (Fase II: Conflicto)
**Alianza HPE GreenLake — CDS Tech Challenge**

---

## 📖 Descripción

Prototipo funcional (POC) de un **Gemelo Digital de un camión de bomberos**, capaz de simular su comportamiento en tiempo real, detectar anomalías, predecir fallos mecánicos y asistir en la toma de decisiones operativas ante situaciones críticas como incendios, rescates y operaciones contra incendios.

El gemelo digital recibe telemetría simulada del vehículo (motor, ubicación, equipamiento contra incendios, estado de la misión) y proporciona:

- Monitoreo en tiempo real del estado del vehículo
- Detección automática de anomalías
- Predicción de fallos mecánicos
- Simulación de escenarios "¿Qué pasaría si...?"
- Insights accionables para el centro de mando

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                     CAPA DE SIMULACIÓN                          │
│                                                                 │
│  simulator/                                                     │
│  ├── vehicle_simulator.py    → Genera telemetría del vehículo   │
│  ├── mission_simulator.py    → Simula misiones de emergencia    │
│  └── scenario_engine.py      → Motor de escenarios "what-if"   │
│                                                                 │
│  Publica datos vía MQTT → topics: bomberos/telemetria/#        │
└──────────────────────────────┬──────────────────────────────────┘
                               │ MQTT
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     CAPA DE PROCESAMIENTO                       │
│                                                                 │
│  core/                                                          │
│  ├── twin_engine.py          → Motor principal del gemelo       │
│  ├── state_manager.py        → Gestión del estado del vehículo  │
│  ├── event_processor.py      → Procesamiento de eventos         │
│  └── rule_engine.py          → Motor de reglas y alertas        │
│                                                                 │
│  ai/                                                            │
│  ├── anomaly_detector.py     → Detección de anomalías (IF/LOF) │
│  ├── failure_predictor.py    → Predicción de fallos (Prophet)   │
│  └── decision_assistant.py   → Asistente de decisiones          │
│                                                                 │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     CAPA DE DATOS                               │
│                                                                 │
│  SQLite / InfluxDB                                              │
│  ├── telemetría histórica                                       │
│  ├── registro de eventos y alertas                              │
│  ├── histórico de misiones                                      │
│  └── resultados de simulaciones                                 │
│                                                                 │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     CAPA DE PRESENTACIÓN                        │
│                                                                 │
│  api/                                                           │
│  ├── main.py                 → FastAPI (REST API)               │
│  ├── routes/                 → Endpoints del gemelo             │
│  └── websocket.py            → Streaming en tiempo real         │
│                                                                 │
│  dashboard/                                                     │
│  └── app.py                  → Streamlit Dashboard              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Stack Tecnológico

| Capa | Tecnología | Justificación |
|------|-----------|---------------|
| Lenguaje | Python 3.11+ | Ecosistema ML maduro, prototipado rápido |
| Simulación | Generadores custom | Control total sobre la telemetría |
| Mensajería | MQTT (Mosquitto) | Protocolo estándar IoT, ligero y pub/sub |
| Backend/API | FastAPI | Async, alto rendimiento, documentación auto |
| Base de datos | SQLite + InfluxDB (opcional) | SQLite para POC, InfluxDB para series temporales |
| IA — Anomalías | scikit-learn (Isolation Forest) | Sin entrenamiento supervisado necesario |
| IA — Predicción | Prophet / statsmodels | Predicción de series temporales robusta |
| Dashboard | Streamlit | Dashboards interactivos rápidos en Python |
| Tiempo real | WebSockets | Streaming de estado a clientes |
| Contenedores | Docker + docker-compose | Despliegue reproducible |

---

## 📁 Estructura del Proyecto

```
bomberos-digital-twin/
│
├── docker-compose.yml              # Orquestación de servicios
├── Dockerfile                      # Imagen del proyecto
├── requirements.txt                # Dependencias Python
├── README.md                       # Este archivo
├── .env.example                    # Variables de entorno
│
├── config/
│   └── settings.py                 # Configuración centralizada
│
├── simulator/
│   ├── __init__.py
│   ├── vehicle_simulator.py        # Generador de telemetría
│   ├── mission_simulator.py        # Simulador de misiones
│   ├── scenario_engine.py          # Motor "what-if"
│   └── data/
│       ├── routes.json             # Rutas predefinidas
│       └── failure_profiles.json   # Perfiles de fallo
│
├── core/
│   ├── __init__.py
│   ├── twin_engine.py              # Motor del gemelo digital
│   ├── state_manager.py            # Estado del vehículo
│   ├── event_processor.py          # Procesador de eventos
│   ├── rule_engine.py              # Reglas y alertas
│   └── models/
│       ├── vehicle.py              # Modelo de datos: vehículo
│       ├── mission.py              # Modelo de datos: misión
│       └── telemetry.py            # Modelo de datos: telemetría
│
├── ai/
│   ├── __init__.py
│   ├── anomaly_detector.py         # Detección de anomalías
│   ├── failure_predictor.py        # Predicción de fallos
│   └── decision_assistant.py       # Asistente IA
│
├── api/
│   ├── __init__.py
│   ├── main.py                     # Aplicación FastAPI
│   ├── websocket.py                # WebSocket handler
│   └── routes/
│       ├── twin.py                 # GET /twin/state, /twin/history
│       ├── simulation.py           # POST /simulate/scenario
│       ├── alerts.py               # GET /alerts
│       └── ecosystem.py            # GET /ecosystem/status
│
├── dashboard/
│   └── app.py                      # Streamlit dashboard
│
├── ecosystem/
│   ├── __init__.py
│   ├── connector.py                # Conexión con otros gemelos
│   ├── event_bus.py                # Bus de eventos inter-gemelos
│   └── protocols.py                # Definición de protocolos
│
├── tests/
│   ├── test_twin_engine.py
│   ├── test_anomaly_detector.py
│   ├── test_simulator.py
│   └── test_api.py
│
└── docs/
    ├── arquitectura.md
    ├── modelo_datos.md
    └── ecosistema.md
```

---

## 📊 Modelo de Datos

### Vehículo (Estado del Gemelo)

```python
class VehicleState(BaseModel):
    # Identificación
    vehicle_id: str               # "BOM-001"
    vehicle_type: str             # "camion_bomberos_BUP"

    # Motor y mecánica
    engine_temp: float            # °C (normal: 80-100)
    engine_rpm: int               # RPM
    fuel_level: float             # % (0-100)
    oil_pressure: float           # PSI
    battery_voltage: float        # V (normal: 12.4-14.7)
    brake_wear: float             # % desgaste (0-100)
    tire_pressure: dict           # {"FL": 35, "FR": 35, "RL": 33, "RR": 33} PSI
    mileage_km: float             # Kilometraje total

    # Ubicación y movimiento
    latitude: float
    longitude: float
    speed_kmh: float
    heading: float                # Grados (0-360)

    # Equipamiento contra incendios
    water_tank_level: float       # % tanque de agua (0-100)
    foam_tank_level: float        # % tanque de espuma (0-100)
    pump_pressure: float          # PSI de la bomba de agua
    ladder_status: str            # "retracted" | "extended" | "fault"
    ladder_angle: float           # Grados de elevación (0-75)
    hose_deployed: bool           # Manguera desplegada
    hydraulic_pressure: float     # PSI sistema hidráulico
    crew_count: int               # Bomberos a bordo

    # Misión
    mission_status: str           # "disponible" | "en_ruta" | "en_escena" | "regreso_base"
    sirens_active: bool
    lights_active: bool

    # Metadatos
    timestamp: datetime
    anomalies: list[str]          # Anomalías activas
    risk_score: float             # 0.0 - 1.0
```

### Telemetría (Evento Individual)

```python
class TelemetryEvent(BaseModel):
    vehicle_id: str
    timestamp: datetime
    metric: str                   # "engine_temp", "speed_kmh", etc.
    value: float
    unit: str
    source: str                   # "sensor" | "simulated"
```

### Alerta

```python
class Alert(BaseModel):
    alert_id: str
    vehicle_id: str
    timestamp: datetime
    severity: str                 # "info" | "warning" | "critical"
    category: str                 # "mecanica" | "equipamiento" | "operativa"
    message: str
    metric: str
    current_value: float
    threshold: float
    recommended_action: str
```

---

## 🔌 API Endpoints

### Estado del Gemelo
```
GET  /api/v1/twin/{vehicle_id}/state         → Estado actual completo
GET  /api/v1/twin/{vehicle_id}/history        → Histórico de estados
GET  /api/v1/twin/{vehicle_id}/health         → Resumen de salud del vehículo
WS   /api/v1/twin/{vehicle_id}/stream         → WebSocket tiempo real
```

### Alertas y Anomalías
```
GET  /api/v1/alerts/{vehicle_id}              → Alertas activas
GET  /api/v1/alerts/{vehicle_id}/history      → Histórico de alertas
GET  /api/v1/anomalies/{vehicle_id}           → Anomalías detectadas
```

### Simulación
```
POST /api/v1/simulate/scenario                → Ejecutar escenario "what-if"
GET  /api/v1/simulate/scenarios               → Escenarios disponibles
POST /api/v1/simulate/failure                  → Simular fallo específico
```

### Predicción (IA)
```
GET  /api/v1/predict/{vehicle_id}/failures    → Predicción de fallos
GET  /api/v1/predict/{vehicle_id}/maintenance → Mantenimiento preventivo
```

### Ecosistema
```
GET  /api/v1/ecosystem/status                 → Estado de gemelos conectados
POST /api/v1/ecosystem/event                  → Enviar evento al ecosistema
GET  /api/v1/ecosystem/twins                  → Lista de gemelos registrados
```

---

## 🤖 Componentes de IA

### 1. Detección de Anomalías

**Algoritmo:** Isolation Forest + Local Outlier Factor (LOF)

```python
# Ejemplo de uso
detector = AnomalyDetector()
detector.fit(historical_telemetry)

# Evaluar nuevo dato
result = detector.evaluate({
    "engine_temp": 115.0,    # Anormalmente alto
    "pump_pressure": 18.0,   # Bajo
    "battery_voltage": 11.2  # Bajo
})
# result: {"is_anomaly": True, "score": 0.87, "features": ["engine_temp", "pump_pressure"]}
```

**Métricas monitoreadas:**
- Temperatura del motor (sobrecalentamiento)
- Presión de bomba de agua (fallo de bomba)
- Nivel de agua/espuma (suministro insuficiente)
- Presión hidráulica (fallo de escalera)
- Voltaje de batería (fallo eléctrico)

### 2. Predicción de Fallos

**Algoritmo:** Prophet / LSTM para series temporales

```python
predictor = FailurePredictor()
predictor.train(vehicle_history)

# Predecir próximos fallos
predictions = predictor.predict(vehicle_id="BOM-001", horizon_hours=48)
# [
#   {"component": "bomba_agua", "probability": 0.73, "estimated_hours": 18},
#   {"component": "sistema_hidraulico", "probability": 0.45, "estimated_hours": 36}
# ]
```

### 3. Asistente de Decisiones

Basado en reglas + scoring para recomendar acciones:

| Situación | Decisión Sugerida |
|-----------|-------------------|
| Agua < 15% en incendio activo | Solicitar cisterna de apoyo |
| Temperatura motor > 110°C | Reducir operación de bomba, solicitar relevo |
| Espuma < 20% y fuego químico | Alertar central, redirigir unidad HAZMAT |
| Fallo bomba de agua | Activar bomba auxiliar, solicitar unidad de respaldo |
| Presión hidráulica baja (escalera) | Retracción manual, no desplegar más |
| 2+ anomalías simultáneas | Evacuar equipo del vehículo, enviar reemplazo |

---

## 🎭 Escenarios de Simulación ("What-If")

### Escenario 1: Fallo de bomba durante incendio
```json
{
  "scenario": "pump_failure_during_fire",
  "description": "La bomba de agua falla durante un incendio activo",
  "parameters": {
    "initial_pump_pressure": 150,
    "pressure_drop_rate": 5.0,
    "fire_intensity": "alto",
    "backup_pump_available": true
  }
}
```

### Escenario 2: Múltiples incendios simultáneos
```json
{
  "scenario": "multi_fire_saturation",
  "description": "3 incendios simultáneos con solo 2 unidades disponibles",
  "parameters": {
    "fires": 3,
    "available_units": 2,
    "severity_levels": ["structural", "vehicle", "wildfire"]
  }
}
```

### Escenario 3: Fallo de escalera hidráulica
```json
{
  "scenario": "ladder_hydraulic_failure",
  "description": "La escalera hidráulica falla durante rescate en altura",
  "parameters": {
    "equipment": "hydraulic_ladder",
    "failure_type": "hydraulic_pressure_loss",
    "rescue_height_meters": 25,
    "people_stranded": 4
  }
}
```

---

## 🌐 Integración con el Ecosistema

El gemelo está diseñado para operar dentro de una red de activos interconectados:

```
                    ┌─────────────────────┐
                    │   CENTRO DE MANDO   │
                    │   (Orchestrator)    │
                    └─────────┬───────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
    ┌─────────▼──────┐ ┌─────▼──────┐ ┌──────▼─────────┐
    │  Gemelo BOM-001│ │ Gemelo     │ │ Gemelo         │
    │  (Bomberos)    │ │ POL-001   │ │ AMB-001        │
    │  *** ESTE ***  │ │ (Patrulla)│ │ (Ambulancia)   │
    └─────────┬──────┘ └─────┬──────┘ └──────┬─────────┘
              │               │               │
              └───────────────┼───────────────┘
                              │
                    ┌─────────▼───────────┐
                    │  ENTORNO DIGITAL    │
                    │  - Tráfico          │
                    │  - Clima            │
                    │  - Hidrantes        │
                    │  - Estaciones       │
                    └─────────────────────┘
```

### Eventos que recibe del entorno
- Nuevos incendios/emergencias asignados
- Cambios en tráfico/clima
- Estado de hidrantes (disponibilidad, presión)
- Órdenes del centro de mando

### Información que comparte
- Estado actual del vehículo y misión
- Alertas y anomalías detectadas
- Tiempo estimado de llegada (ETA)
- Disponibilidad y capacidad operativa

### Protocolo de comunicación
```python
# Formato de mensaje inter-gemelos (MQTT)
{
    "source": "BOM-001",
    "target": "COMMAND_CENTER",   # o "ALL", o "POL-001"
    "event_type": "status_update", # | "alert" | "request_backup" | "mission_complete"
    "payload": { ... },
    "timestamp": "2025-02-27T14:30:00Z",
    "priority": "high"            # "low" | "medium" | "high" | "critical"
}
```

---

## 🚀 Instalación y Ejecución

### Requisitos previos
- Python 3.11+
- Docker y docker-compose (opcional)
- MQTT Broker (Mosquitto) — incluido en docker-compose

### Instalación local

```bash
# Clonar el repositorio
git clone https://github.com/tu-equipo/bomberos-digital-twin.git
cd bomberos-digital-twin

# Crear entorno virtual
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# Instalar dependencias
pip install -r requirements.txt

# Copiar configuración
cp .env.example .env
```

### Ejecución

```bash
# 1. Iniciar MQTT broker (en otra terminal o con Docker)
docker run -d -p 1883:1883 -p 9001:9001 eclipse-mosquitto

# 2. Iniciar el backend (API + motor del gemelo)
uvicorn api.main:app --reload --port 8000

# 3. Iniciar el simulador de telemetría
python -m simulator.vehicle_simulator

# 4. Iniciar el dashboard
streamlit run dashboard/app.py
```

### Con Docker Compose

```bash
docker-compose up --build
```

Servicios disponibles:
| Servicio | URL |
|----------|-----|
| API REST | http://localhost:8000 |
| Docs API (Swagger) | http://localhost:8000/docs |
| Dashboard | http://localhost:8501 |
| MQTT Broker | localhost:1883 |

---

## 📦 Dependencias (`requirements.txt`)

```
# API
fastapi==0.109.0
uvicorn[standard]==0.27.0
websockets==12.0
pydantic==2.5.3

# MQTT
paho-mqtt==1.6.1

# Base de datos
sqlalchemy==2.0.25
aiosqlite==0.19.0

# IA / ML
scikit-learn==1.4.0
prophet==1.1.5
numpy==1.26.3
pandas==2.1.5

# Dashboard
streamlit==1.30.0
plotly==5.18.0

# Utilidades
python-dotenv==1.0.0
loguru==0.7.2
```

---

## 🧪 Tests

```bash
# Ejecutar todos los tests
pytest tests/ -v

# Ejecutar tests específicos
pytest tests/test_twin_engine.py -v
pytest tests/test_anomaly_detector.py -v

# Coverage
pytest tests/ --cov=core --cov=ai --cov-report=html
```

---

## 📐 Diagrama de Flujo — Ciclo del Gemelo

```
  Sensor/Simulador
        │
        ▼
  ┌──────────┐    ┌──────────────┐    ┌─────────────┐
  │  MQTT    │───▶│ Event        │───▶│ State       │
  │  Broker  │    │ Processor    │    │ Manager     │
  └──────────┘    └──────┬───────┘    └──────┬──────┘
                         │                    │
                         ▼                    ▼
                  ┌──────────────┐    ┌─────────────┐
                  │ Rule Engine  │    │ AI Module   │
                  │ (alertas)    │    │ (anomalías) │
                  └──────┬───────┘    └──────┬──────┘
                         │                    │
                         └────────┬───────────┘
                                  ▼
                         ┌─────────────────┐
                         │ Decision        │
                         │ Assistant       │
                         └────────┬────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼              ▼
              ┌──────────┐ ┌──────────┐  ┌────────────┐
              │Dashboard │ │ Alertas  │  │ Ecosistema │
              │          │ │          │  │ (otros     │
              │          │ │          │  │  gemelos)  │
              └──────────┘ └──────────┘  └────────────┘
```

---

## 👥 Equipo

| Rol | Responsabilidad |
|-----|----------------|
| Arquitecto | Diseño del sistema y modelo de datos |
| Backend Developer | API, motor del gemelo, procesamiento |
| Data Scientist | Modelos de IA, detección de anomalías |
| Frontend/Dashboard | Visualización y experiencia de usuario |

---

## 📄 Licencia

Proyecto desarrollado para el **CDS Tech Challenge — HPE GreenLake Alliance**.
