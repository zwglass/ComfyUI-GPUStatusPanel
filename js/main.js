// GPU 状态面板 - ComfyUI 扩展
import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const POLL_MS = 1000;
const STORAGE_KEY = "gpu-status-panel-pos";
const STORAGE_VISIBLE = "gpu-status-panel-visible";

// 根据百分比获取颜色
function getColor(percent) {
  if (percent === null || percent === undefined) return "#888";
  if (percent < 50) return "#4ade80"; // 绿色
  if (percent < 80) return "#fbbf24"; // 黄色
  return "#f87171"; // 红色
}

// 创建进度条 HTML
function createProgressBar(value, max, label, unit = "%") {
  if (value === null || value === undefined) {
    return `<div class="gpu-bar-row"><span class="gpu-bar-label">${label}</span><span class="gpu-bar-na">N/A</span></div>`;
  }
  const percent = max ? (value / max * 100) : value;
  const color = getColor(percent);
  const displayValue = max ? `${value}/${max}${unit}` : `${value}${unit}`;
  
  return `
    <div class="gpu-bar-row">
      <span class="gpu-bar-label">${label}</span>
      <div class="gpu-bar-container">
        <div class="gpu-bar-fill" style="width: ${Math.min(percent, 100)}%; background: ${color};"></div>
      </div>
      <span class="gpu-bar-value">${displayValue}</span>
    </div>
  `;
}

// 创建 GPU 卡片
function createGpuCard(g) {
  const memPercent = g.mem_total_mib ? (g.mem_used_mib / g.mem_total_mib * 100) : null;
  
  return `
    <div class="gpu-card">
      <div class="gpu-header">
        <span class="gpu-name">${g.name}</span>
        <span class="gpu-index">#${g.index}</span>
      </div>
      ${createProgressBar(g.util_gpu, 100, "GPU", "%")}
      ${createProgressBar(g.mem_used_mib, g.mem_total_mib, "VRAM", " MiB")}
      ${g.temp_c !== null ? createProgressBar(g.temp_c, 100, "Temp", "°C") : ""}
      ${g.power_w !== null ? `<div class="gpu-info-row"><span>Power: ${g.power_w}W</span></div>` : ""}
    </div>
  `;
}

