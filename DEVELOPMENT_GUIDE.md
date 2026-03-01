# ComfyUI 自定义节点开发规范

> 基于 ComfyUI 官方文档整理，用于指导本项目的开发

## 1. 项目文件结构

```
ComfyUI-GPUStatusPanel/
├── __init__.py           # 节点注册入口，必须导出 NODE_CLASS_MAPPINGS
├── server.py             # 后端服务器路由和 GPU 状态检测逻辑
├── requirements.txt      # Python 依赖
├── js/
│   └── main.js          # 前端扩展脚本
└── nodes.py (可选)       # 自定义节点类定义（如果需要实际节点）
```

## 2. 后端开发规范

### 2.1 __init__.py 必需导出

```python
# 节点类映射（必须有，即使没有实际节点）
NODE_CLASS_MAPPINGS = {}

# 节点显示名称映射（可选）
NODE_DISPLAY_NAME_MAPPINGS = {}

# Web 前端目录（启用前端扩展必需）
WEB_DIRECTORY = "./js"

# 导出列表
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
```

### 2.2 服务器路由扩展

ComfyUI 使用 aiohttp 作为 Web 框架。自定义节点可以通过两种方式添加路由：

#### 方式一：init_app 函数（推荐用于纯扩展）

```python
# __init__.py
def init_app(app):
    """ComfyUI 启动时会调用此函数（如果存在）"""
    setup_routes(app)
```

#### 方式二：标准节点类（用于功能节点）

```python
class ExampleNode:
    # 必需属性
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_name": ("DATA_TYPE", {options}),
            },
            "optional": {},
            "hidden": {},
        }
    
    RETURN_TYPES = ("OUTPUT_TYPE",)  # 注意末尾逗号！
    RETURN_NAMES = ("output_name",)  # 可选，输出显示名称
    CATEGORY = "category/subcategory"  # 菜单分类路径
    FUNCTION = "function_name"         # 要调用的方法名
    
    # 可选属性
    OUTPUT_NODE = True                 # 是否是输出节点
    
    def function_name(self, input_name):
        # 处理逻辑
        return (output_value,)  # 注意末尾逗号！
```

### 2.3 数据类型

常用输入/输出数据类型：

| 类型 | 说明 |
|------|------|
| `IMAGE` | 图像批次 (Tensor [B,H,W,C]) |
| `LATENT` | 潜空间数据 |
| `MODEL` | 扩散模型 |
| `CLIP` | CLIP 模型 |
| `VAE` | VAE 模型 |
| `CONDITIONING` | 条件数据 |
| `STRING` | 字符串 |
| `INT` | 整数 |
| `FLOAT` | 浮点数 |
| `BOOLEAN` | 布尔值 |

### 2.4 输入类型定义

```python
@classmethod
def INPUT_TYPES(cls):
    return {
        "required": {
            # 基础类型
            "int_input": ("INT", {"default": 0, "min": 0, "max": 100}),
            "float_input": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0, "step": 0.1}),
            "string_input": ("STRING", {"default": "", "multiline": True}),
            "dropdown": (["option1", "option2"],),  # 下拉选项
            
            # 连接类型
            "image": ("IMAGE",),
        },
        "optional": {
            "optional_input": ("STRING", {"default": ""}),
        },
        "hidden": {
            "prompt": "PROMPT",      # 工作流提示词
            "extra_pnginfo": "EXTRA_PNGINFO",
            "unique_id": "UNIQUE_ID", # 节点唯一ID
        }
    }
```

## 3. 前端开发规范

### 3.1 基本结构

```javascript
import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "unique.extension.name",
    
    // 初始化钩子
    async setup() {
        // 页面加载时执行
    },
    
    // 节点创建钩子
    async nodeCreated(node) {
        // 每当创建节点时执行
    },
    
    // 添加自定义节点类型
    registerCustomNodes() {
        // 注册自定义节点
    }
});
```

### 3.2 常用 API

```javascript
// 获取 ComfyUI API 对象
import { api } from "../../scripts/api.js";

// 发起 API 请求
const response = await api.fetchApi("/your_endpoint", {
    method: "GET",  // 或 "POST"
});
const data = await response.json();

// 获取当前工作流
const workflow = app.graph.serialize();

// 获取节点
const node = app.graph.getNodeById(nodeId);
```

### 3.3 前端文件加载

- `js/` 目录下的所有 `.js` 文件会自动加载
- 其他资源（CSS 等）需要通过编程方式添加：

```javascript
const link = document.createElement("link");
link.rel = "stylesheet";
link.href = "extensions/your_node_name/style.css";
document.head.appendChild(link);
```

## 4. 本项目特定规范

### 4.1 GPU 状态检测

- 优先使用 NVML (pynvml) 获取详细的 GPU 信息
- 回退到 torch.cuda 获取基本内存信息
- 支持 macOS MPS（通过 psutil 获取系统信息）

### 4.2 API 路由

```python
# GET /gpu_status
{
    "backend": "nvml" | "torch.cuda" | "mps" | "none",
    "ok": true | false,
    "error": "error message",  # 仅在 ok=false 时存在
    "gpus": [
        {
            "index": 0,
            "name": "NVIDIA GeForce RTX 4090",
            "util_gpu": 45,           # GPU 利用率 %
            "util_mem": 30,           # 显存利用率 %
            "mem_used_mib": 4096,     # 已用显存 MiB
            "mem_total_mib": 24576,   # 总显存 MiB
            "temp_c": 65,             # 温度 °C
            "power_w": 250.5          # 功耗 W
        }
    ]
}
```

### 4.3 前端面板

- 使用固定定位浮层显示 GPU 状态
- 每秒刷新一次数据
- 支持拖拽移动位置
- 支持最小化/关闭

## 5. 调试技巧

### 5.1 后端调试

```python
# 添加日志
print("[GPUStatusPanel] 日志信息")

# 异常处理时打印详细错误
import traceback
traceback.print_exc()
```

### 5.2 前端调试

```javascript
// 浏览器控制台查看
console.log("[GPUStatusPanel]", data);

// 捕获错误
window.addEventListener('error', (e) => {
    console.error("[GPUStatusPanel] Error:", e);
});
```

## 6. 参考资料

- [ComfyUI 官方文档](https://docs.comfy.org/)
- [自定义节点开发指南](https://docs.comfy.org/custom-nodes/walkthrough)
- [后端 API 文档](https://docs.comfy.org/custom-nodes/backend/server_overview)
- [前端扩展文档](https://docs.comfy.org/custom-nodes/js/javascript_overview)
- [路由文档](https://docs.comfy.org/development/comfyui-server/comms_routes)
