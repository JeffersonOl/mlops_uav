"""
kafka_consumer.py — UAV Telemetry Stream Consumer
Consume los 3 topics UAV y llama al servicio de inferencia Flask.
"""
import json, time, base64, os, requests
from kafka import KafkaConsumer

KAFKA_BROKER  = os.environ.get("KAFKA_BROKER",   "localhost:9092")
INFER_URL     = os.environ.get("INFER_URL",       "http://localhost:5000/predict")
TOPICS        = ["uav.camera.frames", "uav.imu.data", "uav.cbf.metrics"]

def make_consumer():
    for attempt in range(10):
        try:
            c = KafkaConsumer(
                *TOPICS,
                bootstrap_servers=KAFKA_BROKER,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                auto_offset_reset="latest",
                group_id="uav-mlops-consumer",
            )
            print(f"[INFO] Consumer conectado a {KAFKA_BROKER}")
            return c
        except Exception as e:
            print(f"[WARN] Intento {attempt+1}/10: {e}. Reintentando en 3s...")
            time.sleep(3)
    raise RuntimeError("No se pudo conectar a Kafka")

def handle_camera(msg):
    """Envía frame al servicio de inferencia Flask."""
    try:
        r = requests.post(INFER_URL,
                          json={"frame": msg["data"]},
                          timeout=2)
        result = r.json()
        status = "OBSTACULO" if result["obstacle_detected"] else "LIBRE"
        print(f"[CAMERA] frame_id={msg['frame_id']} "
              f"→ {status} conf={result['confidence']:.3f} "
              f"lat={result['latency_ms']}ms "
              f"CBF={'SI' if result['cbf_activated'] else 'no'}")
    except Exception as e:
        print(f"[CAMERA] Error inferencia: {e}")

def handle_imu(msg):
    az = msg["linear_acceleration"]["z"]
    wz = msg["angular_velocity"]["z"]
    print(f"[IMU]    az={az:.3f} m/s² | wz={wz:.4f} rad/s")

def handle_cbf(msg):
    active = msg["cbf_active"]
    print(f"[CBF]    active={active} | "
          f"jerk={msg['jerk_m_s3']:.3f} m/s³ | "
          f"v={msg['velocity_mps']:.2f} m/s | "
          f"d_obs={msg['distance_to_obs_m']:.2f} m | "
          f"t_ret={msg['t_return_s']:.1f}s")

HANDLERS = {
    "uav.camera.frames": handle_camera,
    "uav.imu.data":      handle_imu,
    "uav.cbf.metrics":   handle_cbf,
}

def main():
    consumer = make_consumer()
    print(f"[INFO] Escuchando topics: {TOPICS}")
    try:
        for record in consumer:
            HANDLERS.get(record.topic, lambda m: None)(record.value)
    except KeyboardInterrupt:
        print("[INFO] Consumer detenido.")
    finally:
        consumer.close()

if __name__ == "__main__":
    main()
