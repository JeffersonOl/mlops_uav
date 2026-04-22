"""
kafka_producer.py — UAV Telemetry Stream Producer
Replica los topics ROS2 del simulador Gazebo de la tesis:
  uav.camera.frames  <->  /camera/image_raw
  uav.imu.data       <->  /mavros/imu/data
  uav.cbf.metrics    <->  KPIs Control Barrier Function
"""
import json, time, base64, random, os
import numpy as np
from kafka import KafkaProducer

KAFKA_BROKER = os.environ.get("KAFKA_BROKER", "localhost:9092")
TOPICS = {
    "camera": "uav.camera.frames",
    "imu":    "uav.imu.data",
    "cbf":    "uav.cbf.metrics",
}
INTERVAL = float(os.environ.get("PUBLISH_INTERVAL", "0.1"))  # 10 fps

def make_producer():
    for attempt in range(10):
        try:
            p = KafkaProducer(
                bootstrap_servers=KAFKA_BROKER,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
            print(f"[INFO] Conectado a Kafka en {KAFKA_BROKER}")
            return p
        except Exception as e:
            print(f"[WARN] Intento {attempt+1}/10 fallido: {e}. Reintentando en 3s...")
            time.sleep(3)
    raise RuntimeError("No se pudo conectar a Kafka")

def gen_camera_frame(t):
    has_obstacle = (int(t) % 5 == 0)
    arr = np.random.uniform(
        0.55 if has_obstacle else 0.0,
        1.0  if has_obstacle else 0.45,
        (64 * 64,)
    ).astype(np.float32)
    return {
        "timestamp": t,
        "frame_id":  int(t * 10),
        "width": 64, "height": 64,
        "encoding": "mono_float32",
        "data": base64.b64encode(arr.tobytes()).decode(),
        "has_obstacle_gt": has_obstacle,
        "topic_ros2": "/camera/image_raw",
    }

def gen_imu_data(t):
    return {
        "timestamp": t,
        "orientation": {
            "x": random.gauss(0, 0.01),
            "y": random.gauss(0, 0.01),
            "z": random.gauss(0, 0.05),
            "w": 1.0,
        },
        "angular_velocity": {
            "x": random.gauss(0, 0.02),
            "y": random.gauss(0, 0.02),
            "z": random.gauss(0, 0.1),
        },
        "linear_acceleration": {
            "x": random.gauss(0, 0.1),
            "y": random.gauss(0, 0.1),
            "z": 9.81 + random.gauss(0, 0.05),
        },
        "topic_ros2": "/mavros/imu/data",
    }

def gen_cbf_metrics(t):
    cbf_active = random.random() < 0.1
    return {
        "timestamp": t,
        "cbf_active":        cbf_active,
        "cbf_value":         random.uniform(0.0, 0.3) if cbf_active else 0.0,
        "jerk_m_s3":         random.uniform(0.3, 1.2),
        "velocity_mps":      random.uniform(0.2, 1.5),
        "distance_to_obs_m": random.uniform(0.3, 3.0),
        "t_return_s":        random.uniform(2.0, 15.0),
        "corrida_ref":       "C9",
        "topic_ros2":        "uav_cbf_metrics",
    }

def main():
    producer = make_producer()
    frame_count = 0
    print(f"[INFO] Publicando a topics: {list(TOPICS.values())}")
    print(f"[INFO] Intervalo: {INTERVAL}s ({1/INTERVAL:.0f} fps simulados)")
    try:
        while True:
            t = time.time()
            producer.send(TOPICS["camera"], gen_camera_frame(t))
            producer.send(TOPICS["imu"],    gen_imu_data(t))
            if frame_count % 10 == 0:
                producer.send(TOPICS["cbf"], gen_cbf_metrics(t))
            frame_count += 1
            if frame_count % 50 == 0:
                print(f"[INFO] Frames publicados: {frame_count}")
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        print("[INFO] Producer detenido.")
    finally:
        producer.flush()
        producer.close()

if __name__ == "__main__":
    main()
