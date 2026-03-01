import time
from threading import Lock

# ComfyUI uses aiohttp under the hood
from aiohttp import web

try:
    import pynvml
    _NVML_OK = True
except Exception:
    print("[GPUStatusPanel] pynvml not installed, GPU stats disabled.")
    _NVML_OK = False

try:
    import torch
    _TORCH_OK = True
except Exception:
    _TORCH_OK = False

try:
    import psutil
    _PSUTIL_OK = True
except Exception:
    _PSUTIL_OK = False

_lock = Lock()
_cache = {"ts": 0, "data": None}
CACHE_TTL_SEC = 1.0  # 1秒刷新一次，别太频繁


def _bytes_to_mib(x: int) -> float:
    return round(x / (1024 * 1024), 1)


def _safe_decode_name(name):
    """兼容新旧版本 pynvml：新版本返回 str，旧版本返回 bytes"""
    if isinstance(name, bytes):
        return name.decode("utf-8", "ignore")
    return name


def get_gpu_status():
    """
    Return a dict safe for JSON serialization.
    """
    # cache to avoid NVML overhead & prevent UI spamming
    now = time.time()
    with _lock:
        if _cache["data"] is not None and now - _cache["ts"] < CACHE_TTL_SEC:
            return _cache["data"]

    data = {"backend": None, "gpus": [], "ok": True}

    # Prefer NVML (NVIDIA)
    nvml_failed = False
    if _NVML_OK:
        try:
            pynvml.nvmlInit()
            count = pynvml.nvmlDeviceGetCount()
            data["backend"] = "nvml"
            for i in range(count):
                h = pynvml.nvmlDeviceGetHandleByIndex(i)
                name = _safe_decode_name(pynvml.nvmlDeviceGetName(h))

                mem = pynvml.nvmlDeviceGetMemoryInfo(h)
                util = pynvml.nvmlDeviceGetUtilizationRates(h)

                # temperature might fail on some cards/drivers
                temp = None
                try:
                    temp = int(pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU))
                except Exception:
                    pass

                # power might fail too
                power_w = None
                try:
                    power_mw = pynvml.nvmlDeviceGetPowerUsage(h)  # milliwatts
                    power_w = round(power_mw / 1000.0, 1)
                except Exception:
                    pass

                data["gpus"].append({
                    "index": i,
                    "name": name,
                    "util_gpu": int(util.gpu),       # %
                    "util_mem": int(util.memory),    # %
                    "mem_used_mib": _bytes_to_mib(mem.used),
                    "mem_total_mib": _bytes_to_mib(mem.total),
                    "temp_c": temp,
                    "power_w": power_w,
                })
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass

        except Exception as e:
            nvml_failed = True
            # Don't set error yet, try other backends
            pass

    # Fallback: torch.cuda (only gives mem; util/temp not available)
    if not data["gpus"] and _TORCH_OK and getattr(torch, "cuda", None) and torch.cuda.is_available():
        data["backend"] = "torch.cuda"
        try:
            n = torch.cuda.device_count()
            for i in range(n):
                props = torch.cuda.get_device_properties(i)
                total = props.total_memory
                # 注意：memory_allocated 是"已分配给张量"的，memory_reserved 更接近占用
                used = torch.cuda.memory_reserved(i)
                data["gpus"].append({
                    "index": i,
                    "name": props.name,
                    "util_gpu": None,
                    "util_mem": None,
                    "mem_used_mib": _bytes_to_mib(used),
                    "mem_total_mib": _bytes_to_mib(total),
                    "temp_c": None,
                    "power_w": None,
                })
        except Exception as e:
            data["ok"] = False
            data["error"] = f"torch.cuda error: {e}"

    # Apple Silicon MPS support
    if not data["gpus"] and _TORCH_OK and getattr(torch, "mps", None) and torch.backends.mps.is_available():
        data["backend"] = "mps"
        try:
            # MPS 不直接提供显存统计，使用 psutil 获取系统内存作为参考
            if _PSUTIL_OK:
                mem = psutil.virtual_memory()
                # 获取 MPS 内存使用情况（如果可用）
                mps_allocated = 0
                mps_reserved = 0
                try:
                    mps_allocated = torch.mps.current_allocated_memory()
                    mps_reserved = torch.mps.driver_allocated_memory()
                except Exception:
                    pass

                data["gpus"].append({
                    "index": 0,
                    "name": "Apple Silicon GPU (MPS)",
                    "util_gpu": None,
                    "util_mem": round(mem.percent, 1) if hasattr(mem, 'percent') else None,
                    "mem_used_mib": _bytes_to_mib(mps_reserved if mps_reserved else mem.used),
                    "mem_total_mib": _bytes_to_mib(mem.total),
                    "temp_c": None,
                    "power_w": None,
                    "mps_allocated_mib": _bytes_to_mib(mps_allocated) if mps_allocated else None,
                })
            else:
                data["gpus"].append({
                    "index": 0,
                    "name": "Apple Silicon GPU (MPS)",
                    "util_gpu": None,
                    "util_mem": None,
                    "mem_used_mib": None,
                    "mem_total_mib": None,
                    "temp_c": None,
                    "power_w": None,
                })
        except Exception as e:
            data["ok"] = False
            data["error"] = f"MPS error: {e}"

    # CPU only
    if not data["gpus"] and _PSUTIL_OK:
        data["backend"] = "cpu"
        try:
            mem = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=None)
            data["gpus"].append({
                "index": 0,
                "name": "CPU (System Memory)",
                "util_gpu": round(cpu_percent, 1),
                "util_mem": round(mem.percent, 1) if hasattr(mem, 'percent') else None,
                "mem_used_mib": _bytes_to_mib(mem.used),
                "mem_total_mib": _bytes_to_mib(mem.total),
                "temp_c": None,
                "power_w": None,
            })
        except Exception as e:
            data["ok"] = False
            data["error"] = f"CPU error: {e}"

    if not data["gpus"]:
        data["backend"] = "none"
        data["ok"] = False
        data["error"] = "No GPU monitoring available (no NVML, CUDA, MPS, or psutil)."

    with _lock:
        _cache["ts"] = time.time()
        _cache["data"] = data
    return data


# Global flag to track if routes are registered
_routes_registered = False

def setup_routes(app: web.Application):
    """Setup GPU status API routes"""
    global _routes_registered
    if _routes_registered:
        return
    
    async def handle_status(request):
        return web.json_response(get_gpu_status())

    app.router.add_get("/gpu_status", handle_status)
    print("[GPUStatusPanel] GPU status endpoint registered at /gpu_status")
    _routes_registered = True


def setup_routes_legacy(server):
    """Legacy method to setup routes using PromptServer instance"""
    global _routes_registered
    if _routes_registered:
        return
    
    async def handle_status(request):
        return web.json_response(get_gpu_status())

    # Add to server's routes
    server.routes.get("/gpu_status")(handle_status)
    print("[GPUStatusPanel] GPU status endpoint registered at /gpu_status (legacy)")
    _routes_registered = True
