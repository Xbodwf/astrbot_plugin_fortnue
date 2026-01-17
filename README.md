# astrbot_plugin_fortnue

**关于此插件的命名，一开始是fortune打错了，后面干脆就这样了。**

一个使用方法简单的今日运势插件。

# 使用
```plaintext
/今日运势
/运势
/jrys
```
均可。

![今日运势](_README.Assets/p1.png)

进阶使用方式 [点此](#进阶使用)

# 安装

## clone
```bash
cd {Astrbot安装目录}/data/plugins
git clone https://github.com/Xbodwf/astrbot_plugin_fortnue.git
cd astrbot_plugin_fortnue
pip install -r requirements.txt
```
然后重启Astrbot.

## 插件市场

插件市场搜索fortnue即可.

## Source Code

### WebUI安装
从[这里](https://github.com/Xbodwf/astrbot_plugin_fortnue/archive/refs/heads/main.zip)下载插件源代码zip,然后进入Astrbot WebUI安装。

### 终端安装

**需要重启Astrbot**

```bash
cd {Astrbot安装目录}/data/plugins
curl -o astrbot_plugin_fortnue.zip https://github.com/Xbodwf/astrbot_plugin_fortnue/archive/refs/heads/main.zip
unzip astrbot_plugin_fortnue.zip
```

# 进阶使用
| 指令 / 指令组 | 类型 | 插件源 | 功能描述 |
| :--- | :--- | :--- | :--- |
| `jrys` | 指令 | astrbot_plugin_fortnue | 生成今日运势图片 |
| **`jrysl`** | 指令组(2) | astrbot_plugin_fortnue | 今日运势管理指令组 |
| ↳ `jrysl source` | 子指令 | astrbot_plugin_fortnue | 从指定的图源加载图片生成今日运势 |
| ↳ `jrysl last` | 子指令 | astrbot_plugin_fortnue | 获取上一次今日运势的原始背景图片（无运势信息...） |
| **`jrysl none`** | 指令组(1) | astrbot_plugin_fortnue | 单独从图源中刷图（无运势信息） |
| ↳ `jrysl none source` | 子指令 | astrbot_plugin_fortnue | 从指定的图源单独刷图（无运势信息） |