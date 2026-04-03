# AICG内容分发平台 - 后端服务

基于FastAPI的异步Web服务，提供AI驱动的长文本到视频转换功能。

## 功能特性

- 🚀 **异步架构**: FastAPI + SQLAlchemy 2.0 + asyncpg
- 📝 **智能解析**: 百万字级文档章节自动识别
- 🎬 **视频生成**: 
  - **智能缓存**: 增量生成视频，避免重复计算 (New!)
  - **多模态**: 集成 Flux/SDXL 绘图，支持多种 TTS 引擎
  - **字幕纠错**: 基于 LLM 的智能字幕校对
- 🔄 **任务队列**: Celery + Redis高并发处理
- 📊 **实时监控**: WebSocket进度推送 + Prometheus指标
- 🔐 **安全认证**: JWT + 密钥加密存储
- 📱 **多平台分发**: B站、YouTube等平台内容发布

## 技术栈

- **语言**: Python 3.11+
- **Web框架**: FastAPI 0.104+
- **数据库**: PostgreSQL 15+ (主), Redis 7.0 (缓存/队列)
- **ORM**: SQLAlchemy 2.0 (异步)
- **任务队列**: Celery 5.3+
- **对象存储**: MinIO
- **视频处理**: FFmpeg + ffmpeg-python
- **包管理**: uv

## 快速开始

### 1. 一键启动 (推荐)

```bash
# 使用Makefile快速启动开发环境
make setup
```

### 2. 手动启动

如果需要手动控制每个步骤：

```bash
# 安装uv (如果还没有安装)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 同步依赖
uv sync --index=https://pypi.tuna.tsinghua.edu.cn/simple

# GPU加速可选
uv pip install .[gpu] -i https://pypi.tuna.tsinghua.edu.cn/simple

# 运行数据库迁移
uv run alembic upgrade head

# 降级
alembic downgrade -1  # 回滚

# 启动API服务
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 启动完整服务

```bash
# 使用Makefile启动API服务
make start

# 启动Celery Worker (新终端)
make worker

# 启动Celery Beat (新终端)
make beat

# 或者使用快速命令启动完整环境
make dev
```

### 4. 环境配置

复制环境配置文件:
```bash
cp .env.example .env
```

编辑 `.env` 文件，配置数据库、Redis、MinIO等信息。

### 5. 访问API文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## Makefile 命令

项目提供了完整的Makefile来简化开发工作流：

### 核心命令

```bash
make help          # 显示所有可用命令
make setup         # 初始化开发环境 (依赖 + 迁移)
make start         # 启动开发服务器 (热重载)
make migrate       # 运行数据库迁移
make dev           # 显示完整开发环境启动指南
```

### 数据库操作

```bash
make migrate-create MSG="添加用户表"  # 创建新迁移
make migrate-down                     # 回滚最后一次迁移
make db-reset                          # 重置数据库 (危险!)
make db-status                         # 查看迁移状态
```

### 开发工具

```bash
make test           # 运行所有测试
make test-unit      # 运行单元测试
make test-fast      # 快速测试 (排除慢速测试)
make lint           # 代码检查和格式化
make format         # 格式化代码
make clean          # 清理临时文件
```

### Celery 任务

```bash
make worker         # 启动Celery Worker
make beat           # 启动Celery Beat (定时任务)
```

### 快捷别名

```bash
make s              # make start
make m              # make migrate
make t              # make test
make l              # make lint
make c              # make clean
```

## 开发指南

### 代码格式化

```bash
# 使用Makefile
make format

# 手动执行
uv run black src/ tests/
uv run isort src/ tests/

# 代码检查
make check
uv run flake8 src/ tests/
uv run mypy src/
```

### 运行测试

```bash
# 运行所有测试
uv run pytest

# 运行特定类型测试
uv run pytest -m unit
uv run pytest -m integration
uv run pytest -m e2e

# 生成覆盖率报告
uv run pytest --cov=src --cov-report=html
```

### 数据库操作

```bash
# 创建新迁移
uv run alembic revision --autogenerate -m "描述变更内容"

# 执行迁移
uv run alembic upgrade head

# 回滚迁移
uv run alembic downgrade -1

# 查看迁移历史
uv run alembic history
```

### 添加新依赖

```bash
# 添加生产依赖
uv add fastapi sqlalchemy

