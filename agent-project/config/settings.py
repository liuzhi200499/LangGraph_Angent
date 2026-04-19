"""
配置管理模块
使用 Pydantic BaseSettings 实现类型安全的配置管理，自动从 .env 文件加载环境变量。
所有配置项均设有默认值，确保项目开箱即用。
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """全局配置类，所有字段自动从环境变量或 .env 文件读取"""

    # === LLM 大语言模型配置 ===
    LLM_PROVIDER: str = "openai"           # LLM 提供商名称，用于 LiteLLM 路由
    LLM_MODEL: str = "gpt-3.5-turbo"       # 模型标识，如 gpt-3.5-turbo、deepseek-chat
    LLM_API_KEY: Optional[str] = None      # API 密钥，必填项
    LLM_API_BASE: Optional[str] = None     # API 基础地址，用于兼容 OpenAI 格式的接口
    LLM_TEMPERATURE: float = 0.7           # 生成温度，0=确定性，1=随机性
    LLM_MAX_TOKENS: int = 2000             # 单次生成的最大 Token 数

    # === 嵌入模型配置 ===
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"  # 嵌入模型名称

    # === 向量搜索配置 ===
    VECTOR_SEARCH_LIMIT: int = 5           # 语义搜索返回的最大结果数

    # === 文本分块配置 ===
    CHUNK_SIZE: int = 500                  # 每个文本块的最大字符数
    CHUNK_OVERLAP: int = 50                # 相邻文本块之间的重叠字符数，保证上下文连续

    # === 运行配置 ===
    DEBUG: bool = False                    # 调试模式开关
    MAX_HISTORY_MESSAGES: int = 20         # 单个会话保留的最大历史消息数

    # === 数据库路径配置 ===
    SQLITE_DB_PATH: str = "./data/agent.db"      # SQLite 数据库文件路径
    VECTOR_DB_PATH: str = "./data/agent_memory"  # ChromaDB 向量数据库持久化目录

    class Config:
        env_file = ".env"  # 从项目根目录的 .env 文件加载配置


# 全局单例，供其他模块直接导入使用
settings = Settings()
