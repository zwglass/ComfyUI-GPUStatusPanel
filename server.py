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


_lock = Lock()
_cache = {"ts": 0, "data": None}
CACHE_TTL_SEC = 1.0  # 1秒刷新一次，别太频繁


def _bytes_to_mib(x: int) -> float:
    return round(x / (1024 * 1024), 1)


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
    if _NVML_OK:
        try:
            pynvml.nvmlInit()
            count = pynvml.nvmlDeviceGetCount()
            data["backend"] = "nvml"
            for i in range(count):
                h = pynvml.nvmlDeviceGetHandleByIndex(i)
                name = pynvml.nvmlDeviceGetName(h).decode("utf-8", "ignore")

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
            data["ok"] = False
            data["error"] = f"NVML error: {e}"

    # Fallback: torch.cuda (only gives mem; util/temp not available)
    elif _TORCH_OK and getattr(torch, "cuda", None) and torch.cuda.is_available():
        data["backend"] = "torch.cuda"
        try:
            n = torch.cuda.device_count()
            for i in range(n):
                props = torch.cuda.get_device_properties(i)
                total = props.total_memory
                # 注意：memory_allocated 是“已分配给张量”的，memory_reserved 更接近占用
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

    # MPS / CPU only
    else:
        data["backend"] = "none"
        data["ok"] = False
        data["error"] = "No NVML and no CUDA available (maybe MPS/CPU)."

    with _lock:
        _cache["ts"] = time.time()
        _cache["data"] = data
    return data


def setup_routes(app: web.Application):
    async def handle_status(request):
        return web.json_response(get_gpu_status())

    app.router.add_get("/gpu_status", handle_status)
