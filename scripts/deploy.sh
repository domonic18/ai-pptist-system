#!/bin/bash

# AI PPTist 部署脚本
# 用于管理生产环境和开发环境的部署

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 配置文件路径
ENV_FILE="$PROJECT_ROOT/config/.env"
ENV_LOCAL_FILE="$PROJECT_ROOT/config/.env.local"
DOCKER_COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"
DOCKER_COMPOSE_DEV_FILE="$PROJECT_ROOT/docker-compose-dev.yml"

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        log_error "命令 $1 未安装，请先安装"
        exit 1
    fi
}

# 检查环境文件是否存在
check_env_files() {
    if [[ "$1" == "prod" ]] && [[ ! -f "$ENV_FILE" ]]; then
        log_error "生产环境配置文件 $ENV_FILE 不存在"
        log_info "请从 config/.env.example 复制并配置"
        exit 1
    fi

    if [[ "$1" == "dev" ]] && [[ ! -f "$ENV_LOCAL_FILE" ]]; then
        log_warning "开发环境配置文件 $ENV_LOCAL_FILE 不存在"
        log_info "将使用默认开发环境配置"
    fi
}

# 显示帮助信息
show_help() {
    echo "使用方法: $0 [环境] [命令]"
    echo ""
    echo "环境:"
    echo "  prod     生产环境"
    echo "  dev      开发环境"
    echo ""
    echo "命令:"
    echo "  up       启动服务"
    echo "  down     停止服务"
    echo "  restart  重启服务"
    echo "  logs     查看日志"
    echo "  status   查看状态"
    echo "  build    构建镜像"
    echo "  ps       查看容器状态"
    echo "  exec     进入容器"
    echo "  clean    清理数据"
    echo "  clean-mlflow 清理MLflow追踪数据"
    echo "  help     显示帮助"
    echo ""
    echo "示例:"
    echo "  $0 dev up     启动开发环境"
    echo "  $0 prod up    启动生产环境"
    echo "  $0 dev logs   查看开发环境日志"
    echo "  $0 dev clean-mlflow 清理开发环境MLflow数据"
}

# 启动服务
start_services() {
    local env=$1
    local compose_file="$(get_compose_file $env)"

    log_info "启动 $env 环境服务..."
    docker-compose -f "$compose_file" up -d
    log_success "$env 环境服务启动完成"
}

# 停止服务
stop_services() {
    local env=$1
    local compose_file="$(get_compose_file $env)"

    log_info "停止 $env 环境服务..."
    docker-compose -f "$compose_file" down
    log_success "$env 环境服务已停止"
}

# 重启服务
restart_services() {
    local env=$1
    local compose_file="$(get_compose_file $env)"

    log_info "重启 $env 环境服务..."
    docker-compose -f "$compose_file" restart
    log_success "$env 环境服务重启完成"
}

# 查看日志
show_logs() {
    local env=$1
    local compose_file="$(get_compose_file $env)"
    local service=${2:-""}

    if [[ -n "$service" ]]; then
        log_info "查看 $env 环境 $service 服务日志..."
        docker-compose -f "$compose_file" logs -f "$service"
    else
        log_info "查看 $env 环境所有服务日志..."
        docker-compose -f "$compose_file" logs -f
    fi
}

# 查看状态
show_status() {
    local env=$1
    local compose_file="$(get_compose_file $env)"

    log_info "$env 环境服务状态:"
    docker-compose -f "$compose_file" ps
}

# 构建镜像
build_images() {
    local env=$1
    local compose_file="$(get_compose_file $env)"

    log_info "构建 $env 环境镜像..."
    docker-compose -f "$compose_file" build --no-cache
    log_success "$env 环境镜像构建完成"
}

# 查看容器状态
show_containers() {
    local env=$1
    local compose_file="$(get_compose_file $env)"

    log_info "$env 环境容器状态:"
    docker-compose -f "$compose_file" ps -a
}

