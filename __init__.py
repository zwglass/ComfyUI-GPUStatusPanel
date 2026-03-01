import os
import sys

# Import server functions
from .server import setup_routes, setup_routes_legacy, get_gpu_status

# 可选：添加一个测试节点，用于验证节点系统是否正常工作
class GPUStatusNode:
    """
    一个简单的测试节点，显示 GPU 状态信息
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "refresh": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("status_json",)
    FUNCTION = "get_status"
    CATEGORY = "system/GPUStatusPanel"
    OUTPUT_NODE = True

    def get_status(self, refresh=True):
        """返回 GPU 状态信息（JSON 字符串）"""
        import json
        status = get_gpu_status()
        return (json.dumps(status, indent=2),)


# 节点注册映射
NODE_CLASS_MAPPINGS = {
    "GPUStatusNode": GPUStatusNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GPUStatusNode": "GPU Status Info",
}

WEB_DIRECTORY = "./js"

# 尝试多种方式注册路由
def init_app(app):
    """Called by ComfyUI during startup (if supported)"""
    print("[GPUStatusPanel] init_app called")
    setup_routes(app)

# 尝试从 comfy 导入并注册
try:
    # 尝试获取 PromptServer 实例并注册
    import server
    if hasattr(server, 'PromptServer') and server.PromptServer.instance is not None:
        setup_routes_legacy(server.PromptServer.instance)
except Exception as e:
    pass

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY", "init_app"]
