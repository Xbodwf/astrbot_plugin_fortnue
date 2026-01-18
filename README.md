# astrbot_plugin_fortnue

**关于此插件的命名，一开始是 fortune 打错了，后面干脆就这样了。**

一个使用方法简单但是可调内容丰富的今日运势插件，旨在为用户提供精美的二次元风格运势图片。

# 使用
```plaintext
/今日运势
/运势
/jrys
```
均可触发。

![今日运势](_README.Assets/p1.png)

# 安装

## 插件市场 (推荐)
在 AstrBot 插件市场搜索 `fortnue` 即可一键安装。

## 源码安装
1. 进入 AstrBot 的插件目录：
   ```bash
   cd {AstrBot安装目录}/data/plugins
   ```
2. 克隆仓库：
   ```bash
   git clone https://github.com/Xbodwf/astrbot_plugin_fortnue.git
   ```
3. 安装依赖：
   ```bash
   cd astrbot_plugin_fortnue
   pip install -r requirements.txt
   ```
4. 重启 AstrBot。

# 指令说明

| 指令 | 说明 | 示例 |
| :--- | :--- | :--- |
| `/jrys` | 生成今日运势图片 | `/jrys` |
| `/jrysl source <图源名称>` | 指定图源生成运势 | `/jrysl source pixiv` |
| `/jrysl last` | 获取上一张生成的运势背景图 (原图) | `/jrysl last` |
| `/jrysn` | 随机从图源中获取一张背景图 (无运势信息) | `/jrysn` |
| `/jrysl none source <图源名称>` | 从指定图源获取背景图 | `/jrysl none source pixiv` |

# 图源配置指南

插件支持高度自定义的图源配置，所有配置均在插件目录下的 `backgrounds.json` 中完成。

### 1. 静态图源 (数组类型)
最简单的配置方式，直接提供图片 URL 或本地路径的列表。
```json
"my_static_source": [
    "https://example.com/1.jpg",
    "https://example.com/2.png",
    "./data/plugins/astrbot_plugin_fortnue/local_img.jpg"
]
```

### 2. API 图源 (api 类型)
通过请求外部 API 动态获取图片 URL。
```json
"pixiv_api": {
    "type": "api",
    "url": "https://api.example.com/get_image",
    "method": "get",
    "expected": "url",
    "token": "data.image_url", // JSON 解析路径
    "headers": {
        "User-Agent": "..."
    },
    "img_headers": {
        "referer": "https://pixiv.net/" // 专门用于下载图片的请求头
    },
    "replacement": {
        "pattern": "i\\.pixiv\\.re",
        "replace": "i.pixiv.net"
    },
    "addition": "PID: {data.pid}" // 附加信息模板
}
```

### 3. 对象列表图源 (object 类型)
适用于已经拥有图片列表及其相关元数据（如 PID、作者等）的情况。
```json
"pixiv_links": {
    "type": "object",
    "sources": [
        {
            "url": "https://example.com/img1.jpg",
            "pid": "10001",
            "author": "User1"
        },
        {
            "url": "https://example.com/img2.jpg",
            "pid": "10002"
        }
    ],
    "img_headers": {
        "referer": "https://pixiv.net/"
    },
    "addition": "PID: {pid} | Author: {author}" // 变量从选中的对象中提取
}
```

> [NOTE]
> - `addition` 字段支持模板字符串，变量名需与 `object` 中的键或 API 返回的 JSON 结构对应。
> - `img_headers` 非常重要，尤其是对于 Pixiv 等有防盗链限制的图源，通常需要配置 `referer`。
> - 修改 `backgrounds.json` 后无需重启插件，下次请求会自动加载新配置。

# 配置项说明 (config.json)

在 AstrBot 管理面板或 `config.json` 中可以配置以下项：
- `proxy`: 网络代理地址 (如 `http://127.0.0.1:7890`)。
- `image_quality`: 输出图片的 JPEG 质量 (1-100)。

# 变更日志
请参阅 [CHANGELOG.md](CHANGELOG.md) 获取详细的更新历史。
