# AI 镜头脚本生成器

> 一个基于 CustomTkinter 的 AI 内容创作工具，支持剧本生成、图片处理、视频生成、配音等功能。

**⚠️ 半成品 | 在校大学生作品 | 欢迎大佬指点**

---

## 功能模块

| 模块 | 功能 | 状态 |
|------|------|------|
| 剧本生成 | 输入故事创意，自动生成分镜脚本 | ✅ 基本完成 |
| 视觉引擎 | 图片批处理、百炼 AI 生图/生视频 | ✅ 基本完成 |
| Vidu 视频 | Vidu API 视频生成 | ⚠️ API 过期，需更新 |
| 智能配音 | 阿里云 TTS、GPT-SoVITS、小米 MiMo | ✅ 基本完成 |
| 全局设置 | API 配置、供应商管理 | ✅ 基本完成 |
| 一键总装 | FFmpeg 音视频合成 | ✅ 基本完成 |

## 技术栈

- Python 3.12
- CustomTkinter (GUI)
- PIL/Pillow (图片处理)
- Requests (API 调用)
- FFmpeg (音视频处理)

## 快速开始

```bash
# 1. 安装依赖
pip install customtkinter pillow requests

# 2. 运行程序
python batch_processor.py

# 或者双击桌面快捷方式（需要先配置 bat 文件路径）
```

## 项目结构

```
├── batch_processor.py      # 入口文件（兼容旧版）
├── studio/                 # 核心代码（模块化）
│   ├── app.py             # 主应用类
│   ├── config.py          # 配置管理
│   ├── constants.py       # 常量定义
│   ├── ui.py              # 公共组件
│   └── pages/             # 各功能页面
│       ├── script.py      # 剧本生成
│       ├── visuals.py     # 视觉引擎
│       ├── vidu.py        # Vidu 视频
│       ├── voice.py       # 智能配音
│       ├── api_page.py    # API 设置
│       └── assembly.py    # 一键总装
├── config.json            # 用户配置（自动生成）
└── crash.log              # 错误日志
```

## 当前问题（求指导）

1. **代码架构**：目前是单文件拆分，不确定这样的模块化方式是否合理
2. **API 调用**：对 Anthropic/OpenAI 兼容 API 的处理不够完善
3. **错误处理**：异常处理比较粗糙，需要优化
4. **UI 设计**：CustomTkinter 的布局和样式还需要改进
5. **功能完善**：部分功能只是基本实现，还有很多细节需要打磨

## 欢迎贡献

这是一个学习项目，代码还有很多不足之处。如果你有更好的建议或想贡献代码，欢迎：

- 提交 Issue
- 提交 Pull Request
- 分享你的想法

## 环境要求

- Windows 10/11
- Python 3.10+
- FFmpeg（一键总装功能需要）

## 许可证

MIT License

---

**最后更新**：2026-06-25
