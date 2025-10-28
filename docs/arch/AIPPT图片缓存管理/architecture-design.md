# 图片URL管理系统架构设计

## 1. 系统架构图

### 1.1 整体架构

```mermaid
graph TB
    subgraph "前端层"
        A[Vue.js 应用]
        B[SmartImage 组件]
        C[图片缓存管理]
        D[错误重试机制]
    end
    
    subgraph "API网关层"
        E[FastAPI 路由]
        F[图片代理端点]
        G[URL管理端点]
        H[监控端点]
    end
    
    subgraph "服务层"
        I[URL管理服务]
        J[代理服务]
        K[缓存服务]
        L[刷新服务]
    end
    
    subgraph "数据层"
        M[Redis 缓存]
        N[PostgreSQL]
        O[腾讯云 COS]
    end
    
    subgraph "任务层"
        P[定时刷新任务]
        Q[监控任务]
        R[清理任务]
    end
    
    A --> B
    B --> C
    B --> D
    A --> E
    E --> F
    E --> G
    E --> H
    F --> J
    G --> I
    H --> Q
    I --> K
    I --> L
    J --> K
    K --> M
    I --> N
    J --> O
    P --> I
    P --> M
    Q --> M
    R --> M
```

### 1.2 数据流架构

```mermaid
graph LR
    subgraph "数据流向"
        A[用户请求] --> B[前端组件]
        B --> C[API 代理]
        C --> D[URL 管理器]
        D --> E[Redis 缓存]
        D --> F[COS 存储]
        D --> G[数据库]
        
        H[定时任务] --> I[批量刷新]
        I --> E
        I --> F
        
        J[监控系统] --> K[统计数据]
        K --> E
    end
```

## 2. 组件设计图

### 2.1 URL管理服务架构

```mermaid
classDiagram
    class ImageURLManager {
        -db: AsyncSession
        -image_repo: ImageRepository
        -storage: COSStorage
        +get_image_url(image_id, user_id, force_refresh)
        +refresh_url(image_id)
        +batch_refresh_urls(image_ids)
    }
    
    class ImageURLCache {
        -url_key_prefix: str
        -stats_key_prefix: str
        -queue_key: str
        +get_url(image_id)
        +set_url(image_id, url, expires_at)
        +add_to_refresh_queue(image_id)
        +get_refresh_queue(limit)
        +acquire_refresh_lock(image_id)
        +release_refresh_lock(image_id)
    }
    
    class RedisClient {
        -_instance: RedisClient
        -_client: Redis
        -_pool: ConnectionPool
        +connect()
        +disconnect()
        +get_client()
        +health_check()
    }
    
    class URLRefreshTask {
        -running: bool
        -stats: dict
        +start()
        +stop()
        -_run_refresh_cycle()
        +get_stats()
    }
    
    ImageURLManager --> ImageURLCache
    ImageURLCache --> RedisClient
    URLRefreshTask --> ImageURLManager
```

### 2.2 前端组件架构

```mermaid
classDiagram
    class SmartImage {
        -imageRef: HTMLImageElement
        -currentSrc: string
        -loading: boolean
        -error: boolean
        -retryCount: number
        +loadImage()
        +handleLoad()
        +handleError()
        +handleRetry()
    }
    
    class useImageRetry {
        +retryWithBackoff(fn, attempt, delay)
        +exponentialBackoff(attempt, baseDelay)
    }
    
    class useImageCache {
        -cache: Map
        +getCachedUrl(imageId)
        +setCachedUrl(imageId, urlInfo)
        +clearExpiredUrls()
        +getCacheStats()
    }
    
    class ImageService {
        +getImageAccessUrl(imageId)
        +uploadImage(file)
        +proxyImageUrl(imageId)
    }
    
    SmartImage --> useImageRetry
    SmartImage --> useImageCache
    SmartImage --> ImageService
```

## 3. 数据模型设计

### 3.1 Redis数据结构