# 进入容器
exec_container() {
    local env=$1
    local service=${2:-"backend"}
    local compose_file="$(get_compose_file $env)"

    log_info "进入 $env 环境 $service 容器..."
    docker-compose -f "$compose_file" exec "$service" sh
}

# 清理数据
clean_data() {
    local env=$1

    read -p "确定要清理 $env 环境数据吗？这将删除所有数据库、缓存数据和MLflow追踪数据 (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "清理 $env 环境数据..."

        if [[ "$env" == "prod" ]]; then
            # 停止并删除生产环境容器
            docker-compose -f "$DOCKER_COMPOSE_FILE" down -v
            rm -rf "$PROJECT_ROOT/workspace/db_data"
            rm -rf "$PROJECT_ROOT/workspace/redis_data"
            rm -rf "$PROJECT_ROOT/workspace/mlflow_data"
        else
            # 停止并删除开发环境容器
            docker-compose -f "$DOCKER_COMPOSE_DEV_FILE" down -v
            rm -rf "$PROJECT_ROOT/workspace/db_data"
            rm -rf "$PROJECT_ROOT/workspace/redis_data"
            rm -rf "$PROJECT_ROOT/workspace/mlflow_data"
        fi

        log_success "$env 环境数据清理完成"
        log_info "下次启动服务时会自动重新初始化数据库和MLflow追踪"
    else
        log_info "取消数据清理"
    fi
}

# 清理MLflow数据
clean_mlflow_data() {
    local env=$1

    read -p "确定要清理 $env 环境的MLflow追踪数据吗？这将删除所有AI模型调用记录和实验数据 (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "清理 $env 环境MLflow数据..."

        # 停止MLflow服务
        if [[ "$env" == "prod" ]]; then
            docker-compose -f "$DOCKER_COMPOSE_FILE" stop mlflow
            rm -rf "$PROJECT_ROOT/workspace/mlflow_data"
            docker-compose -f "$DOCKER_COMPOSE_FILE" start mlflow
        else
            docker-compose -f "$DOCKER_COMPOSE_DEV_FILE" stop mlflow-dev
            rm -rf "$PROJECT_ROOT/workspace/mlflow_data"
            docker-compose -f "$DOCKER_COMPOSE_DEV_FILE" start mlflow-dev
        fi

        log_success "$env 环境MLflow数据清理完成"
        log_info "MLflow追踪数据已重置，新的AI调用将重新开始记录"
    else
        log_info "取消MLflow数据清理"
    fi
}

# 获取对应的docker-compose文件
get_compose_file() {
    local env=$1

    if [[ "$env" == "prod" ]]; then
        echo "$DOCKER_COMPOSE_FILE"
    else
        echo "$DOCKER_COMPOSE_DEV_FILE"
    fi
}

# 主函数
main() {
    # 检查必需命令
    check_command docker
    check_command docker-compose

    local env=${1:-""}
    local command=${2:-"help"}

    case "$env" in
        "prod" | "dev")
            check_env_files "$env"
            ;;
        "help" | "" | "-h" | "--help")
            show_help
            exit 0
            ;;
        *)
            log_error "无效的环境: $env"
            show_help
            exit 1
            ;;
    esac

    case "$command" in
        "up")
            start_services "$env"
            ;;
        "down")
            stop_services "$env"
            ;;
        "restart")
            restart_services "$env"
            ;;
        "logs")
            show_logs "$env" "$3"
            ;;
        "status")
            show_status "$env"
            ;;
        "build")
            build_images "$env"
            ;;
        "ps")
            show_containers "$env"
            ;;
        "exec")
            exec_container "$env" "$3"
            ;;
        "clean")
            clean_data "$env"
            ;;
        "clean-mlflow")
            clean_mlflow_data "$env"
            ;;
        "help")
            show_help
            ;;
        *)
            log_error "无效的命令: $command"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"