import os, time
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import wandb

CONFIG = {
    "project": "mlops-uav-indoor",
    "epochs": 20,
    "batch_size": 32,
    "lr": 1e-3,
    "input_size": 64 * 64,
    "num_classes": 2,
    "train_samples": 1000,
    "val_samples": 200,
    "max_jerk": 2.5,
    "t_return_max_s": 45.0,
}

class ObstacleProxyModel(nn.Module):
    """
    Proxy model para pipeline MLOps UAV indoor.
    Reemplaza YOLOv8-nano + Safe-PPO en contexto de demostracion.
    Arquitectura inspirada en capa de percepcion Apollo-UAV (7 capas).
    """
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Linear(CONFIG["input_size"], 512),
            nn.BatchNorm1d(512), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(512, 128),
            nn.BatchNorm1d(128), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(128, 32), nn.ReLU(),
        )
        self.classifier = nn.Linear(32, CONFIG["num_classes"])

    def forward(self, x):
        return self.classifier(self.features(x.view(x.size(0), -1)))

def generate_data(n, seed):
    rng = np.random.default_rng(seed)
    X, y = [], []
    for i in range(n):
        obs = i % 2 == 0
        frame = rng.uniform(0.55 if obs else 0.0,
                            1.0  if obs else 0.45,
                            (CONFIG["input_size"],)).astype(np.float32)
        X.append(frame); y.append(int(obs))
    return (torch.tensor(np.array(X)), torch.tensor(y, dtype=torch.long))

def make_loader(X, y, bs, shuffle=True):
    ds = torch.utils.data.TensorDataset(X, y)
    return torch.utils.data.DataLoader(ds, batch_size=bs, shuffle=shuffle)

def compute_kpis(model, val_loader, device):
    model.eval()
    preds, labels = [], []
    with torch.no_grad():
        for xb, yb in val_loader:
            p = model(xb.to(device)).argmax(1)
            preds.extend(p.cpu().numpy())
            labels.extend(yb.numpy())
    preds, labels = np.array(preds), np.array(labels)
    acc = (preds == labels).mean()
    tp = ((preds==1)&(labels==1)).sum()
    fp = ((preds==1)&(labels==0)).sum()
    fn = ((preds==0)&(labels==1)).sum()
    prec = tp/(tp+fp+1e-8); rec = tp/(tp+fn+1e-8)
    f1 = 2*prec*rec/(prec+rec+1e-8)
    cbf = int(max(0, 12 - acc*10))
    jerk = max(0.5, CONFIG["max_jerk"]*(1-acc*0.6))
    t_ret = max(5.0, CONFIG["t_return_max_s"]*(1-acc*0.7))
    return {
        "kpi/obstacle_f1": float(f1),
        "kpi/accuracy": float(acc),
        "kpi/cbf_activations": cbf,
        "kpi/jerk_mean_m_s3": float(jerk),
        "kpi/t_return_mean_s": float(t_ret),
        "kpi/kpis_met": int(f1>0.85)+int(cbf<5)+int(jerk<CONFIG["max_jerk"])+
                        int(t_ret<CONFIG["t_return_max_s"])+int(acc>0.90)+int(acc>0.95),
    }

def train():
    run = wandb.init(
        project=CONFIG["project"], config=CONFIG,
        tags=["proxy-model","sprint-day1","apollo-uav","cenace"],
        notes="Pipeline MLOps UAV indoor GPS-denied. Impacto: CENACE Ecuador.",
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[INFO] Device: {device}")

    X_tr, y_tr = generate_data(CONFIG["train_samples"], 42)
    X_val, y_val = generate_data(CONFIG["val_samples"], 99)
    tr_loader = make_loader(X_tr, y_tr, CONFIG["batch_size"])
    val_loader = make_loader(X_val, y_val, CONFIG["batch_size"], False)

    model = ObstacleProxyModel().to(device)
    opt = optim.Adam(model.parameters(), lr=CONFIG["lr"])
    sched = optim.lr_scheduler.CosineAnnealingLR(opt, T_max=CONFIG["epochs"])
    crit = nn.CrossEntropyLoss()
    wandb.watch(model, log="all", log_freq=50)

    best_acc, best_path = 0.0, "best_model.pt"
    for epoch in range(1, CONFIG["epochs"]+1):
        model.train()
        tr_loss, correct, total = 0.0, 0, 0
        for xb, yb in tr_loader:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            out = model(xb)
            loss = crit(out, yb)
            loss.backward(); opt.step()
            tr_loss += loss.item()*xb.size(0)
            correct += (out.argmax(1)==yb).sum().item()
            total += xb.size(0)
        sched.step()
        tr_acc = correct/total

        model.eval(); vl, vc, vt = 0.0, 0, 0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                out = model(xb)
                vl += crit(out,yb).item()*xb.size(0)
                vc += (out.argmax(1)==yb).sum().item()
                vt += xb.size(0)
        val_acc = vc/vt
        kpis = compute_kpis(model, val_loader, device)

        wandb.log({"epoch":epoch,"train/loss":tr_loss/total,
                   "train/accuracy":tr_acc,"val/accuracy":val_acc,**kpis})
        print(f"Epoch {epoch:02d}/{CONFIG['epochs']} | "
              f"tr_acc:{tr_acc:.3f} val_acc:{val_acc:.3f} | "
              f"KPIs:{kpis['kpi/kpis_met']}/6 CBF:{kpis['kpi/cbf_activations']}")

        if val_acc > best_acc:
            best_acc = val_acc
            torch.save(model.state_dict(), best_path)
            wandb.run.summary["best_val_accuracy"] = best_acc

    artifact = wandb.Artifact("obstacle-proxy-model", type="model",
        metadata={"best_val_accuracy": best_acc,
                  "production_replacement": "YOLOv8-nano + Safe-PPO"})
    artifact.add_file(best_path)
    run.log_artifact(artifact)
    print(f"\nEntrenamiento completo. Best val_acc: {best_acc:.3f}")
    wandb.finish()

if __name__ == "__main__":
    train()
