# LiteLLM — 多模型统一调用接口技术文档

---

## 1. 技术概述

LiteLLM 是一个统一的 LLM 调用库，用**同一套 API** 调用 100+ 大语言模型（OpenAI、Claude、DeepSeek、豆包、Gemini 等）。它将不同厂商的 API 差异封装在底层，上层只需修改 `model` 参数即可切换模型，**无需改动业务代码**。

打个比方：LiteLLM 就像一个"万能充电器"——不管你的手机是什么品牌，插上就能充。同理，不管你用的是 OpenAI、Claude 还是 DeepSeek，用同一套代码就能调用，只是换个"插头"（model 参数）而已。对于本项目来说，LiteLLM 的价值在于：我们可以在 DeepSeek（便宜）和 Claude（能力强）之间随时切换，而不用修改任何业务逻辑。

| 项目 | 说明 |
|------|------|
| 版本 | 1.83.3 |
| 语言 | Python |
| 官方文档 | https://docs.litellm.ai/ |
| 安装 | `pip install litellm` |
| 核心价值 | 一套代码调用所有 LLM |

---

## 2. 为什么需要 LiteLLM

### 2.1 没有 LiteLLM 时的痛点

在实际项目中，我们经常需要对比不同模型的效果，或者在某个模型不稳定时快速切换备用模型。如果没有统一接口，每换一个模型就要引入该厂商的 SDK、学习不同的 API 写法、修改大量业务代码，维护成本非常高。下面的代码展示了这种痛苦：

```python
# 每换一个模型就要改一套代码
import openai          # OpenAI SDK
import anthropic       # Claude SDK
from zhipuai import ZhipuAI  # 智谱 SDK

# OpenAI 调用
openai_client = openai.OpenAI(api_key="sk-xxx")
openai_client.chat.completions.create(model="gpt-4", messages=[...])

# Claude 调用（完全不同的 API）
claude_client = anthropic.Anthropic(api_key="sk-xxx")
claude_client.messages.create(model="claude-3", messages=[...])

# 切换成本极高
```

### 2.2 使用 LiteLLM 后

有了 LiteLLM，所有模型都用同一个 `completion()` 函数调用，唯一的区别就是 `model` 参数不同。这意味着你可以在不修改任何业务代码的情况下，通过修改配置文件来切换模型。下面的三行代码分别调用了三个不同的模型，但调用方式完全一致：

```python
from litellm import completion

# 只需改 model 参数，其他代码完全不变
response = completion(model="openai/gpt-4", messages=[...], api_key="...")
response = completion(model="claude-3-opus", messages=[...], api_key="...")
response = completion(model="deepseek/deepseek-chat", messages=[...], api_key="...")
```

---

## 3. 安装与配置

### 3.1 安装

```bash
pip install litellm
# 当前最新版本：1.83.3（2026 年 4 月）
```

### 3.2 环境变量配置

```env
# 方式一：直接在 .env 文件中配置
OPENAI_API_KEY=sk-xxxxxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxxxxx
DEEPSEEK_API_KEY=sk-xxxxxxxx

# 方式二：自定义 Base URL（国内中转/私有部署）
OPENAI_API_BASE=https://your-proxy.com/v1
```

### 3.3 验证安装

```python
from litellm import completion
response = completion(
    model="openai/gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Hello"}],
    api_key="your-key"
)
print(response.choices[0].message.content)
```

---

## 4. 模型命名规则

LiteLLM 使用 `provider/model` 格式指定模型，其中 `provider` 是模型提供商的名称，`model` 是该提供商下的具体模型名称。这个命名规则是 LiteLLM 识别模型并将其路由到正确 API 的关键。下表列出了本项目可能用到的模型及其配置要求：

