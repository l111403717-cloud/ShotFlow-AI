# 🌌 AI Content Studio v7.0 - 系统架构与依赖白皮书

> **警告：** 本文档为系统拓扑核心锚点。任何 AI 助手在执行代码修改、模块增删前，**必须优先阅读此白皮书**，以防切断跨模块依赖导致系统瘫痪。

## 1. 【中央骨架与星型 Mixin 映射】
系统采用高内聚的星型多重继承架构（MRO）。`BatchProcessor` 作为 UI 壳子和生命周期总线，挂载 8 个自治的 Mixin 引擎。

* **`BatchProcessor` (母体):** 负责初始化窗口、左侧导航栏、全局路由 (`_show_page`) 以及挂载各 Mixin。
* **`ScriptEngineMixin` (剧本引擎):** 负责连接大模型，生成动态镜头脚本，维护核心文本框 `self.script_output`。
* **`VisualEngineMixin` (视觉引擎):** 负责图片批处理、尺寸调整，以及百炼图像/图生视频的 API 轮询。
* **`NineGridMixin` (九宫格引擎):** 负责处理画布重绘 (`self.ng_canvas`)、相对坐标转换及九宫格图片裁剪切片。
* **`ViduEngineMixin` (Vidu视频引擎):** 负责 Vidu API 鉴权、积分计算、渲染参数配置及视频轮询下载。
* **`VoiceEngineMixin` (配音引擎):** 负责管理 DashScope / GPT-SoVITS / MiMo TTS，处理文本到音频的批量转换。
* **`AssemblyMixin` (总装引擎):** 负责调度本地 FFmpeg，计算音视频 Tpad 差值，并自动生成 SRT 字幕。
* **`AgentMixin` (智能体引擎):** 负责全局悬浮窗 (`self._mimo_fab`) 的唤醒，处理自然语言指令并进行函数路由。

---

## 2. 【数据流转与全局状态总线】

所有跨文件共享的核心状态，必须通过以下方式在 `batch_processor.py` 中初始化并注入：

### A. 全局配置与持久化 (`config.json`)
* **载体：** `self.config` (字典类型)
* **流转：** 所有引擎的 API Key (如 `api_key`, `mimo_api_key`, `vidu_api_key`)、上次选择的模型和分辨率等，均实时绑定于 `tk.StringVar`。
* **落盘：** 当任何模块调用 `save_config(self.config)` 时，数据物理写入硬盘。

### B. 全局主题与 UI 组件 (`C` & `SectionCard`)
* **载体：** 字典 `C` (存储所有 HEX 颜色) 和 `FONT_*` 常量。
* **依赖：** 所有 Mixin 的 `_build_page_*` 方法在绘制界面时，极度依赖这些常量。
* **警告：** 必须确保常量在 `class BatchProcessor` 实例化**之前**完成加载，否则会导致 Mixin 启动白屏或闪退。

### C. 统一日志输出 (`self.global_log`)
* **载体：** 右侧抽屉式的 `LogBox` 实例。
* **流转：** 各引擎通过自身的 `_xxx_log_msg` (如 `_vidu_log_msg`, `_bailian_log_msg`)，最终通过线程安全的 `self.safe_after()` 写入全局终端，并同时抛给 `crash.log`。

---

## 3. 🚨【跨模块通信链路地图（横向依赖暗道）】
**（极度重要：修改以下任何上游变量命名，将导致下游功能直接暴毙！）**

整个系统以 **`ScriptEngineMixin` (剧本引擎)** 为事实上的"数据源泉"，多个模块会跨界读取它的数据。

### 🔗 链路 1：配音提取台词 (Voice -> Script)
* **触发动作：** 配音页面点击"从 Script 提取"按钮 (`_extract_dialogue`)
* **越界读取：** `self.script_output.get("1.0", "end")`
* **逻辑：** 正则表达式匹配"台词/旁白："后的内容，将其写入配音引擎的 `self.tts_text`。

### 🔗 链路 2：Vidu 同步分镜 (Vidu -> Script)
* **触发动作：** Vidu 页面点击"🔄 从 Script 同步分镜" (`_vidu_sync_shots_from_script`)
* **越界读取：** `self.script_output.get("1.0", "end")`
* **逻辑：** 调用底层的 `_parse_script_shots` 提取英文 Prompt 和时长，并渲染到 Vidu 的分镜列表 `self._vidu_shot_rows`。

### 🔗 链路 3：百炼批量提取提示词 (Visual -> Script)
* **触发动作：** 图生视频页面点击"从 Script 提取" (`_i2v_extract_prompts_from_script`)
* **越界读取：** `self.script_output.get("1.0", "end")`
* **逻辑：** 将提取出的英文提示词，精准注入到视觉引擎的 `self._i2v_mapping_rows`（图片-提示词对应表）中。

### 🔗 链路 4：总装获取字幕文本 (Assembly -> Voice)
* **触发动作：** 一键总装页面点击"开始一键高质量合片" (`_start_assembly`)
* **越界读取：** `self.tts_text.get("1.0", "end")`
* **逻辑：** 组装引擎不读剧本，而是直接去读**配音引擎**文本框里的行数，用来映射生成对应的 `shot_X.srt` 字幕。

### 🔗 链路 5：智能体全局监控 (Agent -> 全局)
* **触发动作 1 (提取提示词)：** `_agent_extract_prompts()` 会读取 `self.script_output`，并直接修改视觉引擎的 UI 表格。
* **触发动作 2 (排查错误)：** `_agent_get_logs()` 会跨界读取 `crash.log` 文件和 `self.global_log` 组件内的文本，上报给大模型进行诊断。

---
**架构师签名：** `AI_Director` / `刘晨旭`
**更新日期：** `2026-06-09`
