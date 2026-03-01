# ComfyUI-GPUStatusPanel

Displays real-time GPU usage, VRAM consumption and temperature inside ComfyUI UI.

## Features

- **Multi-backend support**: NVIDIA (NVML), CUDA (torch), Apple Silicon (MPS), CPU fallback
- **Real-time monitoring**: Updates every second
- **Visual progress bars**: Color-coded GPU/VRAM/Temperature bars (green → yellow → red)
- **Draggable UI**: Move the panel anywhere on screen
- **Persistent position**: Remembers your preferred location
- **Minimize/Close controls**: Hide when not needed

## Screenshots

```
🖥️ GPU Status
─────────────────────────────────
Backend: mps
─────────────────────────────────
┌─────────────────────────────┐
│ Apple Silicon GPU (MPS)  #0 │
│ GPU  [░░░░░░░░] N/A         │
│ VRAM [██░░░░░░] 0.5/16384   │
└─────────────────────────────┘
```

## Installation

Clone into ComfyUI/custom_nodes:

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/zwglass/ComfyUI-GPUStatusPanel.git
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Restart ComfyUI.

## Supported Platforms

| Platform | Backend | GPU Util | VRAM | Temperature | Power |
|----------|---------|----------|------|-------------|-------|
| NVIDIA GPU | NVML | ✅ | ✅ | ✅ | ✅ |
| NVIDIA GPU | torch.cuda | ❌ | ✅ | ❌ | ❌ |
| Apple Silicon | MPS | ❌ | ✅* | ❌ | ❌ |
| CPU | psutil | ✅ | ✅ | ❌ | ❌ |

*MPS shows system memory as GPU memory reference

## Usage

Once installed and ComfyUI is restarted, a GPU status panel will appear in the top-right corner of the interface:

- **Drag** the header to move the panel
- **Click −** to minimize/restore the panel
- **Click ×** to close the panel (refresh page to restore)

## API

The plugin exposes a simple HTTP endpoint:

```
GET /gpu_status
```

Response:
```json
{
  "backend": "nvml",
  "ok": true,
  "gpus": [
    {
      "index": 0,
      "name": "NVIDIA GeForce RTX 4090",
      "util_gpu": 45,
      "util_mem": 30,
      "mem_used_mib": 4096,
      "mem_total_mib": 24576,
      "temp_c": 65,
      "power_w": 250.5
    }
  ]
}
```

## Development

See [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) for ComfyUI custom node development guidelines.

## License

MIT