# 添加开发依赖
uv add --dev pytest black
```

## 项目结构

```
backend/
├── src/                   # 源代码
│   ├── models/           # SQLAlchemy数据模型
│   ├── services/         # 业务逻辑服务
│   ├── api/              # FastAPI路由
│   │   └── v1/          # API v1版本
│   ├── core/            # 核心组件(配置、数据库等)
│   ├── workers/         # Celery任务
│   ├── utils/           # 工具函数
│   └── main.py          # FastAPI应用入口
├── tests/               # 测试代码
│   ├── unit/           # 单元测试
│   ├── integration/    # 集成测试
│   └── contract/       # 合同测试
├── migrations/          # 数据库迁移文件
├── scripts/            # 脚本文件
├── pyproject.toml      # 项目配置
└── README.md          # 项目说明
```

## API文档

### 认证相关

- `POST /api/v1/auth/register` - 用户注册
- `POST /api/v1/auth/login` - 用户登录
- `GET /api/v1/auth/me` - 获取当前用户信息

### 项目管理

- `GET /api/v1/projects` - 获取项目列表
- `POST /api/v1/projects` - 创建新项目
- `GET /api/v1/projects/{id}` - 获取项目详情
- `PUT /api/v1/projects/{id}` - 更新项目
- `DELETE /api/v1/projects/{id}` - 删除项目

### 文件上传

- `POST /api/v1/upload` - 上传文件
- `DELETE /api/v1/files/{id}` - 删除文件

### 章节管理

- `GET /api/v1/chapters` - 获取章节列表
- `PUT /api/v1/chapters/{id}/confirm` - 确认章节
- `POST /api/v1/chapters/{id}/parse` - 解析章节

### 视频生成

- `POST /api/v1/generation/start` - 开始视频生成
- `GET /api/v1/generation/tasks/{id}/progress` - 获取生成进度
- `POST /api/v1/generation/tasks/{id}/pause` - 暂停生成任务
- `POST /api/v1/generation/tasks/{id}/resume` - 继续生成任务
- `POST /api/v1/generation/tasks/{id}/cancel` - 取消生成任务

## 环境变量

### 必需变量

```bash
# 数据库
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/aicg_db

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-super-secret-jwt-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=10080
```

### 可选变量

```bash
# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
MINIO_BUCKET_NAME=aicg-files

# 日志
LOG_LEVEL=INFO
STRUCTURED_LOGGING=true

# API
API_V1_PREFIX=/api/v1
CORS_ORIGINS=["http://localhost:3000"]

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
CELERY_WORKER_CONCURRENCY=4
```

## 监控

### 健康检查

- `GET /health` - 基础健康检查
- `GET /health/db` - 数据库连接检查
- `GET /health/redis` - Redis连接检查
- `GET /health/celery` - Celery状态检查

### Prometheus指标

访问 `http://localhost:8000/metrics` 获取Prometheus格式的指标数据。

### 彩色日志系统

系统提供智能的彩色日志输出：

**开发环境特性：**
- 🌈 **彩色输出** - 不同日志级别使用不同颜色 (INFO绿色, ERROR红色)
- 📍 **精确定位** - 显示模块、函数名和行号
- ⚡ **实时更新** - 热重载时日志自动刷新
- 🎯 **智能检测** - 自动检测终端颜色支持

**日志格式示例：**
```
14:32:15   INFO     [main] start_server 🚀 启动开发服务器...
14:32:15   INFO     [database] test_connection ✅ 数据库连接成功
14:32:16   WARNING  [auth] verify_token ⚠️ Token即将过期
14:32:17   ERROR    [api] handle_request ❌ 请求处理失败
```

**配置选项：**
```bash
# .env 文件中配置
COLORED_LOGS=true     # 启用彩色日志 (默认: true)
LOG_LEVEL=INFO         # 日志级别
STRUCTURED_LOGGING=true # 结构化日志到文件
```

**生产环境：**
- 自动切换到标准格式，确保兼容性
- 支持JSON结构化日志输出
- 可配置日志文件轮转

### 结构化日志

系统使用structlog进行结构化日志记录，支持JSON格式输出，便于日志聚合和分析。

## 部署

### Docker部署

```bash
# 构建镜像
docker build -t aicg-backend .

# 运行容器
docker run -d --name aicg-backend \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://... \
  -e REDIS_URL=redis://... \
  aicg-backend
```

### 生产环境配置

1. 使用生产级数据库连接池
2. 配置HTTPS和反向代理
3. 设置日志轮转
4. 配置监控告警
5. 设置自动备份

## 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查数据库服务状态
   - 验证连接字符串格式
   - 确认网络连通性

2. **Celery任务不执行**
   - 检查Redis连接
   - 确认Worker进程状态
   - 查看任务队列状态

3. **文件上传失败**
   - 检查MinIO服务状态
   - 验证存储桶权限
   - 确认文件大小限制

### 测试单个文件生成
```
uv run scripts/test_single_sentence_video.py --sentence-id 94673ecc-abe0-42ea-ae19-9d4a8bb95cc0 --api-key-id 6861e67b-6731-4dca-b215-aade208b627f
```


### 日志查看

```bash
# 查看应用日志
docker logs -f aicg-backend

# 查看特定组件日志
grep "ERROR" /var/log/aicg/backend.log
```

## 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交代码变更
4. 运行测试确保通过
5. 提交Pull Request

## 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 支持

- 文档: https://docs.aicg-platform.com
- 问题反馈: https://github.com/your-org/aicg-platform/issues
- 邮件: support@aicg-platform.com
