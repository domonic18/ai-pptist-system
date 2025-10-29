# HTML生成与DOM解析方案

> **文档版本**: v1.0  
> **创建日期**: 2025-10-29  
> **适用范围**: PPT内容排版优化功能

## 概述

基于专家评审建议，我们采用HTML生成和DOM解析的方式来实现布局优化，而非直接让LLM生成PPTist的JSON数据结构。

### 核心优势

1. **利用LLM擅长HTML的特性**：LLM经过大量HTML训练，对HTML理解和生成质量更高
2. **语义化表达**：HTML的语义化标签和CSS样式能更直观地表达布局意图
3. **降低学习成本**：无需让LLM学习PPTist特定的数据结构
4. **提高输出质量**：HTML格式的约束性更强，LLM更容易生成符合规范的输出

### 数据流转流程

```
PPTist元素 → HTML生成 → LLM优化 → 返回HTML → DOM解析 → PPTist元素
     ↓            ↓          ↓          ↓           ↓            ↓
  JSON格式    HTML标签   AI处理    HTML标签   解析样式      JSON格式
```

---

## 1. PPTist元素 → HTML生成

### 1.1 整体转换逻辑

```python
def _convert_to_html(
    self,
    elements: List[ElementData],
    canvas_size: CanvasSize
) -> str:
    """
    将PPTist元素转换为HTML格式
    利用LLM擅长HTML的特性
    """
    html_parts = [
        f'<div class="ppt-canvas" style="width: {canvas_size.width}px; height: {canvas_size.height}px; position: relative; background: white;">\n'
    ]
    
    for el in elements:
        if el.type == 'text':
            html_parts.append(self._element_to_html_text(el))
        elif el.type == 'shape':
            html_parts.append(self._element_to_html_shape(el))
        elif el.type == 'image':
            html_parts.append(self._element_to_html_image(el))
    
    html_parts.append('</div>')
    return '\n'.join(html_parts)
```

### 1.2 文本元素转换

```python
def _element_to_html_text(self, el: ElementData) -> str:
    """
    文本元素转HTML
    
    PPTist文本元素结构：
    {
      "id": "text_001",
      "type": "text",
      "left": 100,
      "top": 50,
      "width": 600,
      "height": 80,
      "rotate": 0,
      "content": "标题文字",
      "defaultFontName": "Microsoft YaHei",
      "defaultColor": "#333333",
      "lineHeight": 1.5
    }
    """
    styles = [
        'position: absolute',
        f'left: {el.left}px',
        f'top: {el.top}px',
        f'width: {el.width}px',
        f'height: {el.height}px',
        f'transform: rotate({el.rotate}deg)',
    ]
    
    if el.defaultFontName:
        styles.append(f"font-family: '{el.defaultFontName}'")
    if el.defaultColor:
        styles.append(f'color: {el.defaultColor}')
    if el.lineHeight:
        styles.append(f'line-height: {el.lineHeight}')
    # 可选：添加字体大小
    if hasattr(el, 'fontSize') and el.fontSize:
        styles.append(f'font-size: {el.fontSize}px')
    # 可选：添加文本对齐
    if hasattr(el, 'textAlign') and el.textAlign:
        styles.append(f'text-align: {el.textAlign}')
        
    style_str = '; '.join(styles)
    content = el.content or ''
    
    return f'''  <div 
    class="ppt-element ppt-text" 
    data-id="{el.id}" 
    data-type="text"
    style="{style_str}">
    {content}
  </div>\n'''
```

**输出示例**：
```html
<div 
  class="ppt-element ppt-text" 
  data-id="text_001" 
  data-type="text"
  style="position: absolute; left: 100px; top: 50px; width: 600px; height: 80px; transform: rotate(0deg); font-family: 'Microsoft YaHei'; color: #333333; line-height: 1.5">
  标题文字
</div>
```

### 1.3 形状元素转换