```mermaid
erDiagram
    URL_CACHE {
        string key "image:url:${image_id}"
        json value "url信息对象"
        int ttl "过期时间"
    }
    
    REFRESH_QUEUE {
        string key "image:refresh:queue"
        set value "待刷新的image_id集合"
    }
    
    REFRESH_LOCK {
        string key "image:refresh:lock:${image_id}"
        string value "锁定时间戳"
        int ttl "锁定超时时间"
    }
    
    STATS_CACHE {
        string key "image:stats:daily:${date}"
        json value "统计信息对象"
        int ttl "数据保留时间"
    }
```

### 3.2 URL信息数据结构

```json
{
  "url": "https://bucket.cos.region.myqcloud.com/path/image.jpg?sign=...",
  "expires_at": 1699999999,
  "created_at": 1699996399,
  "access_count": 156,
  "cos_key": "images/user_001/2024/01/image.jpg",
  "last_access": 1699998888,
  "refresh_count": 3
}
```

### 3.3 统计数据结构

```json
{
  "date": "2024-01-15",
  "total_requests": 10000,
  "cache_hits": 8500,
  "cache_misses": 1500,
  "refresh_count": 150,
  "error_count": 25,
  "avg_response_time": 45.2,
  "unique_images": 2500
}
```

## 4. 流程设计图

### 4.1 图片访问完整流程

```mermaid
sequenceDiagram
    participant U as 用户
    participant F as 前端组件
    participant A as API网关
    participant M as URL管理器
    participant C as Redis缓存
    participant D as 数据库
    participant S as COS存储
    participant T as 定时任务

    Note over U,T: 正常访问流程
    U->>F: 请求显示图片
    F->>A: GET /api/v1/images/{id}/url
    A->>M: 获取图片URL
    M->>C: 检查缓存
    
    alt 缓存命中且未过期
        C-->>M: 返回缓存URL
        M-->>A: 返回URL信息
        A-->>F: 返回URL
        F->>F: 显示图片
    else 缓存未命中或已过期
        M->>D: 查询图片元数据
        D-->>M: 返回cos_key等信息
        M->>S: 生成预签名URL
        S-->>M: 返回预签名URL
        M->>C: 缓存URL信息
        M-->>A: 返回URL信息
        A-->>F: 返回URL
        F->>F: 显示图片
    end
    
    Note over U,T: 后台刷新流程
    T->>C: 扫描即将过期的URL
    C-->>T: 返回待刷新列表
    T->>M: 批量刷新URL
    M->>S: 批量生成新URL
    S-->>M: 返回新URL列表
    M->>C: 更新缓存
```

### 4.2 错误处理流程

```mermaid
sequenceDiagram
    participant F as 前端组件
    participant A as API网关
    participant M as URL管理器
    participant C as Redis缓存
    participant S as COS存储

    Note over F,S: 图片加载失败处理
    F->>F: 图片加载失败
    F->>F: 检查重试次数
    
    alt 未达到最大重试次数
        F->>F: 等待指数退避时间
        F->>A: 重新请求URL
        A->>M: 强制刷新URL
        M->>C: 清除旧缓存
        M->>S: 生成新URL
        S-->>M: 返回新URL
        M->>C: 缓存新URL
        M-->>A: 返回新URL
        A-->>F: 返回新URL
        F->>F: 重新加载图片
    else 达到最大重试次数
        F->>F: 显示错误状态
        F->>F: 提供手动重试按钮
    end
```

### 4.3 代理服务流程

```mermaid
sequenceDiagram
    participant U as 用户浏览器
    participant P as 代理服务
    participant M as URL管理器
    participant S as COS存储

    Note over U,S: 代理模式访问
    U->>P: GET /api/v1/images/{id}/proxy
    P->>M: 获取有效URL
    M-->>P: 返回预签名URL
    P->>S: 代理请求图片
    S-->>P: 返回图片流
    P-->>U: 流式返回图片

    Note over U,S: 重定向模式访问
    U->>P: GET /api/v1/images/{id}/proxy?redirect=true
    P->>M: 获取有效URL
    M-->>P: 返回预签名URL
    P-->>U: 302重定向到预签名URL
    U->>S: 直接请求图片
    S-->>U: 返回图片
```

## 5. 性能优化设计

### 5.1 缓存策略