| 提供商 | model 参数值 | 需要的 API Key |
|--------|-------------|---------------|
| OpenAI | `openai/gpt-4` | `OPENAI_API_KEY` |
| OpenAI | `openai/gpt-3.5-turbo` | `OPENAI_API_KEY` |
| Anthropic | `claude-3-opus-20240229` | `ANTHROPIC_API_KEY` |
| DeepSeek | `deepseek/deepseek-chat` | `DEEPSEEK_API_KEY` |
| 豆包（字节） | `doubao/doubao-pro` | `DOUBAO_API_KEY` |
| Google | `gemini/gemini-pro` | `GEMINI_API_KEY` |
| 智谱 | `zhipu/glm-4` | `ZHIPU_API_KEY` |
| 本地 Ollama | `ollama/llama3` | 无需 Key |
| Azure OpenAI | `azure/my-deployment` | `AZURE_API_KEY` |

---

## 5. 核心使用方法

这一节覆盖了日常开发中最常用的功能，从最基础的对话到流式输出、异步调用等进阶用法。每个示例都可以直接复制使用，只需替换 `api_key` 即可。

### 5.1 基础对话

最基本的使用方式：发送一条消息，获取模型的回复。`messages` 参数是一个消息列表，每条消息包含 `role`（角色）和 `content`（内容）。`system` 角色用于设定模型的行为方式，`user` 角色代表用户的输入。

```python
from litellm import completion

response = completion(
    model="deepseek/deepseek-chat",
    messages=[
        {"role": "system", "content": "你是一个有帮助的助手。"},
        {"role": "user", "content": "什么是机器学习？"}
    ],
    api_key="your-deepseek-key"
)

# 获取回复内容
answer = response.choices[0].message.content
print(answer)
```

### 5.2 带参数控制

通过调节参数可以控制模型的输出行为。最常用的是 `temperature`：值越低输出越确定（适合写代码），值越高输出越有创意（适合写作）。`max_tokens` 则限制了模型回复的最大长度，避免产生过长的回答消耗过多 Token。

```python
response = completion(
    model="deepseek/deepseek-chat",
    messages=[{"role": "user", "content": "写一首诗"}],
    api_key="your-key",
    temperature=0.7,      # 创造性：0=确定, 1=随机
    max_tokens=1000,      # 最大输出 Token 数
    top_p=0.9,            # 核采样
    stop=["。"],          # 停止词
)
```

**参数说明：**

| 参数 | 类型 | 说明 | 推荐值 |
|------|------|------|--------|
| `temperature` | float | 输出随机性 | 代码生成 0.1，对话 0.7 |
| `max_tokens` | int | 最大输出长度 | 512-4096 |
| `top_p` | float | 核采样概率 | 0.9 |
| `stop` | list | 遇到停止词即结束 | 按需设置 |

### 5.3 自定义 API Base URL

国内直连某些海外 API 可能网络不稳定，这时可以通过 `api_base` 参数指定一个中转代理地址。同样，如果你使用的是私有部署的模型服务（如通过 vLLM 部署的本地模型），也用这个参数来指定服务地址。

```python
response = completion(
    model="openai/gpt-4",
    messages=[{"role": "user", "content": "你好"}],
    api_key="your-key",
    api_base="https://your-proxy.com/v1"   # 自定义 API 地址
)
```

### 5.4 流式输出

流式输出是聊天类应用必备的功能——就像 ChatGPT 那样一个字一个字地"打"出来，而不是等很久才一次性显示全部内容。开启流式只需设置 `stream=True`，然后遍历返回的每个 chunk 即可。这在用户体验上会有很大的提升，尤其是生成较长回复时。

```python
from litellm import completion

response = completion(
    model="deepseek/deepseek-chat",
    messages=[{"role": "user", "content": "解释量子计算"}],
    api_key="your-key",
    stream=True   # 开启流式
)

for chunk in response:
    content = chunk.choices[0].delta.content or ""
    print(content, end="", flush=True)
```

### 5.5 异步调用

在 Web 服务（如 FastAPI）中，为了避免一个请求阻塞整个服务，需要使用异步调用。LiteLLM 提供了 `acompletion` 函数，用法和同步的 `completion` 完全一致，只需加上 `await` 关键字。这在并发处理多个用户请求时尤其重要。

