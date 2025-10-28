# API 路由管理规范

## 1. 设计原则

### 1.1 统一性
- 所有API路由遵循统一的命名和管理规范
- 保持前后端API路径的一致性

### 1.2 层次性
- API路径应该反映资源层次结构
- 使用清晰的路径前缀区分不同功能模块

### 1.3 可扩展性
- 路由设计应该便于未来功能扩展
- 支持版本管理和模块化开发

## 2. 路由管理规范

### 2.1 文件结构
```
app/api/
├── v1/                    # API版本目录
│   ├── endpoints/         # 端点实现文件
│   │   ├── images.py     # 图片管理端点
│   │   ├── image_upload.py # 图片上传端点
│   │   └── image_search.py # 图片搜索端点
│   └── router.py         # 路由聚合配置
└── __init__.py
```

### 2.2 路由定义规范

#### 端点文件内部（如 images.py）
```python
# ✅ 正确：使用相对路径（不以/开头）
router = APIRouter(tags=["Image Management"])

@router.get("", summary="获取图片列表")  # 根路径使用空字符串
@router.get("/{image_id}", summary="获取图片详情")  # 参数路径使用/开头
@router.post("", summary="创建资源")  # POST操作使用空字符串
```

#### 路由聚合文件（router.py）
```python
# ✅ 正确：统一在聚合文件中管理前缀
api_router.include_router(images.router, prefix="/images", tags=["图片管理"])
api_router.include_router(image_upload.router, prefix="/images/upload", tags=["图片上传"])
api_router.include_router(image_search.router, prefix="/images/search", tags=["图片搜索"])
```

### 2.3 禁止的模式

```python
# ❌ 错误：在端点文件中使用绝对前缀
router = APIRouter(prefix="/images", tags=["Image Management"])

# ❌ 错误：混合使用前缀管理
# 文件内设置前缀，聚合文件又设置前缀会导致路径重复
```

## 3. API路径示例

### 3.1 图片管理模块
```
GET    /api/v1/images           # 获取图片列表
GET    /api/v1/images/{id}     # 获取图片详情
DELETE /api/v1/images/{id}     # 删除图片
POST   /api/v1/images/batch/delete # 批量删除
```

### 3.2 图片上传模块
```
POST   /api/v1/images/upload    # 上传图片
POST   /api/v1/images/upload/presigned # 获取预签名URL
POST   /api/v1/images/upload/batch # 批量上传
```

### 3.3 图片搜索模块
```
POST   /api/v1/images/search    # 搜索图片
POST   /api/v1/images/search/tags # 按标签搜索
GET    /api/v1/images/search/tags # 获取标签列表
GET    /api/v1/images/search/statistics # 搜索统计
```

## 4. 最佳实践

### 4.1 路径命名
- 使用复数名词表示资源集合：`/images`而不是`/image`
- 使用连字符分隔单词：`search-statistics`而不是`searchStatistics`
- 保持URL小写

### 4.2 HTTP方法使用
- `GET`：获取资源
- `POST`：创建资源或执行操作
- `PUT`：更新完整资源
- `PATCH`：部分更新资源
- `DELETE`：删除资源

### 4.3 版本管理
- 在URL路径中包含版本号：`/api/v1/`
- 支持向后兼容的版本升级

## 5. 维护指南

1. **新增端点**：在对应的端点文件中添加路由定义
2. **修改路径**：在router.py中调整前缀配置
3. **添加模块**：创建新的端点文件并在router.py中注册
4. **版本升级**：创建v2目录并逐步迁移

## 6. 示例代码

### 端点文件示例（images.py）
```python
router = APIRouter(tags=["Image Management"])

@router.get("", summary="获取图片列表")
async def list_images():
    pass

@router.get("/{image_id}", summary="获取图片详情")
async def get_image(image_id: str):
    pass
```

### 路由聚合示例（router.py）
```python
api_router.include_router(images.router, prefix="/images", tags=["图片管理"])
api_router.include_router(upload.router, prefix="/images/upload", tags=["图片上传"])
api_router.include_router(search.router, prefix="/images/search", tags=["图片搜索"])
```

遵循此规范可以确保API路由的清晰性、一致性和可维护性。