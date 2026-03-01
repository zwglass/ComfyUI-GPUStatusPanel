// 简单浮层：每1秒请求一次 /gpu_status，并显示 GPU/显存/温度
const POLL_MS = 1000;

function formatGpu(g) {
  const mem = `${g.mem_used_mib}/${g.mem_total_mib} MiB`;
  const util = (g.util_gpu === null || g.util_gpu === undefined) ? "NA" : `${g.util_gpu}%`;
  const temp = (g.temp_c === null || g.temp_c === undefined) ? "NA" : `${g.temp_c}°C`;
  return `GPU${g.index}: ${g.name}\nUtil: ${util}  VRAM: ${mem}  Temp: ${temp}`;
}

function createPanel() {
  const panel = document.createElement("div");
  panel.id = "gpu-status-panel";
  panel.style.position = "fixed";
  panel.style.top = "10px";
  panel.style.right = "10px";
  panel.style.zIndex = "99999";
  panel.style.whiteSpace = "pre";
  panel.style.fontFamily = "monospace";
  panel.style.fontSize = "12px";
  panel.style.padding = "8px 10px";
  panel.style.borderRadius = "8px";
  panel.style.background = "rgba(0,0,0,0.65)";
  panel.style.color = "white";
  panel.style.maxWidth = "420px";
  panel.style.pointerEvents = "none"; // 不挡操作
  panel.textContent = "GPU: loading...";
  document.body.appendChild(panel);
  return panel;
}

async function poll(panel) {
  try {
    const res = await fetch("/gpu_status", { cache: "no-store" });
    const data = await res.json();
    if (!data.ok) {
      panel.textContent = `GPU: ${data.backend}\n${data.error || "error"}`;
      return;
    }
    const lines = [];
    lines.push(`Backend: ${data.backend}`);
    for (const g of data.gpus) lines.push(formatGpu(g));
    panel.textContent = lines.join("\n\n");
  } catch (e) {
    panel.textContent = `GPU: fetch error\n${e}`;
  }
}

function start() {
  const panel = createPanel();
  poll(panel);
  setInterval(() => poll(panel), POLL_MS);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", start);
} else {
  start();
}