```mermaid
graph TD
    A[图片请求] --> B{检查L1缓存}
    B -->|命中| C[返回缓存URL]
    B -->|未命中| D{检查Redis缓存}
    D -->|命中且未过期| E[返回Redis URL]
    D -->|未命中或过期| F[从COS生成新URL]
    
    E --> G[更新L1缓存]
    F --> H[缓存到Redis]
    H --> I[更新L1缓存]
    
    subgraph "缓存层级"
        J[L1: 前端内存缓存<br/>容量: 100个URL<br/>TTL: 10分钟]
        K[L2: Redis分布式缓存<br/>容量: 10000个URL<br/>TTL: 动态过期]
        L[L3: COS预签名URL<br/>TTL: 1小时]
    end
```

### 5.2 预刷新策略

```mermaid
graph TD
    A[定时扫描任务] --> B[获取即将过期URL列表]
    B --> C{按优先级排序}
    C --> D[高频访问图片]
    C --> E[最近上传图片]
    C --> F[其他图片]
    
    D --> G[优先刷新队列]
    E --> G
    F --> H[普通刷新队列]
    
    G --> I[批量并发刷新]
    H --> I
    I --> J[更新缓存]
    
    subgraph "刷新策略"
        K[阈值触发: 15分钟内过期]
        L[批量大小: 100个/批次]
        M[并发限制: 10个并发]
        N[重试机制: 指数退避]
    end
```

## 6. 监控与告警设计

### 6.1 监控指标体系

```mermaid
graph TD
    A[监控指标] --> B[性能指标]
    A --> C[业务指标]
    A --> D[系统指标]
    
    B --> B1[响应时间]
    B --> B2[吞吐量]
    B --> B3[缓存命中率]
    
    C --> C1[图片访问成功率]
    C --> C2[URL刷新成功率]
    C --> C3[用户体验指标]
    
    D --> D1[Redis连接状态]
    D --> D2[内存使用率]
    D --> D3[CPU使用率]
    
    subgraph "告警阈值"
        E[响应时间 > 200ms]
        F[缓存命中率 < 70%]
        G[访问失败率 > 1%]
        H[Redis连接异常]
    end
```

### 6.2 告警处理流程

```mermaid
sequenceDiagram
    participant M as 监控系统
    participant A as 告警中心
    participant O as 运维人员
    participant S as 自愈系统

    M->>M: 定期检查指标
    M->>A: 触发告警
    A->>O: 发送告警通知
    A->>S: 触发自动处理
    
    par 人工处理
        O->>O: 分析问题
        O->>O: 执行修复措施
    and 自动处理
        S->>S: 重启服务
        S->>S: 清理缓存
        S->>S: 切换备用方案
    end
    
    O->>A: 确认处理完成
    S->>A: 返回处理结果
    A->>M: 更新告警状态
```

## 7. 扩展性设计

### 7.1 水平扩展

```mermaid
graph TB
    subgraph "负载均衡层"
        A[负载均衡器]
    end
    
    subgraph "应用服务层"
        B[API服务1]
        C[API服务2]
        D[API服务N]
    end
    
    subgraph "缓存层"
        E[Redis主节点]
        F[Redis从节点1]
        G[Redis从节点2]
    end
    
    subgraph "存储层"
        H[PostgreSQL主库]
        I[PostgreSQL从库]
        J[COS存储]
    end
    
    A --> B
    A --> C
    A --> D
    
    B --> E
    C --> F
    D --> G
    
    E --> F
    E --> G
    
    B --> H
    C --> I
    D --> J
```

### 7.2 多地域部署

```mermaid
graph TB
    subgraph "北京地域"
        A1[API服务]
        B1[Redis缓存]
        C1[COS-北京]
    end
    
    subgraph "上海地域"
        A2[API服务]
        B2[Redis缓存]
        C2[COS-上海]
    end
    
    subgraph "广州地域"
        A3[API服务]
        B3[Redis缓存]
        C3[COS-广州]
    end
    
    D[全局负载均衡] --> A1
    D --> A2
    D --> A3
    
    E[中心数据库] --> A1
    E --> A2
    E --> A3
    
    F[缓存同步] --> B1
    F --> B2
    F --> B3
```

---

**文档版本**：v1.0  
**创建时间**：2024年12月  
**维护者**：AI开发团队  
