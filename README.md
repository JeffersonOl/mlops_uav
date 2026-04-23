# 🚁 MLOps para Navegación Autónoma de UAV Indoor

[![CI/CD](https://github.com/JeffersonOl/mlops_uav/actions/workflows/ci.yml/badge.svg)](https://github.com/JeffersonOl/mlops_uav/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-%E2%9C%93-2496ED?logo=docker)](https://www.docker.com/)
[![Kubernetes](https://img.shields.io/badge/kubernetes-%E2%9C%93-326CE5?logo=kubernetes)](https://kubernetes.io/)

**Sistema habilitado por IA para navegación autónoma de UAV en entornos interiores sin GPS (GPS-denied), con evasión de obstáculos y colisiones.**

> 📌 **Materia:** Machine Learning in Production — Yachay Tech  
> 📌 **Autor:** Jefferson Daniel Olalla Delgado | Abril 2026

---

## 📌 Tabla de Contenidos

- [Contribución e Impacto](#-contribución-e-impacto)
- [Marco Teórico](#-marco-teórico-de-referencia)
- [Arquitectura del Sistema](#-arquitectura-del-sistema)
- [9 Requisitos del Syllabus](#-9-requisitos-del-syllabus)
- [Inicio Rápido](#-inicio-rápido)
- [Monitoreo y Acceso](#-monitoreo-y-acceso)
- [Estructura del Repositorio](#-estructura-del-repositorio)
- [Investigación Asociada](#-investigación-asociada)

---

## 🌍 Contribución e Impacto

**Contribución original:** Adaptación de la arquitectura Apollo (Baidu / U. de Toronto) al dominio UAV indoor GPS-denied. Transferencia metodológica de 7 capas no documentada previamente en literatura de maestría (ICRA/IROS 2024-2025).

### Impacto Social — CENACE Ecuador

Aplicación a inspección autónoma de subestaciones eléctricas en el contexto de apagones 2024-2026.

| Métrica | Valor |
|---------|-------|
| Inspección manual | 4 horas |
| Inspección autónoma | < 20 minutos |
| Reducción de tiempo | **> 90%** |

### Evidencia Cuantitativa

| Indicador | Valor |
|-----------|-------|
| Corridas de simulación | 13 (C1–C9 activas) |
| Bugs corregidos | 7 (v8.0-L → v8.0-O2) |
| Mejor resultado | Corrida C9: 4/6 KPIs cumplidos |
| Branch congelado | `v8.0-research-freeze-20Abr2026` |
| Commit referencia | `ee2950a` (tag v8.0-O2) |

---

## 📚 Marco Teórico de Referencia

Este proyecto se alinea con **"Fundamentals of Engineering AI-Enabled Systems"**:

| Dimensión | Implementación en este proyecto |
|-----------|-------------------------------|
| **Holistic system view** | IA (modelo) + Kafka + K8s + Prometheus + GitHub Actions |
| **Quality beyond accuracy** | KPIs de seguridad: jerk, CBF activaciones, t_return |
| **Risk analysis** | Confidence gate 3 niveles + CBF + health checks |
| **Planning for mistakes** | Liveness probes, timeouts, watchdogs, restart policies |
| **Reproducibility** | Docker + Git tags + W&B artifacts |
| **Safety** | CBF v2.2 + N-MPC Acados (investigación) |
| **Interpretability** | Confianza del modelo expuesta en API REST `/predict` |
| **Transparency** | Documentación completa + diagrama de arquitectura |

---

## 🏗️ Arquitectura del Sistema

Arquitectura de **7 capas** adaptada de Apollo al dominio UAV indoor.  
Ver descripción completa en [ARCHITECTURE.md](./ARCHITECTURE.md).

![Diagrama de Arquitectura](./docs/architecture_diagram.svg)

| Capa | Componente | Tecnología |
|------|-----------|------------|
| 1 | Fuentes de datos | Gazebo + PX4 / Dataset pre-grabado |
| 2 | Streaming | Apache Kafka (topics: camera, imu, cbf) |
| 3 | Inferencia | Docker + Flask (`/predict`, `/health`, `/metrics`) |
| 4 | Monitoreo de modelo | Weights & Biases |
| 5 | Monitoreo de sistema | Prometheus + Grafana |
| 6 | Orquestación | Kubernetes — Deployment + HPA + Service |
| 7 | CI/CD | GitHub Actions |

---

## ✅ 9 Requisitos del Syllabus

| # | Requisito | Implementación | Estado |
|---|-----------|----------------|:------:|
| 1 | Requisitos funcionales/no funcionales | [REQUIREMENTS.md](./REQUIREMENTS.md) | ✅ |
| 2 | Diagrama arquitectura Apollo-UAV | [ARCHITECTURE.md](./ARCHITECTURE.md) | ✅ |
| 3 | Docker entrenamiento | `training/Dockerfile.train` | ✅ |
| 4 | Docker inferencia + Flask + UI | `inference/Dockerfile.infer` | ✅ |
| 5 | W&B evaluación/monitoreo | `training/train.py` + [Dashboard W&B](https://wandb.ai/models-universidad-yachay-tech/mlops-uav-indoor) | ✅ |
| 6 | Kafka data streaming | `streaming/kafka_producer.py` + `kafka_consumer.py` | ✅ |
| 7 | Prometheus + Grafana | `monitoring/prometheus.yml` + `docker-compose.yml` | ✅ |
| 8 | Kubernetes | `k8s/deployment.yaml` + HPA 1→5 réplicas | ✅ |
| 9 | GitHub Actions CI/CD | `.github/workflows/ci.yml` | ✅ |

---

## 🚀 Inicio Rápido

### Prerrequisitos

- Docker + Docker Compose
- Python 3.11+
- Cuenta en [Weights & Biases](https://wandb.ai/)
- Minikube (opcional, para Kubernetes)

### Levantar el stack completo

```bash
# 1. Clonar
git clone https://github.com/JeffersonOl/mlops_uav.git
cd mlops_uav

# 2. Entrenar modelo
docker build -f training/Dockerfile.train -t uav-train ./training
docker run --name uav-train-run -e WANDB_API_KEY=<tu_key> uav-train
docker cp uav-train-run:/app/best_model.pt inference/
docker rm uav-train-run

# 3. Build imagen de inferencia
docker build -f inference/Dockerfile.infer -t uav-inference ./inference

# 4. Levantar stack completo
docker compose up -d

# 5. Verificar
curl http://localhost:5000/health
```

---

## 📊 Monitoreo y Acceso

| Servicio | URL | Credenciales |
|----------|-----|--------------|
| Flask UI + Demo | http://localhost:5000 | — |
| Prometheus | http://localhost:9090 | — |
| Grafana | http://localhost:3000 | admin / uav2026 |
| W&B Dashboard | [mlops-uav-indoor](https://wandb.ai/models-universidad-yachay-tech/mlops-uav-indoor) | — |
| Kubernetes (Minikube) | http://192.168.49.2:30500 | — |

---

## 📁 Estructura del Repositorio
mlops_uav/
├── .github/
│   └── workflows/
│       └── ci.yml                  # CI/CD: lint → test → build → push
├── docs/
│   ├── architecture_diagram.svg    # Diagrama visual del sistema
│   └── fundamentals_ai_eng.png     # Marco teórico de referencia
├── training/
│   ├── Dockerfile.train
│   ├── train.py                    # ObstacleProxyModel + W&B KPIs
│   └── requirements_train.txt
├── inference/
│   ├── Dockerfile.infer
│   ├── app.py                      # Flask API + UI + Prometheus
│   └── requirements_infer.txt
├── streaming/
│   ├── kafka_producer.py           # Topics: camera / imu / cbf
│   └── kafka_consumer.py
├── monitoring/
│   └── prometheus.yml
├── k8s/
│   ├── deployment.yaml             # HPA: 1 → 5 réplicas
│   └── service.yaml                # NodePort :30500
├── docker-compose.yml              # Stack: Kafka + Inference + Prometheus + Grafana
├── REQUIREMENTS.md                 # RF + RNF + Risk Analysis + Responsible AI
└── ARCHITECTURE.md                 # 7 capas Apollo-UAV + mapeo investigación
---

## 🔬 Investigación Asociada

Este sistema MLOps es la infraestructura de producción del proyecto de investigación:

> *"Navegación autónoma basada en visión para robot aéreo en entornos interiores mediante aprendizaje profundo y evasión de obstáculos"*

| Componente investigación | Integración MLOps |
|--------------------------|-------------------|
| CBF + N-MPC (Safety) | `uav_cbf_activations_total` en Prometheus |
| YOLOv8-nano + Safe-PPO | Reemplaza `ObstacleProxyModel` en producción |
| KPIs (jerk, t_return, cbf_total) | Exportados a W&B + Prometheus |
| Corrida C9 (4/6 KPIs) | Referencia en W&B run summary |
| Topics ROS2 Gazebo | Replicados en Kafka (`uav.camera.frames`, etc.) |

---

*Yachay Tech — Maestría en Inteligencia Artificial — Abril 2026*
