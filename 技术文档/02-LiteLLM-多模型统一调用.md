# LiteLLM — 多模型统一调用接口技术文档

---

## 1. 技术概述

LiteLLM 是一个统一的 LLM 调用库，用**同一套 API** 调用 100+ 大语言模型（OpenAI、Claude、DeepSeek、豆包、Gemini 等）。它将不同厂商的 API 差异封装在底层，上层只需修改 `model` 参数即可切换模型，**无需改动业务代码**。

| 项目 | 说明 |
|------|------|
| 版本 | 1.50.0 |
| 语言 | Python |
| 官方文档 | https://docs.litellm.ai/ |
| 安装 | `pip install litellm==1.50.0` |
| 核心价值 | 一套代码调用所有 LLM |

---

## 2. 为什么需要 LiteLLM

### 2.1 没有 LiteLLM 时的痛点

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
pip install litellm==1.50.0
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

LiteLLM 使用 `provider/model` 格式指定模型：

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

### 5.1 基础对话

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

用于国内代理或私有部署：

```python
response = completion(
    model="openai/gpt-4",
    messages=[{"role": "user", "content": "你好"}],
    api_key="your-key",
    api_base="https://your-proxy.com/v1"   # 自定义 API 地址
)
```

### 5.4 流式输出

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

### 6.1 定义工具

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

### 7.1 配置驱动切换

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

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| `AuthenticationError` | API Key 无效 | 检查环境变量和 Key 有效性 |
| `RateLimitError` | 请求过于频繁 | 降低并发，添加重试逻辑 |
| `ModelError` | 模型名称格式错误 | 确认使用 `provider/model` 格式 |
| 连接超时 | 网络问题 | 配置 `api_base` 使用代理 |
| 工具调用不触发 | 模型不支持 | 确认模型支持 Function Calling |

### 错误处理最佳实践

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