```python
from litellm import acompletion

response = await acompletion(
    model="deepseek/deepseek-chat",
    messages=[{"role": "user", "content": "你好"}],
    api_key="your-key"
)
print(response.choices[0].message.content)
```

### 5.6 异步流式

将异步和流式结合起来，就是 Web 应用中最常见的模式：既不阻塞服务器，又能逐字返回给用户。使用 `async for` 来遍历流式响应的每个 chunk。

```python
from litellm import acompletion

response = await acompletion(
    model="deepseek/deepseek-chat",
    messages=[{"role": "user", "content": "解释深度学习"}],
    api_key="your-key",
    stream=True
)

async for chunk in response:
    content = chunk.choices[0].delta.content or ""
    print(content, end="", flush=True)
```

---

## 6. 工具调用（Function Calling）

工具调用是 LLM 连接外部世界的关键能力。简单来说，当你问"北京天气怎么样"时，模型本身并不知道实时天气，但它可以"决定"调用一个天气查询工具来获取信息，然后把工具返回的结果组织成自然语言回复给你。整个过程分三步：定义工具 → 模型决定调用 → 执行工具并返回结果。

### 6.1 定义工具

首先，我们需要告诉模型有哪些工具可以用。每个工具就是一个 JSON Schema 描述，包含工具名称、功能描述和参数定义。描述越清晰，模型就越能准确判断什么时候该调用哪个工具。

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称"
                    }
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "执行数学计算",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "数学表达式"
                    }
                },
                "required": ["expression"]
            }
        }
    }
]
```

### 6.2 发送工具调用请求

把工具定义传给模型后，模型会分析用户的问题，判断是否需要调用工具。如果需要，返回的不再是普通的文本回复，而是一个 `tool_calls` 对象，告诉我们它想调用哪个函数、传什么参数。

```python
response = completion(
    model="deepseek/deepseek-chat",
    messages=[{"role": "user", "content": "北京天气怎么样？"}],
    tools=tools,
    api_key="your-key"
)

# 检查是否触发了工具调用
message = response.choices[0].message

if message.tool_calls:
    for tool_call in message.tool_calls:
        func_name = tool_call.function.name
        func_args = tool_call.function.arguments
        print(f"模型想调用: {func_name}({func_args})")
        # 输出：模型想调用: get_weather({"city": "北京"})
```

### 6.3 返回工具结果并继续对话

这是最关键的一步：拿到工具的执行结果后，需要把它作为一条 `role: "tool"` 的消息追加到对话历史中，再次调用模型。模型会综合用户原始问题和工具返回的结果，生成最终的自然语言回复。注意 `tool_call_id` 必须和第一轮返回的 id 对应上，这样模型才能把结果和对应的工具调用关联起来。

```python
import json

# 第一轮：模型决定调用工具
response_1 = completion(
    model="deepseek/deepseek-chat",
    messages=[{"role": "user", "content": "北京天气怎么样？"}],
    tools=tools,
    api_key="your-key"
)

# 执行工具
tool_call = response_1.choices[0].message.tool_calls[0]
weather_result = "北京：晴天，气温 25°C"

# 第二轮：将工具结果返回给模型
response_2 = completion(
    model="deepseek/deepseek-chat",
    messages=[
        {"role": "user", "content": "北京天气怎么样？"},
        response_1.choices[0].message,                        # 模型的工具调用
        {"role": "tool", "tool_call_id": tool_call.id,        # 工具结果
         "content": weather_result}
    ],
    tools=tools,
    api_key="your-key"
)

print(response_2.choices[0].message.content)
# 输出：北京现在是晴天，气温25°C，适合外出。
```

---

## 7. 在项目中集成 LiteLLM

本节展示如何在实际项目中使用 LiteLLM。核心思路是"配置驱动"：把模型选择、API Key 等信息放在 `.env` 配置文件中，代码通过读取配置来决定调用哪个模型。这样切换模型时只需修改配置文件，完全不需要改代码。

### 7.1 配置驱动切换

使用 Pydantic 的 `BaseSettings` 来管理配置，它会自动从 `.env` 文件中读取环境变量。这种方式的好处是类型安全（自动转换类型）且有默认值，即使缺少某些配置也不会报错。

```python
# config/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    LLM_PROVIDER: str = "deepseek"
    LLM_MODEL: str = "deepseek-chat"
    LLM_API_KEY: str = ""
    LLM_API_BASE: str = ""
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2000

    class Config:
        env_file = ".env"

