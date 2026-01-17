# 变更日志

## 1.28.1
- 在下载图片时增加 URL 日志输出，方便调试和追踪图源。

## 1.28.0
- 新增 `object` 类型图源支持，允许从静态列表 `sources` 中随机选取图片。
- `object` 类型支持 `img_headers` 和基于 `sources` 对象的 `addition` 模板变量。
- 重构了背景图获取逻辑，统一了 `api`、`object` 和静态图源的处理流程。

## 1.27.0
- 支持在 `backgrounds.json` 中为 API 类型背景源设置独立的 `img_headers`，用于下载图片时的请求头。
- 优化了图片下载逻辑，支持自定义请求头合并。

## 1.18.0~1.26.0更新日志
1.18.0以后，插件本身可以更自由地添加图源。如何添加图源，修改插件目录的`backgrounds.json`即可。
并且我们提供了代理 Token等方便的功能。

示例图源: 鸭子API (大多来自于Pixiv,以下称作Pixiv)(公益API 请勿滥用)
若为Pixiv图源的图片,今日运势下方会显示图片的pid.
```jsonc
"pixiv": {
        "type": "api",
        "url": "https://api.mossia.top/duckMo",
        "method": "get",
        "expected": "url",
        "token": "data.urlsList.0.url",
        "replacement": {
            "pattern": "i\\.pixiv\\.re",
            "replace": "i.yuki.sh"
        },
        "headers": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0",
            "referer": "https://www.pixiv.net/"
        },
        "addition": "pid {data.pid}" /*可选添加字符串*/
    }
```

## 1.26.0

### 新增
- URL 替换规则（Replacement）：
  - 支持在 `api` 类型图源中配置 `replacement` 正则替换规则。
  - 允许将 API 返回的图片 URL 进行正则处理，以便适配镜像站或其他 CDN。
  - 已为 `pixiv` 图源添加替换规则：将 `i.pixiv.re` 替换为 `i.yuki.sh`。

## 1.25.0

### 优化
- 详细错误报告：
  - 重构了图片下载和 API 解析逻辑，现在在失败时会提供具体的错误信息（如 HTTP 状态码、超时、JSON 解析失败、Token 无效等）。
  - 头像下载失败时改为警告记录并使用默认头像，不再中断运势生成。

## 1.24.0

### 新增
- 增强 Token 解析能力：
  - 支持在 `token` 中使用数字索引（如 `data.0.url`），方便解析数组类型的 API 响应。
  - 保持对原有“数组自动随机选择”逻辑的兼容。

## 1.23.0

### 新增
- 代理支持：
  - 在 `_conf_schema.json` 中新增 `proxy` 配置项。
  - 图片下载及 API 请求支持通过配置的代理进行访问。

## 1.22.0

### 变更
- 指令结构调整：
  - `jrys` 回归为独立指令（带别名：今日运势、运势）。
  - 管理类及扩展子指令迁移至新指令组 `jrysl`。
  - 迁移后的指令包括：`jrysl source`, `jrysl last`, `jrysl none`, `jrysl none source`。

## 1.21.0

### 新增
- 嵌套指令组支持：
  - `jrys none`：单独从图源中随机刷图（不带运势信息）。
  - `jrys none source {name}`：从指定图源刷图（不带运势信息）。
- 指令迁移：
  - `jrys_last` 迁移为 `jrys last` 子指令。

## 1.20.0

### 新增
- 指令组支持：将 `jrys` 重构为指令组。
- 指定图源生成：支持使用 `/jrys source {source_name}` 从指定的图源（`backgrounds.json` 中的键名）加载背景图并生成运势图片。
- 直接触发：保留了直接使用 `/jrys` 生成随机图源运势图片的功能。

## 1.19.0

### 新增
- API 图源支持可选属性 `addition`：支持模板字符串（如 `pixiv {data.pid}`），解析后的内容将展示在图片底部页脚的头部。
- 模板字符串解析：支持通过 `{path.to.key}` 语法从 API 返回的 JSON 中提取数据并填充。

## 1.18.0

### 变更
- 节日判断逻辑优化：移除硬编码的节日日期，改用 `zhdate` 库动态计算公历元旦及农历春节、元宵、端午、中秋等重大节日。
- 依赖更新：新增 `zhdate` 库。

## 1.17.0

### 新增
- 背景图源类型化与等概率选择：支持按“图源”为单位进行等概率选择，图源内部再随机一张图片，避免大数组图源被偏向。
- 支持两类图源类型：
  - `array`：图源自身为图片 URL 数组。
  - `api`：图源为 HTTP 接口，可返回图片数据或图片地址。
- API 图源解析能力：
  - `expected`：支持 `url`（接口返回 JSON，通过路径提取图片地址）或 `image`（接口直接返回图片字节流）。
  - `token`：在 `expected=url` 模式下使用点号分隔路径（例如 `data.url`）提取图片地址，遇到列表会随机选取元素继续解析。
  - `headers`：可在图源中配置请求头（可选），与 `method` 一同用于请求接口。
- 新增示例图源：
  - `alcy_mp`（`api`，`expected=image`）：`https://t.alcy.cc/mp`。
  - `sexphoto`（`api`，`expected=url`，`token=data.url`）：`https://sex.nyan.run/api/v2/`。

### 变更
- 节日好运保底：在元旦及春节日期，幸运指数不低于 70；若同日缓存的幸运指数低于保底值，会自动重新生成并覆盖。
- 背景选择算法重构：由“直接合并全部 URL 后随机”改为“先等概率选择图源，再在图源内随机”，提升选择的公平性与可控性。
