from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # LLM 配置
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-3.5-turbo"
    LLM_API_KEY: Optional[str] = None
    LLM_API_BASE: Optional[str] = None
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2000

    # 嵌入模型
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # 向量搜索
    VECTOR_SEARCH_LIMIT: int = 5

    # 文本分块
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    # 运行配置
    DEBUG: bool = False
    MAX_HISTORY_MESSAGES: int = 20

    # 数据库路径
    SQLITE_DB_PATH: str = "./data/agent.db"
    VECTOR_DB_PATH: str = "./data/agent_memory"

    class Config:
        env_file = ".env"


settings = Settings()
