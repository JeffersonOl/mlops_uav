# Requisitos del Sistema – Navegación Autónoma de UAV Indoor

## Contexto
Este documento define los requisitos funcionales y no funcionales del sistema
habilitado por IA para navegación autónoma de un robot aéreo (UAV) en entornos
interiores sin GPS, con capacidades de evasión de obstáculos y colisiones.

## Referencia al Marco Teórico
Los requisitos siguen el modelo *"Fundamentals of Engineering AI-Enabled Systems"*,
cubriendo:
- Holistic system view (IA + componentes no-IA)
- Quality beyond accuracy
- Risk analysis & Planning for mistakes
- Responsible AI Engineering (safety, reproducibility, transparency)

---

## Requisitos Funcionales (RF)

| ID | Descripción | Componente asociado |
|----|-------------|---------------------|
| RF1 | Recibir flujo de video desde cámara monocular (simulada o real) | Kafka Producer |
| RF2 | Predecir presencia de obstáculos y comandos de velocidad (vx, vy, vz) | ObstacleProxyModel / YOLOv8+LSTM |
| RF3 | Exponer API REST para inferencia síncrona | Flask `/predict` |
| RF4 | Proporcionar interfaz gráfica web para visualización en tiempo real | Flask + HTML/JS |
| RF5 | Registrar métricas de entrenamiento y predicción | Weights & Biases (W&B) |
| RF6 | Transmitir datos en tiempo real vía streaming | Apache Kafka |
| RF7 | Exponer métricas de salud para monitoreo | Prometheus `/metrics` |
| RF8 | Ser desplegable como contenedores orquestados | Kubernetes |
| RF9 | Integrar pipeline de integración continua | GitHub Actions |

---

## Requisitos No Funcionales (RNF)

| ID | Descripción | Métrica objetivo | Justificación |
|----|-------------|------------------|---------------|
| RNF1 | Reproducibilidad | `docker build` + `docker run` produce mismo resultado | Ciencia reproducible |
| RNF2 | Latencia de inferencia | < 100 ms por frame | Tiempo real para UAV |
| RNF3 | Disponibilidad del API | 99% durante demostración | Confiabilidad |
| RNF4 | Trazabilidad de experimentos | Cada corrida loggeada a W&B | Auditoría |
| RNF5 | Tolerancia a fallos de streaming | Reconexión automática de Kafka | Robustez |
| RNF6 | Seguridad | Sin hardcoding de API keys (usar secrets) | Buenas prácticas |
| RNF7 | Escalabilidad horizontal | Múltiples réplicas en K8s | Preparado para producción |

---

## Quality Beyond Accuracy

| Dimensión | Métrica | Cómo se mide |
|-----------|---------|---------------|
| Precisión del modelo | Accuracy en conjunto de prueba | W&B dashboard |
| Confiabilidad del sistema | Tasa de éxito de predicciones | Prometheus `uav_frames_total` |
| Monitoreo de drift | Distribución de confianza del modelo | W&B + Grafana |
| Seguridad del UAV | Jerk < 10 m/s³, CBF activaciones < 100 | KPIs corrida C9 |
| Reproducibilidad | Versión Docker + commit hash | `docker inspect` + `git log` |

---

## Risk Analysis & Planning for Mistakes

| Riesgo | Probabilidad | Mitigación implementada |
|--------|--------------|-------------------------|
| Modelo produce salidas erróneas | Media | Confidence gate + CBF safety |
| Kafka se cae | Baja | Docker compose con restart policy |
| Prometheus pierde métricas | Baja | Persistencia de datos configurada |
| Error en API Flask | Media | Health check endpoint `/health` |
| Fallo en Kubernetes pod | Baja | Liveness + readiness probes |
| Drift del modelo en producción | Media | Monitoreo continuo en W&B |

---

## Responsible AI Engineering

| Principio | Implementación |
|-----------|----------------|
| Provenance & Versioning | Git tags + Docker tags + W&B run IDs |
| Reproducibilidad | Docker + requirements.txt + semillas fijas |
| Safety | CBF (Control Barrier Function) en investigación |
| Security | Secrets de GitHub + variables de entorno |
| Interpretability | Confianza del modelo expuesta en API |
| Transparency | README con arquitectura + instrucciones |

---

## Alineación con Fundamentals of Engineering AI-Enabled Systems

| Dimensión del marco teórico | Implementación en este proyecto |
|-----------------------------|--------------------------------|
| Holistic system view | IA (modelo) + Kafka + K8s + Prometheus |
| Quality beyond accuracy | KPIs: jerk, CBF activaciones, t_return |
| Risk analysis | Confidence gate 3 niveles + CBF + watchdogs |
| Planning for mistakes | Health checks, timeouts, restart policies |
| Reproducibility | Docker + Git + W&B |
| Safety | CBF v2.2 + N-MPC Acados (investigación) |
| Interpretability | Confianza del modelo expuesta en API REST |

---

## Contribución e Impacto

### Contribución Original
Adaptación de arquitectura Apollo (coches autónomos terrestres, U. de Toronto)
a UAV indoor GPS-denied. Transferencia metodológica de 7 capas Apollo al dominio
de navegación aérea en entornos cerrados sin señal GPS.

### Impacto Social — CENACE Ecuador
Inspección autónoma de subestaciones eléctricas en Ecuador.
Contexto: apagones 2024-2026. Reducción de tiempo de inspección
de 4 horas (manual) a < 20 minutos (autónomo).

### Evidencia Cuantitativa
- 13 corridas de simulación documentadas (C1–C9 activas)
- 7 bugs corregidos con causa raíz identificada
- Corrida C9: 4/6 KPIs cumplidos (mejor resultado)
- Branch congelado: v8.0-research-freeze-20Abr2026, commit ee2950a

---

**Versión:** 1.0
**Fecha:** 22 de abril de 2026
**Autor:** Jefferson D. Olalla Delgado — Yachay Tech
**Repositorio:** https://github.com/JeffersonOl/mlops_uav
