import os, time, base64
import numpy as np
import torch
import torch.nn as nn
from flask import Flask, request, jsonify, render_template_string
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

class ObstacleProxyModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Linear(64*64, 512), nn.BatchNorm1d(512), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(512, 128),  nn.BatchNorm1d(128), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(128, 32),   nn.ReLU(),
        )
        self.classifier = nn.Linear(32, 2)

    def forward(self, x):
        return self.classifier(self.features(x.view(x.size(0), -1)))

MODEL_PATH = os.environ.get("MODEL_PATH", "best_model.pt")
device = torch.device("cpu")
model = ObstacleProxyModel()
if os.path.exists(MODEL_PATH):
    model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    print(f"[INFO] Modelo cargado desde {MODEL_PATH}")
else:
    print("[WARN] Modelo no encontrado — usando pesos aleatorios (demo)")
model.eval()

FRAMES_TOTAL      = Counter("uav_frames_total", "Total frames procesados")
OBSTACLE_DETECTED = Counter("uav_obstacle_detected_total", "Obstaculos detectados")
FREE_PATH         = Counter("uav_free_path_total", "Caminos libres detectados")
LATENCY           = Histogram("uav_inference_latency_seconds", "Latencia inferencia",
                               buckets=[0.005,0.01,0.025,0.05,0.1,0.25,0.5])
CONFIDENCE        = Gauge("uav_model_confidence_last", "Confianza ultima prediccion")
CBF_ACTIVATIONS   = Counter("uav_cbf_activations_total", "Activaciones CBF (KPI tesis)")
ERRORS            = Counter("uav_request_errors_total", "Errores en peticiones")

UI = """
<!DOCTYPE html><html lang="es"><head>
<meta charset="UTF-8"><title>UAV Obstacle Detection</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;background:#0d1117;color:#e6edf3;
     display:flex;flex-direction:column;align-items:center;padding:2rem}
h1{font-size:1.8rem;color:#58a6ff;text-align:center;margin-bottom:.5rem}
.sub{color:#8b949e;font-size:.85rem;text-align:center;margin-bottom:2rem}
.card{background:#161b22;border:1px solid #30363d;border-radius:12px;
      padding:1.5rem;margin-bottom:1.5rem;width:100%;max-width:680px}
.card h2{color:#c9d1d9;font-size:1rem;margin-bottom:1rem}
.row{display:flex;justify-content:space-between;padding:.4rem 0;
     border-bottom:1px solid #21262d;font-size:.85rem}
.row:last-child{border-bottom:none}
.lbl{color:#8b949e}.val{font-weight:600}
.btn{background:#238636;color:#fff;border:none;padding:.6rem 1.2rem;
     border-radius:6px;cursor:pointer;font-weight:600;margin:.3rem;
     font-size:.9rem;transition:background .2s}
.btn:hover{background:#2ea043}
.btn-b{background:#1f6feb}.btn-b:hover{background:#388bfd}
#result{margin-top:1rem;padding:1rem;border-radius:8px;background:#0d1117;
        border:1px solid #30363d;font-family:monospace;font-size:.85rem;display:none}
.obs{border-left:4px solid #f85149}.free{border-left:4px solid #3fb950}
a.lnk{background:#21262d;border:1px solid #30363d;padding:.3rem .7rem;
      border-radius:6px;font-size:.8rem;color:#58a6ff;text-decoration:none;
      margin-right:.5rem}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;
     background:#3fb950;margin-right:6px;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
</style></head><body>
<h1>UAV Obstacle Detection Service</h1>
<p class="sub">Yachay Tech — MLOps Sprint | Apollo-UAV Architecture<br>
Impacto: Inspeccion subestaciones CENACE — Ecuador</p>

<div class="card">
  <h2><span class="dot"></span>Estado del Servicio</h2>
  <div class="row"><span class="lbl">Modelo</span><span class="val">ObstacleProxyModel</span></div>
  <div class="row"><span class="lbl">Produccion target</span><span class="val">YOLOv8-nano + Safe-PPO</span></div>
  <div class="row"><span class="lbl">Referencia tesis</span><span class="val">Corrida C9 — 4/6 KPIs</span></div>
  <div style="margin-top:.8rem">
    <a class="lnk" href="/metrics">Prometheus /metrics</a>
    <a class="lnk" href="/health">/health</a>
  </div>
</div>

<div class="card">
  <h2>Demo: Deteccion de Obstaculos</h2>
  <button class="btn"   onclick="send(true)">Frame con Obstaculo</button>
  <button class="btn btn-b" onclick="send(false)">Frame Camino Libre</button>
  <div id="result"></div>
</div>

<script>
function frame(obs){
  const a=new Float32Array(4096);
  for(let i=0;i<4096;i++) a[i]=obs?(0.55+Math.random()*0.45):(Math.random()*0.45);
  return btoa(String.fromCharCode(...new Uint8Array(a.buffer)));
}
async function send(obs){
  const d=document.getElementById('result');
  d.style.display='block';d.className='';d.textContent='Procesando...';
  try{
    const r=await fetch('/predict',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({frame:frame(obs)})});
    const j=await r.json();
    d.className=j.obstacle_detected?'obs':'free';
    d.innerHTML=`<strong>${j.obstacle_detected?'OBSTACULO DETECTADO':'CAMINO LIBRE'}</strong><br><br>
Confianza:    ${(j.confidence*100).toFixed(1)}%<br>
Latencia:     ${j.latency_ms} ms<br>
CBF activado: ${j.cbf_activated?'SI (barrier function activa)':'No'}<br>
P(libre):     ${(j.class_probs.free_path*100).toFixed(1)}%<br>
P(obstaculo): ${(j.class_probs.obstacle*100).toFixed(1)}%`;
  }catch(e){d.textContent='Error: '+e.message}
}
</script></body></html>
"""

