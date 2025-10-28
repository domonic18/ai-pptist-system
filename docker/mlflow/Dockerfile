# MLflow Tracking Server Dockerfile
FROM python:3.11-slim

# 设置环境变量避免交互式安装
ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/*

# 安装MLflow和依赖
RUN pip install --no-cache-dir \
    mlflow==3.1.4

# 创建标准的数据目录结构
RUN mkdir -p /var/lib/mlflow/data && \
    mkdir -p /var/log/mlflow && \
    mkdir -p /etc/mlflow && \
    chmod 755 /var/lib/mlflow /var/log/mlflow /etc/mlflow

# 暴露MLflow端口
EXPOSE 5001

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5001 || exit 1

# 启动MLflow服务器（使用SQLite作为后端存储）
CMD ["mlflow", "server", "--host", "0.0.0.0", "--port", "5001", "--backend-store-uri", "sqlite:////var/lib/mlflow/data/mlflow.db"]