```python
def _element_to_html_shape(self, el: ElementData) -> str:
    """
    形状元素转HTML
    
    PPTist形状元素结构：
    {
      "id": "shape_001",
      "type": "shape",
      "left": 100,
      "top": 150,
      "width": 760,
      "height": 300,
      "rotate": 0,
      "fill": "#f5f5f5",
      "outline": {"color": "#ddd", "width": 2},
      "text": "形状内的文字"
    }
    """
    styles = [
        'position: absolute',
        f'left: {el.left}px',
        f'top: {el.top}px',
        f'width: {el.width}px',
        f'height: {el.height}px',
        f'transform: rotate({el.rotate}deg)',
    ]
    
    if el.fill:
        styles.append(f'background-color: {el.fill}')
    
    # 处理outline（可能是字符串或字典）
    if el.outline:
        if isinstance(el.outline, dict):
            color = el.outline.get('color', '#000')
            width = el.outline.get('width', 1)
            styles.append(f'border: {width}px solid {color}')
        else:
            styles.append(f'border: 1px solid {el.outline}')
    
    # 可选：圆角
    if hasattr(el, 'borderRadius') and el.borderRadius:
        styles.append(f'border-radius: {el.borderRadius}px')
            
    style_str = '; '.join(styles)
    text_content = el.text or ''
    
    # 形状内部文字使用单独的div
    return f'''  <div 
    class="ppt-element ppt-shape" 
    data-id="{el.id}" 
    data-type="shape"
    style="{style_str}">
    <div class="shape-text" style="padding: 20px; display: flex; align-items: center; justify-content: center; height: 100%;">
      {text_content}
    </div>
  </div>\n'''
```

**输出示例**：
```html
<div 
  class="ppt-element ppt-shape" 
  data-id="shape_001" 
  data-type="shape"
  style="position: absolute; left: 100px; top: 150px; width: 760px; height: 300px; transform: rotate(0deg); background-color: #f5f5f5; border: 2px solid #ddd">
  <div class="shape-text" style="padding: 20px; display: flex; align-items: center; justify-content: center; height: 100%;">
    形状内的文字
  </div>
</div>
```

### 1.4 图片元素转换

```python
def _element_to_html_image(self, el: ElementData) -> str:
    """
    图片元素转HTML
    
    PPTist图片元素结构：
    {
      "id": "image_001",
      "type": "image",
      "left": 50,
      "top": 200,
      "width": 200,
      "height": 150,
      "rotate": 0,
      "src": "https://example.com/image.jpg",
      "fixedRatio": true
    }
    """
    styles = [
        'position: absolute',
        f'left: {el.left}px',
        f'top: {el.top}px',
        f'width: {el.width}px',
        f'height: {el.height}px',
        'object-fit: cover',  # 保持图片比例
    ]
    
    if el.rotate:
        styles.append(f'transform: rotate({el.rotate}deg)')
    
    # 可选：圆角
    if hasattr(el, 'borderRadius') and el.borderRadius:
        styles.append(f'border-radius: {el.borderRadius}px')
        
    style_str = '; '.join(styles)
    src = el.src or ''
    
    return f'''  <img 
    class="ppt-element ppt-image" 
    data-id="{el.id}" 
    data-type="image"
    src="{src}"
    style="{style_str}"
  />\n'''
```

**输出示例**：
```html
<img 
  class="ppt-element ppt-image" 
  data-id="image_001" 
  data-type="image"
  src="https://example.com/image.jpg"
  style="position: absolute; left: 50px; top: 200px; width: 200px; height: 150px; object-fit: cover"
/>
```

---

## 2. Prompt设计

### 2.1 System Prompt