settings = Settings()
```

### 7.2 封装 LLM 调用

将 LiteLLM 的调用封装成 `chat()` 和 `achat()` 两个函数，分别对应同步和异步调用。这样项目中的其他模块只需要调用这两个函数即可，不需要关心底层用的是哪个模型、哪个 API。函数内部根据配置自动拼接 `provider/model` 格式的模型名称，并处理可选参数（如自定义 API 地址、工具调用等）。

```python
# core/llm.py
from litellm import completion, acompletion
from config.settings import settings

def chat(messages: list, tools: list = None, stream: bool = False):
    """统一的 LLM 调用接口"""
    params = {
        "model": f"{settings.LLM_PROVIDER}/{settings.LLM_MODEL}",
        "messages": messages,
        "api_key": settings.LLM_API_KEY,
        "temperature": settings.LLM_TEMPERATURE,
        "max_tokens": settings.LLM_MAX_TOKENS,
    }
    if settings.LLM_API_BASE:
        params["api_base"] = settings.LLM_API_BASE
    if tools:
        params["tools"] = tools
    if stream:
        params["stream"] = True

    return completion(**params)

async def achat(messages: list, tools: list = None, stream: bool = False):
    """异步 LLM 调用"""
    params = {
        "model": f"{settings.LLM_PROVIDER}/{settings.LLM_MODEL}",
        "messages": messages,
        "api_key": settings.LLM_API_KEY,
        "temperature": settings.LLM_TEMPERATURE,
        "max_tokens": settings.LLM_MAX_TOKENS,
    }
    if settings.LLM_API_BASE:
        params["api_base"] = settings.LLM_API_BASE
    if tools:
        params["tools"] = tools
    if stream:
        params["stream"] = True

    return await acompletion(**params)
```

### 7.3 切换模型只需修改 .env

这是 LiteLLM 最大的便利之处。当你想把模型从 DeepSeek 切换到 OpenAI 时，只需要修改 `.env` 文件中的三行配置，重启服务即可生效。所有使用 `chat()` 函数的地方都会自动使用新模型，无需任何代码改动。

```env
# 使用 DeepSeek
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-chat
LLM_API_KEY=sk-xxx
LLM_API_BASE=https://api.deepseek.com/v1

# 切换到 OpenAI（只改这三行）
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
LLM_API_KEY=sk-xxx
```

---

## 8. 常见问题

在使用 LiteLLM 的过程中，你可能会遇到以下常见问题。大多数问题都与 API Key 配置、网络连接或模型名称格式有关。

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| `AuthenticationError` | API Key 无效 | 检查环境变量和 Key 有效性 |
| `RateLimitError` | 请求过于频繁 | 降低并发，添加重试逻辑 |
| `ModelError` | 模型名称格式错误 | 确认使用 `provider/model` 格式 |
| 连接超时 | 网络问题 | 配置 `api_base` 使用代理 |
| 工具调用不触发 | 模型不支持 | 确认模型支持 Function Calling |

### 错误处理最佳实践

在生产环境中，LLM 调用可能因为网络波动、API 限流等原因失败。推荐的应对策略是"指数退避重试"：第一次失败等 1 秒重试，第二次等 2 秒，第三次等 4 秒，以此类推。这样既不会频繁请求导致被封，也能在临时故障时自动恢复。

```python
from litellm import completion
import time

def chat_with_retry(messages, max_retries=3):
    """带重试的 LLM 调用"""
    for attempt in range(max_retries):
        try:
            return completion(
                model="deepseek/deepseek-chat",
                messages=messages,
                api_key="your-key"
            )
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt  # 指数退避：1s, 2s, 4s
                time.sleep(wait)
            else:
                raise
```
