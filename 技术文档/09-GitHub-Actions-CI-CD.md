# GitHub Actions — CI/CD 流水线技术文档

---

## 1. 技术概述

GitHub Actions 是 GitHub 内置的持续集成/持续部署（CI/CD）平台，通过 YAML 配置文件定义自动化工作流，在代码推送、PR 创建等事件触发时自动执行测试、构建和部署。

| 项目 | 说明 |
|------|------|
| 官方文档 | https://docs.github.com/en/actions |
| 配置文件 | `.github/workflows/*.yml` |
| 触发方式 | push、PR、定时任务、手动 |
| 运行环境 | GitHub 提供的虚拟机（Ubuntu/Windows/macOS） |
| 在项目中的角色 | 自动化测试、构建镜像、部署服务 |

---

## 2. 核心概念

```
Workflow（工作流）
  │
  ├── Event（触发事件）    → 什么时候执行（push、PR、定时）
  │
  ├── Job（作业）          → 在同一虚拟机上执行的一组步骤
  │     │
  │     ├── Step 1         → 检出代码
  │     ├── Step 2         → 安装依赖
  │     ├── Step 3         → 运行测试
  │     └── Step 4         → 构建镜像
  │
  └── Runner（运行器）     → 执行 Job 的虚拟机
```

| 概念 | 说明 |
|------|------|
| **Workflow** | 一个完整的自动化流程，定义在 YAML 文件中 |
| **Event** | 触发工作流的事件（push、pull_request 等） |
| **Job** | 一组 Step 的集合，可并行或串行执行 |
| **Step** | 单个操作（运行命令或使用 Action） |
| **Action** | 可复用的操作单元（社区共享或自定义） |

---

## 3. 配置文件结构

### 3.1 创建工作流文件

```
项目根目录/
└── .github/
    └── workflows/
        ├── ci.yml          # 持续集成（测试）
        ├── build.yml       # 构建镜像
        └── deploy.yml      # 部署
```

### 3.2 基本结构

```yaml
name: 工作流名称

on:                     # 触发条件
  push:
    branches: [main]

jobs:                   # 作业列表
  job-name:
    runs-on: ubuntu-latest    # 运行环境
    steps:                    # 执行步骤
      - name: 步骤名
        run: echo "Hello"
```

---

## 4. 完整 CI/CD 流水线

### 4.1 完整配置

```yaml
# .github/workflows/ci.yml
name: Agent CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  # === 作业 1：测试 ===
  test:
    runs-on: ubuntu-latest
    steps:
      # 步骤 1：检出代码
      - name: Checkout code
        uses: actions/checkout@v5

      # 步骤 2：设置 Python 环境
      - name: Set up Python
        uses: actions/setup-python@v6
        with:
          python-version: "3.10"

      # 步骤 3：缓存依赖
      - name: Cache pip packages
        uses: actions/cache@v5
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-

      # 步骤 4：安装依赖
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov

      # 步骤 5：运行测试
      - name: Run tests
        run: pytest --cov=. --cov-report=xml --cov-report=term-missing -v

      # 步骤 6：检查覆盖率
      - name: Check coverage
        run: |
          coverage=$(python -c "
          import xml.etree.ElementTree as ET
          tree = ET.parse('coverage.xml')
          rate = tree.getroot().attrib['line-rate']
          print(float(rate) * 100)
          ")
          echo "Coverage: ${coverage}%"
          if (( $(echo "$coverage < 80" | bc -l) )); then
            echo "Coverage below 80%"
            exit 1
          fi

  # === 作业 2：构建 Docker 镜像 ===
  build:
    needs: test                    # 依赖 test 作业完成
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'  # 仅 main 分支触发
    steps:
      - name: Checkout code
        uses: actions/checkout@v5

      - name: Log in to Docker Hub
        uses: docker/login-action@v4
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}

      - name: Build and push Docker image
        uses: docker/build-push-action@v7
        with:
          context: .
          push: true
          tags: |
            ${{ secrets.DOCKER_USERNAME }}/agent:latest
            ${{ secrets.DOCKER_USERNAME }}/agent:${{ github.sha }}

  # === 作业 3：部署 ===
  deploy:
    needs: build                   # 依赖 build 作业完成
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to server
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/agent
            docker compose pull
            docker compose up -d --force-recreate
            sleep 5
            curl -f http://localhost:8000/api/health || exit 1
            echo "Deploy successful"
```

### 4.2 执行流程

```
代码推送到 main
  │
  ▼
┌──────────────┐
│   test 作业   │  运行测试、检查覆盖率
└──────┬───────┘
       │ 测试通过
       ▼
┌──────────────┐
│  build 作业   │  构建 Docker 镜像、推送到仓库
└──────┬───────┘
       │ 构建成功
       ▼
┌──────────────┐
│ deploy 作业   │  SSH 到服务器、拉取镜像、重启服务
└──────────────┘
```

---

## 5. Secrets 配置

在 GitHub 仓库中配置敏感信息：

1. 进入仓库 → Settings → Secrets and variables → Actions
2. 添加以下 Secrets：

| Secret 名称 | 说明 |
|-------------|------|
| `DOCKER_USERNAME` | Docker Hub 用户名 |
| `DOCKER_PASSWORD` | Docker Hub 密码/Token |
| `SERVER_HOST` | 服务器 IP 地址 |
| `SERVER_USER` | 服务器 SSH 用户名 |
| `SSH_PRIVATE_KEY` | SSH 私钥 |
| `LLM_API_KEY` | LLM API 密钥（构建测试用） |

---

## 6. 常用触发事件

```yaml
on:
  # push 到指定分支
  push:
    branches: [main, develop]

  # Pull Request
  pull_request:
    branches: [main]

  # 定时任务（cron 表达式，UTC 时间）
  schedule:
    - cron: "0 2 * * *"    # 每天 UTC 2:00（北京时间 10:00）

  # 手动触发
  workflow_dispatch:
    inputs:
      environment:
        description: "部署环境"
        required: true
        default: "staging"
        type: choice
        options:
          - staging
          - production

  # 其他工作流触发
  workflow_call:
```

---

## 7. 常用 Actions

| Action | 用途 | 示例 |
|--------|------|------|
| `actions/checkout@v5` | 检出代码 | 每个工作流第一步 |
| `actions/setup-python@v6` | 配置 Python | `python-version: "3.10"` |
| `actions/cache@v5` | 缓存依赖 | 缓存 pip 包 |
| `docker/login-action@v4` | Docker 登录 | 推送镜像前登录 |
| `docker/build-push-action@v7` | 构建推送镜像 | 一键构建并推送 |
| `appleboy/ssh-action@v1` | SSH 远程执行 | 远程部署命令 |

---

## 8. 本地验证工作流

在推送前可以使用 [act](https://github.com/nektos/act) 在本地测试：

```bash
# 安装 act
# macOS
brew install act
# Linux
curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# 本地运行工作流
act push                    # 模拟 push 事件
act -j test                 # 只运行 test 作业
act -n                      # 干跑（不实际执行，只检查语法）
```

---

## 9. 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 工作流未触发 | 分支或事件不匹配 | 检查 `on` 配置 |
| Secrets 找不到 | 未配置或名称错误 | 在仓库 Settings 中检查 |
| 测试步骤失败 | 依赖安装或测试失败 | 查看 Actions 日志定位 |
| Docker 登录失败 | 凭据错误 | 重新生成 Docker Token |
| SSH 连接失败 | 密钥格式问题 | 确保私钥完整（含 BEGIN/END 行） |
| 部署后服务异常 | 健康检查未通过 | 增加 `sleep` 等待时间 |