```python
def _build_system_prompt(self) -> str:
    """
    构建系统提示词
    使用HTML方式，利用LLM擅长HTML的特性
    """
    return """你是一位专业的演示文稿设计专家，擅长优化PowerPoint幻灯片的布局。

# 任务
你将收到一个幻灯片的HTML表示，需要优化其布局，使其更具视觉吸引力和专业性。

# 核心原则
1. **内容绝对不变**：所有文字内容、data-id属性必须完全保持原样
2. **视觉层次**：通过字体大小、位置、颜色建立清晰的视觉层次
3. **对齐原则**：确保元素之间的对齐关系（左对齐、居中、右对齐）
4. **留白空间**：合理利用留白，避免过度拥挤，提升呼吸感
5. **平衡布局**：确保视觉重心平衡，元素分布合理

# 优化方式
- 调整元素的 position (left, top)
- 调整元素的 size (width, height)
- 调整字体样式 (font-size, font-weight, line-height, text-align)
- 调整颜色 (color, background-color)
- 添加视觉增强 (box-shadow, border-radius)

# 严格约束
- ✅ 必须保持所有 data-id 属性不变
- ✅ 必须保持所有文本内容不变
- ✅ 必须保持元素的 data-type 属性不变
- ✅ 返回完整的HTML结构

# 输出格式
直接返回优化后的HTML代码，无需任何解释说明。只返回从 <div class="ppt-canvas"> 开始到 </div> 结束的完整HTML结构。"""
```

### 2.2 User Prompt

```python
def _build_user_prompt(
    self,
    html_content: str,
    canvas_size: CanvasSize,
    options: Optional[OptimizationOptions]
) -> str:
    """
    构建用户提示词
    传入HTML内容和优化选项
    """
    requirements = []
    
    if options:
        if options.keep_colors:
            requirements.append("- 保持原有颜色方案，不得更改元素颜色")
        if options.keep_fonts:
            requirements.append("- 保持原有字体，不得更改font-family")
        
        style_hints = {
            'professional': '专业、商务、简洁',
            'creative': '创意、活泼、大胆',
            'minimal': '极简、留白、克制'
        }
        style = options.style or 'professional'
        requirements.append(f"- 优化风格：{style_hints.get(style, '专业')}")
    else:
        requirements.append("- 全面优化布局、字体大小、颜色、间距")
    
    requirements_str = "\n".join(requirements) if requirements else "全面优化"
    
    return f"""请优化以下幻灯片的布局（画布尺寸: {canvas_size.width}x{canvas_size.height}）：

{html_content}

## 优化要求
{requirements_str}

## 输出要求
请直接返回优化后的HTML代码，从 <div class="ppt-canvas"> 开始。"""
```

---

## 3. HTML响应解析

### 3.1 提取HTML内容

```python
def _extract_html_from_response(self, llm_response: str) -> str:
    """
    从LLM响应中提取纯HTML内容
    LLM可能返回markdown格式或带注释的内容
    """
    # 移除markdown代码块标记
    html = llm_response.strip()
    
    # 如果包含```html，提取其中的内容
    if '```html' in html:
        html = re.search(r'```html\s*(.*?)\s*```', html, re.DOTALL)
        if html:
            html = html.group(1)
    elif '```' in html:
        html = re.search(r'```\s*(.*?)\s*```', html, re.DOTALL)
        if html:
            html = html.group(1)
    
    # 提取<div class="ppt-canvas">...</div>
    match = re.search(
        r'<div\s+class="ppt-canvas".*?</div>\s*$',
        html,
        re.DOTALL | re.MULTILINE
    )
    
    if not match:
        raise ValueError("LLM响应中未找到有效的HTML结构")
    
    return match.group(0)
```

### 3.2 DOM解析核心逻辑

```python
from bs4 import BeautifulSoup
import re

