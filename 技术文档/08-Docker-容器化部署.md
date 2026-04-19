# Docker — 容器化部署技术文档

---

## 1. 技术概述

Docker 是一个容器化平台，将应用及其所有依赖打包到一个可移植的容器中，确保在任何环境中都能一致运行。

| 项目 | 说明 |
|------|------|
| 官方文档 | https://docs.docker.com/ |
| 安装 | https://docs.docker.com/get-docker/ |
| 核心概念 | 镜像（Image）、容器（Container）、编排（Compose） |
| 在项目中的角色 | 打包 Agent 应用，实现一键部署 |

---

## 2. 安装 Docker

### 2.1 Windows

1. 下载 [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
2. 安装并启动 Docker Desktop
3. 验证：

```bash
docker --version
docker compose version
```

### 2.2 Linux (Ubuntu)

```bash
# 安装 Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 安装 Docker Compose
sudo apt install docker-compose-plugin

# 验证
docker --version
docker compose version
```

---

## 3. Dockerfile：构建镜像

### 3.1 什么是 Dockerfile

Dockerfile 是一个文本文件，包含构建 Docker 镜像的指令。每条指令对应镜像的一层。

### 3.2 本项目的 Dockerfile

```dockerfile
# === 第一阶段：构建镜像 ===

# 基础镜像（Python 运行环境）
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖文件（利用 Docker 缓存层）
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目源码
COPY . .

# 创建数据和日志目录
RUN mkdir -p /app/data /app/logs

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# 暴露端口
EXPOSE 8000

# 健康检查（使用 Python 替代 curl，因为 slim 镜像不含 curl）
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# 启动命令
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3.3 Dockerfile 指令说明

| 指令 | 说明 | 示例 |
|------|------|------|
| `FROM` | 基础镜像 | `FROM python:3.10-slim` |
| `WORKDIR` | 工作目录 | `WORKDIR /app` |
| `COPY` | 复制文件到镜像 | `COPY . .` |
| `RUN` | 构建时执行命令 | `RUN pip install -r requirements.txt` |
| `ENV` | 设置环境变量 | `ENV PORT=8000` |
| `EXPOSE` | 声明端口 | `EXPOSE 8000` |
| `CMD` | 容器启动命令 | `CMD ["uvicorn", ...]` |
| `HEALTHCHECK` | 健康检查 | `HEALTHCHECK CMD curl ...` |

### 3.4 .dockerignore

```
# .dockerignore — 排除不需要的文件
.git
__pycache__
*.pyc
venv/
.env
data/
logs/
htmlcov/
.vscode/
.idea/
*.md
tests/
```

---

## 4. Docker 镜像操作

### 4.1 构建镜像

```bash
# 构建并打标签
docker build -t agent-app:latest .
docker build -t agent-app:v1.0.0 .

# 查看本地镜像
docker images
```

### 4.2 运行容器

```bash
# 基本运行
docker run -d -p 8000:8000 --name agent agent-app

# 带环境变量
docker run -d -p 8000:8000 \
    -e LLM_API_KEY=sk-xxx \
    -e LLM_PROVIDER=deepseek \
    --name agent agent-app

# 带数据持久化
docker run -d -p 8000:8000 \
    -v $(pwd)/data:/app/data \
    -v $(pwd)/logs:/app/logs \
    --env-file .env \
    --name agent agent-app
```

### 4.3 容器管理

```bash
# 查看运行中的容器
docker ps

# 查看日志
docker logs agent
docker logs -f agent         # 实时跟踪

# 进入容器
docker exec -it agent bash

# 停止/启动/重启
docker stop agent
docker start agent
docker restart agent

# 删除容器
docker rm -f agent

# 删除镜像
docker rmi agent-app:latest
```

---

## 5. Docker Compose：多容器编排

### 5.1 docker-compose.yml

```yaml
# 注意：Docker Compose V2 已弃用 version 字段，直接省略即可

services:
  # Agent 应用服务
  agent:
    build: .
    container_name: agent-app
    ports:
      - "8000:8000"
    volumes:
      - sqlite_data:/app/data
      - vector_data:/app/data/agent_memory
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    depends_on:
      - prometheus

  # Prometheus 监控
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    restart: unless-stopped

  # Grafana 可视化
  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
    depends_on:
      - prometheus
    restart: unless-stopped

# 数据卷（持久化存储）
volumes:
  sqlite_data:
  vector_data:
  prometheus_data:
  grafana_data:
```

### 5.2 Compose 命令

```bash
# 构建并启动所有服务
docker compose up -d --build

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f agent

# 重启单个服务
docker compose restart agent

# 停止所有服务
docker compose down

# 停止并删除数据卷（谨慎！）
docker compose down -v

# 重新构建并启动
docker compose up -d --build --force-recreate
```

---

## 6. 完整部署流程

### 6.1 首次部署

```bash
# 1. 克隆项目
git clone https://github.com/your-org/agent-project.git
cd agent-project

# 2. 创建环境配置
cp .env.example .env
# 编辑 .env 填入 API Key

# 3. 构建并启动
docker compose up -d --build

# 4. 验证服务
curl http://localhost:8000/api/health
# {"code": 200, "msg": "Agent服务运行正常"}
```

### 6.2 更新部署

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 重新构建并启动
docker compose up -d --build --force-recreate agent

# 3. 验证
curl http://localhost:8000/api/health

# 4. 清理旧镜像
docker image prune -f
```

### 6.3 数据备份

```bash
# 备份 SQLite 数据
docker compose exec agent sqlite3 /app/data/agent.db ".backup /app/data/backup.db"
cp data/backup.db backup/agent_$(date +%Y%m%d).db

# 备份向量数据
tar -czf backup/vectors_$(date +%Y%m%d).tar.gz data/agent_memory/
```

---

## 7. 生产环境 Nginx 配置

```nginx
# /etc/nginx/conf.d/agent.conf
server {
    listen 80;
    server_name agent.yourdomain.com;

    # 请求体大小限制
    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # SSE 流式支持（关键）
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

---

## 8. 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 端口冲突 | 宿主端口被占用 | 修改 `-p` 映射端口 |
| 容器启动后立即退出 | 启动命令报错 | `docker logs <name>` 查看错误 |
| 数据丢失 | 未挂载数据卷 | 添加 `-v` 挂载或使用 named volumes |
| 镜像构建慢 | 网络或缓存问题 | 先 COPY requirements.txt 再 COPY 源码 |
| 健康检查失败 | 服务未就绪 | 增大 `start_period` |
| 权限问题 | 文件权限不匹配 | 确保容器用户有读写权限 |