function createPanel() {
  const container = document.createElement("div");
  container.id = "gpu-status-container";
  
  // 添加样式
  const style = document.createElement("style");
  style.textContent = `
    #gpu-status-container {
      position: fixed;
      top: 10px;
      right: 10px;
      z-index: 99999;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
      font-size: 12px;
      user-select: none;
      min-width: 320px;
    }
    #gpu-status-header {
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      color: #4ade80;
      padding: 10px 15px;
      border-radius: 12px 12px 0 0;
      cursor: move;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid #333;
      box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    #gpu-status-header .title {
      font-weight: 600;
      font-size: 14px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    #gpu-status-header .controls {
      display: flex;
      gap: 8px;
    }
    #gpu-status-header .controls span {
      cursor: pointer;
      padding: 4px 8px;
      border-radius: 6px;
      transition: background 0.2s;
    }
    #gpu-status-header .controls span:hover {
      background: rgba(255,255,255,0.1);
    }
    #gpu-status-panel {
      background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 100%);
      padding: 15px;
      border-radius: 0 0 12px 12px;
      color: #e0e0e0;
      max-width: 400px;
      box-shadow: 0 10px 25px rgba(0,0,0,0.5);
      border: 1px solid #333;
      border-top: none;
    }
    .gpu-backend {
      font-size: 11px;
      color: #888;
      margin-bottom: 12px;
      padding-bottom: 10px;
      border-bottom: 1px solid #333;
    }
    .gpu-card {
      background: rgba(255,255,255,0.03);
      border-radius: 10px;
      padding: 12px;
      margin-bottom: 12px;
      border: 1px solid rgba(255,255,255,0.05);
    }
    .gpu-card:last-child {
      margin-bottom: 0;
    }
    .gpu-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
    }
    .gpu-name {
      font-weight: 600;
      color: #fff;
      font-size: 13px;
    }
    .gpu-index {
      font-size: 11px;
      color: #666;
      background: rgba(255,255,255,0.05);
      padding: 2px 8px;
      border-radius: 12px;
    }
    .gpu-bar-row {
      display: flex;
      align-items: center;
      margin-bottom: 8px;
      gap: 10px;
    }
    .gpu-bar-row:last-child {
      margin-bottom: 0;
    }
    .gpu-bar-label {
      width: 50px;
      color: #888;
      font-size: 11px;
    }
    .gpu-bar-container {
      flex: 1;
      height: 8px;
      background: rgba(255,255,255,0.1);
      border-radius: 4px;
      overflow: hidden;
      position: relative;
    }
    .gpu-bar-fill {
      height: 100%;
      border-radius: 4px;
      transition: width 0.3s ease, background 0.3s ease;
      box-shadow: 0 0 10px rgba(74, 222, 128, 0.3);
    }
    .gpu-bar-value {
      width: 80px;
      text-align: right;
      font-size: 11px;
      color: #ccc;
      font-variant-numeric: tabular-nums;
    }
    .gpu-bar-na {
      color: #666;
      font-style: italic;
    }
    .gpu-info-row {
      font-size: 11px;
      color: #888;
      margin-top: 8px;
      padding-top: 8px;
      border-top: 1px solid rgba(255,255,255,0.05);
    }
    .gpu-error {
      color: #f87171;
      padding: 20px;
      text-align: center;
    }
    .gpu-loading {
      color: #888;
      padding: 20px;
      text-align: center;
    }
  `;
  document.head.appendChild(style);

  // 标题栏
  const header = document.createElement("div");
  header.id = "gpu-status-header";
  header.innerHTML = `
    <span class="title">🖥️ GPU Status</span>
    <span class="controls">
      <span id="gpu-status-toggle" title="Minimize">−</span>
      <span id="gpu-status-close" title="Close">×</span>
    </span>
  `;

  // 内容区域
  const panel = document.createElement("div");
  panel.id = "gpu-status-panel";
  panel.innerHTML = '<div class="gpu-loading">Loading GPU status...</div>';

  container.appendChild(header);
  container.appendChild(panel);
  document.body.appendChild(container);

  // 恢复位置
  const savedPos = localStorage.getItem(STORAGE_KEY);
  if (savedPos) {
    try {
      const pos = JSON.parse(savedPos);
      container.style.top = pos.top;
      container.style.left = pos.left;
      container.style.right = "auto";
    } catch (e) {}
  }

  // 恢复可见性
  const savedVisible = localStorage.getItem(STORAGE_VISIBLE);
  if (savedVisible === "false") {
    panel.style.display = "none";
    header.querySelector("#gpu-status-toggle").textContent = "+";
  }

  // 拖拽功能
  let isDragging = false;
  let startX, startY, startLeft, startTop;

  header.addEventListener("mousedown", (e) => {
    if (e.target.id === "gpu-status-toggle" || e.target.id === "gpu-status-close") return;
    isDragging = true;
    startX = e.clientX;
    startY = e.clientY;
    const rect = container.getBoundingClientRect();
    startLeft = rect.left;
    startTop = rect.top;
    container.style.transition = "none";
  });

  document.addEventListener("mousemove", (e) => {
    if (!isDragging) return;
    const dx = e.clientX - startX;
    const dy = e.clientY - startY;
    container.style.left = `${startLeft + dx}px`;
    container.style.top = `${startTop + dy}px`;
    container.style.right = "auto";
  });

  document.addEventListener("mouseup", () => {
    if (isDragging) {
      isDragging = false;
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        top: container.style.top,
        left: container.style.left
      }));
    }
  });

  // 最小化/展开
  header.querySelector("#gpu-status-toggle").addEventListener("click", (e) => {
    const isVisible = panel.style.display !== "none";
    panel.style.display = isVisible ? "none" : "block";
    e.target.textContent = isVisible ? "+" : "−";
    localStorage.setItem(STORAGE_VISIBLE, (!isVisible).toString());
  });

  // 关闭按钮
  header.querySelector("#gpu-status-close").addEventListener("click", () => {
    container.remove();
    localStorage.setItem(STORAGE_VISIBLE, "false");
  });

  return panel;
}

async function poll(panel) {
  try {
    const res = await api.fetchApi("/gpu_status", { cache: "no-store" });
    const data = await res.json();
    
    if (!data.ok) {
      panel.innerHTML = `<div class="gpu-error">⚠️ ${data.error || "GPU monitoring unavailable"}</div>`;
      return;
    }
    
    let html = `<div class="gpu-backend">Backend: ${data.backend}</div>`;
    
    for (const g of data.gpus) {
      html += createGpuCard(g);
    }
    
    panel.innerHTML = html;
  } catch (e) {
    panel.innerHTML = `<div class="gpu-error">⚠️ Connection error</div>`;
    console.error("[GPUStatusPanel] Fetch error:", e);
  }
}

function start() {
  const panel = createPanel();
  poll(panel);
  setInterval(() => poll(panel), POLL_MS);
}

// 注册扩展
app.registerExtension({
  name: "comfyui.gpu-status-panel",
  async setup() {
    console.log("[GPUStatusPanel] Extension loaded with visual bars");
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", start);
    } else {
      start();
    }
  }
});