def _parse_html_to_elements(
    self,
    html_content: str,
    original_elements: List[ElementData]
) -> List[ElementData]:
    """
    解析HTML DOM，转换为PPTist元素列表
    
    Args:
        html_content: 优化后的HTML
        original_elements: 原始元素列表（用于保留未优化的字段）
    
    Returns:
        List[ElementData]: 优化后的元素列表
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 构建原始元素ID映射
    original_map = {el.id: el for el in original_elements}
    
    # 查找所有PPT元素
    ppt_elements = soup.find_all(class_='ppt-element')
    
    optimized_elements = []
    
    for elem in ppt_elements:
        # 获取data-id和data-type
        element_id = elem.get('data-id')
        element_type = elem.get('data-type')
        
        if not element_id or not element_type:
            continue
        
        # 获取原始元素
        original = original_map.get(element_id)
        if not original:
            logger.warning(f"未找到原始元素: {element_id}")
            continue
        
        # 解析样式
        style_dict = self._parse_inline_style(elem.get('style', ''))
        
        # 根据类型解析
        if element_type == 'text':
            optimized = self._parse_html_text_element(elem, style_dict, original)
        elif element_type == 'shape':
            optimized = self._parse_html_shape_element(elem, style_dict, original)
        elif element_type == 'image':
            optimized = self._parse_html_image_element(elem, style_dict, original)
        else:
            continue
        
        optimized_elements.append(optimized)
    
    return optimized_elements
```

### 3.3 样式解析工具

```python
def _parse_inline_style(self, style_str: str) -> Dict[str, str]:
    """
    解析内联样式字符串为字典
    
    Input: "position: absolute; left: 100px; top: 50px; color: #333"
    Output: {"position": "absolute", "left": "100px", "top": "50px", "color": "#333"}
    """
    style_dict = {}
    if not style_str:
        return style_dict
    
    for item in style_str.split(';'):
        item = item.strip()
        if ':' in item:
            key, value = item.split(':', 1)
            style_dict[key.strip()] = value.strip()
    
    return style_dict

def _parse_px_value(self, value: str) -> float:
    """
    解析px值
    
    Input: "100px" or "100"
    Output: 100.0
    """
    if not value:
        return 0.0
    
    value = str(value).strip()
    if value.endswith('px'):
        value = value[:-2]
    
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def _parse_rotate_value(self, transform: str) -> float:
    """
    从transform中解析旋转角度
    
    Input: "rotate(15deg)"
    Output: 15.0
    """
    if not transform:
        return 0.0
    
    match = re.search(r'rotate\s*\(\s*([-\d.]+)deg\s*\)', transform)
    if match:
        try:
            return float(match.group(1))
        except (ValueError, TypeError):
            pass
    
    return 0.0
```

### 3.4 文本元素解析

```python
def _parse_html_text_element(
    self,
    elem: BeautifulSoup,
    style_dict: Dict[str, str],
    original: ElementData
) -> ElementData:
    """
    解析HTML文本元素为PPTist文本元素
    """
    # 提取文本内容
    text_content = elem.get_text(strip=True)
    
    # 构建优化后的元素
    optimized = ElementData(
        id=elem.get('data-id'),
        type='text',
        # 位置和尺寸
        left=self._parse_px_value(style_dict.get('left', 0)),
        top=self._parse_px_value(style_dict.get('top', 0)),
        width=self._parse_px_value(style_dict.get('width', original.width)),
        height=self._parse_px_value(style_dict.get('height', original.height)),
        rotate=self._parse_rotate_value(style_dict.get('transform', '')),
        # 文本内容（必须与原始一致）
        content=text_content,
        # 字体样式
        defaultFontName=style_dict.get('font-family', original.defaultFontName).strip("'\""),
        defaultColor=style_dict.get('color', original.defaultColor),
        lineHeight=float(style_dict.get('line-height', original.lineHeight or 1.5)),
    )
    
    # 可选字段
    if 'font-size' in style_dict:
        optimized.fontSize = self._parse_px_value(style_dict['font-size'])
    if 'font-weight' in style_dict:
        optimized.fontWeight = style_dict['font-weight']
    if 'text-align' in style_dict:
        optimized.textAlign = style_dict['text-align']
    
    return optimized
```

### 3.5 形状元素解析

```python
def _parse_html_shape_element(
    self,
    elem: BeautifulSoup,
    style_dict: Dict[str, str],
    original: ElementData
) -> ElementData:
    """
    解析HTML形状元素为PPTist形状元素
    """
    # 提取形状内部文字
    shape_text_elem = elem.find(class_='shape-text')
    text_content = shape_text_elem.get_text(strip=True) if shape_text_elem else ''
    
    # 解析border
    outline = None
    if 'border' in style_dict:
        border_match = re.match(r'(\d+)px\s+solid\s+(#[0-9a-fA-F]{3,6})', style_dict['border'])
        if border_match:
            outline = {
                'width': int(border_match.group(1)),
                'color': border_match.group(2)
            }
    
    optimized = ElementData(
        id=elem.get('data-id'),
        type='shape',
        # 位置和尺寸
        left=self._parse_px_value(style_dict.get('left', 0)),
        top=self._parse_px_value(style_dict.get('top', 0)),
        width=self._parse_px_value(style_dict.get('width', original.width)),
        height=self._parse_px_value(style_dict.get('height', original.height)),
        rotate=self._parse_rotate_value(style_dict.get('transform', '')),
        # 形状样式
        fill=style_dict.get('background-color', original.fill),
        outline=outline or original.outline,
        text=text_content,
    )
    
    # 可选：圆角
    if 'border-radius' in style_dict:
        optimized.borderRadius = self._parse_px_value(style_dict['border-radius'])
    
    return optimized
```

### 3.6 图片元素解析

```python
def _parse_html_image_element(
    self,
    elem: BeautifulSoup,
    style_dict: Dict[str, str],
    original: ElementData
) -> ElementData:
    """
    解析HTML图片元素为PPTist图片元素
    """
    optimized = ElementData(
        id=elem.get('data-id'),
        type='image',
        # 位置和尺寸
        left=self._parse_px_value(style_dict.get('left', 0)),
        top=self._parse_px_value(style_dict.get('top', 0)),
        width=self._parse_px_value(style_dict.get('width', original.width)),
        height=self._parse_px_value(style_dict.get('height', original.height)),
        rotate=self._parse_rotate_value(style_dict.get('transform', '')),
        # 图片源
        src=elem.get('src', original.src),
        fixedRatio=original.fixedRatio,
    )
    
    # 可选：圆角
    if 'border-radius' in style_dict:
        optimized.borderRadius = self._parse_px_value(style_dict['border-radius'])
    
    return optimized
```

---

## 4. 完整流程示例

### 4.1 输入：PPTist元素

```json
{
  "elements": [
    {
      "id": "text_001",
      "type": "text",
      "left": 100,
      "top": 50,
      "width": 600,
      "height": 80,
      "rotate": 0,
      "content": "产品介绍",
      "defaultFontName": "Microsoft YaHei",
      "defaultColor": "#333333"
    }
  ],
  "canvas_size": {"width": 1000, "height": 562.5}
}
```

### 4.2 步骤1：转换为HTML

```html
<div class="ppt-canvas" style="width: 1000px; height: 562.5px; position: relative; background: white;">
  <div 
    class="ppt-element ppt-text" 
    data-id="text_001" 
    data-type="text"
    style="position: absolute; left: 100px; top: 50px; width: 600px; height: 80px; transform: rotate(0deg); font-family: 'Microsoft YaHei'; color: #333333">
    产品介绍
  </div>
</div>
```

### 4.3 步骤2：LLM优化

LLM接收上述HTML + Prompt，返回优化后的HTML：

```html
<div class="ppt-canvas" style="width: 1000px; height: 562.5px; position: relative; background: white;">
  <div 
    class="ppt-element ppt-text" 
    data-id="text_001" 
    data-type="text"
    style="position: absolute; left: 200px; top: 100px; width: 600px; height: 120px; transform: rotate(0deg); font-family: 'Microsoft YaHei'; font-size: 48px; font-weight: bold; color: #1a1a1a; text-align: center">
    产品介绍
  </div>
</div>
```

### 4.4 步骤3：DOM解析

解析优化后的HTML，转换回PPTist元素：

```json
{
  "id": "text_001",
  "type": "text",
  "left": 200,
  "top": 100,
  "width": 600,
  "height": 120,
  "rotate": 0,
  "content": "产品介绍",
  "defaultFontName": "Microsoft YaHei",
  "defaultColor": "#1a1a1a",
  "fontSize": 48,
  "fontWeight": "bold",
  "textAlign": "center"
}
```

---

## 5. 依赖库

### 5.1 Python依赖

```python
# HTML解析
from bs4 import BeautifulSoup  # pip install beautifulsoup4
import re
```

在 `backend/pyproject.toml` 中添加：

```toml
[tool.poetry.dependencies]
beautifulsoup4 = "^4.12.0"
```

### 5.2 安装命令

```bash
cd backend
poetry add beautifulsoup4
```

---

## 6. 错误处理

### 6.1 HTML提取失败

```python
def _extract_html_from_response(self, llm_response: str) -> str:
    try:
        # 提取逻辑
        ...
    except Exception as e:
        logger.error(
            "HTML提取失败",
            operation="extract_html",
            error=str(e)
        )
        raise ValueError(f"无法从LLM响应中提取有效HTML: {str(e)}")
```

### 6.2 DOM解析失败

```python
def _parse_html_to_elements(self, html_content: str, original_elements: List[ElementData]) -> List[ElementData]:
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        ...
    except Exception as e:
        logger.error(
            "DOM解析失败",
            operation="parse_html_dom",
            error=str(e),
            html_length=len(html_content)
        )
        raise ValueError(f"HTML DOM解析失败: {str(e)}")
```

### 6.3 元素ID不一致

```python
# 在验证阶段检查
def _validate_optimized_elements(self, optimized: List[ElementData], original: List[ElementData]):
    original_ids = {el.id for el in original}
    optimized_ids = {el.id for el in optimized}
    
    if original_ids != optimized_ids:
        missing = original_ids - optimized_ids
        extra = optimized_ids - original_ids
        raise ValueError(
            f"元素ID不一致。缺失: {missing}, 多余: {extra}"
        )
```

---

## 7. 最佳实践

### 7.1 HTML生成

1. ✅ 使用语义化的class名称（`ppt-element`, `ppt-text`, `ppt-shape`）
2. ✅ 使用data-*属性保存元数据（`data-id`, `data-type`）
3. ✅ 使用内联样式（便于LLM理解和修改）
4. ✅ 保持HTML结构简洁（避免过度嵌套）

### 7.2 Prompt设计

1. ✅ 明确告知LLM约束条件（ID不变、内容不变）
2. ✅ 提供具体的优化方向（视觉层次、对齐、留白）
3. ✅ 要求返回纯HTML（无markdown标记）
4. ✅ 提供示例输出格式

### 7.3 DOM解析

1. ✅ 使用专业HTML解析库（BeautifulSoup）
2. ✅ 容错处理（缺失字段使用默认值）
3. ✅ 严格验证（ID一致性、内容不变性）
4. ✅ 详细日志记录（便于调试）

---

## 8. 与原方案对比

| 维度 | 原方案（JSON） | 新方案（HTML） |
|------|---------------|---------------|
| **LLM理解难度** | ⚠️ 需要学习PPTist特定结构 | ✅ HTML是标准格式 |
| **输出质量** | ⚠️ 可能不稳定 | ✅ HTML约束性强 |
| **语义表达** | ⚠️ JSON抽象度高 | ✅ HTML语义化清晰 |
| **实现复杂度** | ✅ 简单（直接映射） | ⚠️ 需要HTML↔PPTist转换 |
| **可维护性** | ⚠️ 需要维护JSON Schema | ✅ HTML标准稳定 |
| **调试便利性** | ⚠️ JSON不直观 | ✅ HTML可视化 |

---

## 9. 参考资料

- [BeautifulSoup文档](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [CSS内联样式规范](https://developer.mozilla.org/en-US/docs/Web/HTML/Global_attributes/style)
- [HTML data-*属性](https://developer.mozilla.org/en-US/docs/Learn/HTML/Howto/Use_data_attributes)

---

**文档维护者**: AI开发团队  
**最后更新**: 2025-10-29  
**版本**: v1.0