def run_inference(frame_bytes):
    arr = np.frombuffer(frame_bytes, dtype=np.float32)
    if len(arr) < 4096:
        arr = np.pad(arr, (0, 4096-len(arr)))
    arr = arr[:4096].reshape(1,-1)
    t0 = time.perf_counter()
    with torch.no_grad():
        logits = model(torch.tensor(arr, dtype=torch.float32))
        probs  = torch.softmax(logits, dim=1).squeeze().numpy()
    lat = (time.perf_counter()-t0)*1000
    idx = int(np.argmax(probs))
    conf = float(probs[idx])
    cbf = bool(idx==1 and conf>0.85)
    return {"obstacle_detected": bool(idx==1), "confidence": round(conf,4),
            "latency_ms": round(lat,2), "cbf_activated": cbf,
            "class_probs": {"free_path": round(float(probs[0]),4),
                            "obstacle":  round(float(probs[1]),4)}}

@app.route("/")
def index(): return render_template_string(UI)

@app.route("/predict", methods=["POST"])
def predict():
    FRAMES_TOTAL.inc()
    try:
        data = request.get_json(force=True)
        if not data or "frame" not in data:
            ERRORS.inc()
            return jsonify({"error": "Campo 'frame' requerido"}), 400
        result = run_inference(base64.b64decode(data["frame"]))
        LATENCY.observe(result["latency_ms"]/1000)
        CONFIDENCE.set(result["confidence"])
        (OBSTACLE_DETECTED if result["obstacle_detected"] else FREE_PATH).inc()
        if result["cbf_activated"]: CBF_ACTIVATIONS.inc()
        return jsonify(result)
    except Exception as e:
        ERRORS.inc()
        return jsonify({"error": str(e)}), 500

@app.route("/metrics")
def metrics(): return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}

@app.route("/health")
def health():
    return jsonify({"status":"healthy","model":"ObstacleProxyModel",
                    "service":"uav-inference","version":"1.0.0"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"[INFO] UAV Inference Service — http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
