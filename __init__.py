from .server import setup_routes

# ComfyUI will call this if present in custom_nodes
def init_app(app):
    setup_routes(app)

# 没有自定义节点也没关系，保持这个文件存在即可
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

WEB_DIRECTORY = "./js"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
