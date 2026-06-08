# AI Content Studio — 开发笔记

## 项目位置
`D:\AI Tools\cua-repo\batch_processor.py`

## 最近改动 (2026-06-08)

### MiMo 长消息修复
- 第 3068 行附近：`max_tokens: 500 → 2000`，`timeout: 60 → 120`
- 加了空回复和超时的错误提示
- 原因：长消息输入时，500 token 不够模型输出完整 JSON，导致静默吞掉

### 百炼模型下拉框优化
- 模型分类从 4 个合并为 2 个：`图像生成 (Image)` 和 `视频生成 (Video)`
- 下拉框显示 `模型名  (✅ 无需参考图)` 或 `模型名  (📎 需要参考图)`
- 新增 `_model_hint()` 和 `_extract_model_id()` 函数
- `_update_model_combo()` 改为显示带提示的名称
- `_on_model_changed()` 改为从显示名还原模型 ID

### 管线类型提示
- `_toggle_video_settings()` 里的管线类型从小字改为彩色横幅
- 绿色 = Text-to-Video（无需参考图）
- 橙色 = Image-to-Video（需要参考图）
- 红色 = Video Edit（需要素材）

## 待解决
- [ ] Vidu 页面的模型选择也加类似提示？
- [ ] 排版细节问题（用户说"有点小问题"，具体待确认）
