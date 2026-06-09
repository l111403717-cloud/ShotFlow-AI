"""AI Content Studio v7.0 — 赛博极客风重构版
CustomTkinter 深色主题 | 三栏响应式布局 | 卡片化模块
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import sys
import time
import json
import logging
import traceback
import requests
from PIL import Image, ImageTk
import threading
import base64
import mimetypes
import time as _time

# ============ 日志系统 ============
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash.log")
logging.basicConfig(
    filename=LOG_PATH, level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)

# ============ CustomTkinter 全局主题 ============
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ============ 设计系统 v7.0 — 赛博极客美学 ============
C = {
    # 主背景层级
    "bg":           "#080808",      # 最深背景
    "surface":      "#0F0F0F",      # 卡片底色
    "surface2":     "#161616",      # 输入框/次级容器
    "surface3":     "#1A1A1A",      # 悬停态
    "border":       "#252525",      # 微弱边框
    "border_focus": "#3A3A3A",      # 聚焦边框

    # 强调色 — 低饱和高质感
    "accent":       "#00FF9D",      # 赛博绿（主按钮/激活态）
    "accent_dim":   "#00CC7D",      # 赛博绿暗调
    "accent2":      "#00D4FF",      # 赛博蓝（辅助强调）
    "accent3":      "#FF6B9D",      # 赛博粉（警告/删除）

    # 文字层级
    "text":         "#F0F0F0",      # 主文字
    "text2":        "#A0A0A0",      # 次要文字
    "text3":        "#606060",      # 占位符/禁用态

    # 语义色
    "red":          "#FF4757",
    "green":        "#2ED573",
    "blue":        "#1E90FF",
    "warn":         "#FFA502",
}

# 字体系统
FONT_TITLE   = ("Segoe UI Semibold", 22, "bold")
FONT_H2      = ("Segoe UI Semibold", 13)
FONT_BODY    = ("Segoe UI", 11)
FONT_SMALL   = ("Segoe UI", 9)
FONT_MONO    = ("Cascadia Code", 11)
FONT_MONO_SM = ("Cascadia Code", 10)

# 间距系统 (全局呼吸感)
PAD_XS = 4
PAD_SM = 8
PAD_MD = 12
PAD_LG = 16
PAD_XL = 24
PAD_XXL = 32

# 组件尺寸
BTN_HEIGHT_SM = 28
BTN_HEIGHT_MD = 34
BTN_HEIGHT_LG = 40
INPUT_HEIGHT = 32
CORNER_RADIUS = 8
CORNER_RADIUS_LG = 12

# ============ 管线类型枚举 ============
class PipelineType:
    TEXT_TO_VIDEO = "t2v"      # 纯文本生成视频，不需要参考图
    IMAGE_TO_VIDEO = "i2v"     # 图像驱动视频生成，必须有参考图
    REF_TO_VIDEO = "r2v"       # 参考视频驱动，必须有参考视频
    VIDEO_EDIT = "edit"        # 视频编辑，必须有素材
    TEXT_TO_IMAGE = "text2img" # 文本生成图像
    IMAGE_GEN = "img"          # 图像生成

def get_pipeline_type(model: str) -> str:
    """根据模型ID自动判断管线类型"""
    model_lower = model.lower()
    if model_lower.endswith("-t2v") or "-t2v-" in model_lower:
        return PipelineType.TEXT_TO_VIDEO
    elif model_lower.endswith("-i2v") or "-i2v-" in model_lower:
        return PipelineType.IMAGE_TO_VIDEO
    elif model_lower.endswith("-r2v") or "-r2v-" in model_lower:
        return PipelineType.REF_TO_VIDEO
    elif "videoedit" in model_lower or "video-edit" in model_lower:
        return PipelineType.VIDEO_EDIT
    else:
        return PipelineType.IMAGE_GEN

# ============ 阿里云百炼模型分类 ============
BAILIAN_MODEL_MAP = {
    "图像生成 (Image)": [
        "qwen-image-2.0-pro",
        "qwen-image-2.0-pro-2026-04-22",
        "qwen-image-2.0-pro-2026-03-03",
        "wan2.7-image-pro",
        "qwen-image-2.0",
        "qwen-image-2.0-2026-03-03",
        "wan2.7-image",
    ],
    "视频生成 (Video)": [
        "wan2.7-t2v", "wan2.7-t2v-2026-04-25",
        "wan2.7-i2v", "wan2.7-i2v-2026-04-25",
        "wan2.7-r2v",
        "happyhorse-1.0-t2v", "happyhorse-1.0-i2v", "happyhorse-1.0-r2v",
        "wan2.7-videoedit", "happyhorse-1.0-video-edit",
    ],
}

# 模型名 → 显示名（下拉框里看到的）
def _model_hint(model: str) -> str:
    p = get_pipeline_type(model)
    hints = {
        PipelineType.TEXT_TO_VIDEO:   "✅ 无需参考图",
        PipelineType.IMAGE_TO_VIDEO:  "📎 需要参考图",
        PipelineType.REF_TO_VIDEO:    "📎 需要参考视频",
        PipelineType.VIDEO_EDIT:      "📎 需要素材",
        PipelineType.IMAGE_GEN:       "✏️ 文生图",
    }
    return f"{model}  ({hints.get(p, '')})"

def _extract_model_id(display_name: str) -> str:
    """从显示名 'wan2.7-i2v (📎 需要参考图)' 还原出模型ID 'wan2.7-i2v'"""
    return display_name.split("  (")[0].strip()

# 模型到管线类型的映射缓存
MODEL_PIPELINE_CACHE = {}
for _models in BAILIAN_MODEL_MAP.values():
    for _m in _models:
        MODEL_PIPELINE_CACHE[_m] = get_pipeline_type(_m)

VIDEO_MODELS = BAILIAN_MODEL_MAP["视频生成 (Video)"]
EDIT_MODELS  = [m for m in VIDEO_MODELS if "videoedit" in m or "video-edit" in m]
IMAGE_MODELS = BAILIAN_MODEL_MAP["图像生成 (Image)"]

BAILIAN_BASE_URL = "https://dashscope.aliyuncs.com/api/v1"

# ============ Vidu 视频生成 API ============
VIDU_BASE_URL = "https://api.vidu.cn"
VIDU_MODELS = [
    "viduq3-pro",    # 高效生成优质音视频，效果最好
    "viduq3-turbo",  # 对比q3-pro生成速度更快
    "viduq2",        # 最新模型
    "viduq1",        # 画面清晰，平滑转场，运镜稳定
]
VIDU_STYLES = ["general", "anime"]
VIDU_RESOLUTIONS = ["540p", "720p", "1080p"]
VIDU_ASPECT_RATIOS = ["16:9", "9:16", "1:1", "3:4", "4:3"]
VIDU_MOVEMENT_AMPLITUDES = ["auto", "small", "medium", "large"]

# 积分单价 (积分/秒)
VIDU_CREDIT_RATES = {"1080p": 24, "720p": 20, "540p": 9}

# 各模型支持的时长范围
VIDU_MODEL_DURATION = {
    "viduq3-pro":   (1, 16),
    "viduq3-turbo": (1, 16),
    "viduq2":       (1, 10),
    "viduq1":       (5, 5),
}

# ============ 配置 ============
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "api_base_url": "https://token-plan-cn.xiaomimimo.com/anthropic",
    "api_key": "tp-clgfpo6b15ix395enlisuyd5eifnderql0r4215zyifj3v5t",
    "api_model": "mimo-v2.5-pro",
    "image_width": "1920", "image_height": "1080",
    "dark_mode": True,
    "bailian_api_key": "", "bailian_mode": "图像生成 (Image)",
    "bailian_model": "qwen-image-2.0-pro", "bailian_video_duration": "5",
    "bailian_ratio": "1:1 (正方形)",
    "tts_engine": "bailian", "tts_voice": "sambert-zhichu-v1", "tts_custom_model": "",
    "tts_ref_audio": "", "tts_prompt_text": "", "tts_adv_mode": "preset",
    "sovits_url": "http://127.0.0.1:8080",
    "sovits_bat_path": r"D:\剪映\声音克隆\一键启动.bat",
    "sovits_character": "", "sovits_emotion": "平静",
    "mimo_api_key": "", "mimo_model": "MiMo-V2.5-TTS", "mimo_voice": "mimo-female-01",
    "vidu_api_key": "", "vidu_model": "viduq3-pro",
    "vidu_duration": "5", "vidu_resolution": "720p",
    "vidu_style": "general", "vidu_aspect_ratio": "16:9",
    "vidu_seed": "0", "vidu_bgm": False, "vidu_audio": True,
    "vidu_off_peak": False, "vidu_watermark": False,
    "vidu_movement_amplitude": "auto",
    "project_name": "",
    "save_path": "",
}

VISUAL_SUFFIX = "cinematic lighting, breathtaking depth of field, hyper-realistic textures, 8k resolution, Unreal Engine 5 style render, high-contrast"

SYSTEM_PROMPT = """你是一位专业的悬疑与科幻影视导演兼分镜师。
用户会给你一个故事创意或剧情大纲，你需要：
1. 根据剧情节奏，动态决定需要的镜头数量（不需要固定数量，可以是3~15个镜头，按剧情自然拆分）。
2. 每个镜头必须包含以下字段：
   - 镜头编号 (Shot Number)
   - 景别 (Shot Type): 如大远景、远景、全景、中景、近景、特写、大特写
   - 时长 (Duration): 如 3s, 5s
   - 画面描述 (Visual Description): 详细的中文画面描述
   - 英文Prompt: 可直接用于AI图像/视频生成的英文 Prompt
   - 运镜方式 (Camera Movement): 如推、拉、摇、移、跟、升、降、固定
   - 配乐/音效建议 (Audio Suggestion): 简短的配乐或音效描述
3. 输出格式使用清晰的结构化文本，每个镜头之间用分隔线隔开。
4. Prompt 必须是英文，适合AI图像或视频生成模型使用。
请用中文输出整体结构，英文 Prompt 部分用英文。"""


def load_config():
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            merged = {**DEFAULT_CONFIG, **cfg}
            return merged
    except (json.JSONDecodeError, PermissionError, OSError) as e:
        print(f"[警告] config.json 读取失败，使用默认配置: {e}")
    return dict(DEFAULT_CONFIG)


def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except (PermissionError, OSError) as e:
        print(f"[警告] config.json 保存失败: {e}")


# ============ 辅助组件 v7.0 ============

class SectionCard(ctk.CTkFrame):
    """卡片容器 — 赛博极客风格"""
    def __init__(self, master, title="", **kwargs):
        super().__init__(
            master,
            fg_color=C["surface"],
            corner_radius=CORNER_RADIUS_LG,
            border_width=1,
            border_color=C["border"],
            **kwargs
        )
        if title:
            ctk.CTkLabel(
                self, text=title, font=FONT_H2,
                text_color=C["accent"]
            ).pack(anchor="w", padx=PAD_LG, pady=(PAD_MD, PAD_SM))


class LogBox(ctk.CTkTextbox):
    """日志文本框 — 紧凑风格"""
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            font=FONT_MONO_SM,
            fg_color=C["surface2"],
            text_color=C["text2"],
            corner_radius=CORNER_RADIUS,
            border_width=1,
            border_color=C["border"],
            state="disabled",
            **kwargs
        )

    def append(self, msg):
        self.configure(state="normal")
        self.insert("end", msg + "\n")
        self.see("end")
        self.configure(state="disabled")

    def clear_all(self):
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.configure(state="disabled")


class CyberButton(ctk.CTkButton):
    """赛博风格按钮"""
    def __init__(self, master, variant="primary", **kwargs):
        styles = {
            "primary": {
                "fg_color": C["accent"],
                "hover_color": C["accent_dim"],
                "text_color": C["bg"],
            },
            "secondary": {
                "fg_color": C["surface2"],
                "hover_color": C["surface3"],
                "text_color": C["text"],
            },
            "danger": {
                "fg_color": C["accent3"],
                "hover_color": "#FF4757",
                "text_color": "#FFFFFF",
            },
        }
        style = styles.get(variant, styles["primary"])
        defaults = {
            "corner_radius": CORNER_RADIUS,
            "height": BTN_HEIGHT_MD,
            "font": FONT_BODY,
        }
        defaults.update(style)
        defaults.update(kwargs)
        super().__init__(master, **defaults)


# ============ 主应用 ============

class BatchProcessor:
    NAV_ITEMS = [
        ("Script",  "剧本生成"),
        ("Visuals", "视觉引擎"),
        ("Vidu",    "🎬 Vidu 视频"),
        ("Voice",   "智能配音"),
        ("API",     "全局设置"),
        ("Assembly", "一键总装"),
    ]

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("AI Content Studio v7.0")
        self.root.geometry("1600x960")
        self.root.minsize(1400, 800)
        self.root.configure(fg_color=C["bg"])

        self.config = load_config()
        self.selected_files = []
        self._char_name_to_id = {}
        self.output_dir = ""
        self._current_page = None
        self._is_shutting_down = False  # 防止关闭时线程回调闪退

        # MiMo 历史记录
        self._mimo_history_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mimo_chat_history.json")
        self._mimo_messages = []  # 当前会话的消息列表
        self._mimo_session_id = time.strftime("%Y%m%d_%H%M%S")  # 当前会话ID

        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        self._build_sidebar()
        self._build_pages()
        self._build_floating_mimo_button()
        self._show_page("Script")

    def _on_closing(self):
        """安全关闭 — 防止线程回调访问已销毁的 tkinter"""
        self._is_shutting_down = True
        try:
            self.root.quit()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def safe_after(self, func):
        """线程安全的 GUI 回调包装 — 关闭时跳过"""
        if self._is_shutting_down:
            return
        try:
            self.root.after(0, func)
        except (tk.TclError, RuntimeError):
            pass

    # ==================== 侧边栏 v7.0 ====================

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self.root, width=180, fg_color=C["surface"],
            corner_radius=0, border_width=0
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Logo 区
        ctk.CTkLabel(
            self.sidebar, text="⚡ AI Studio",
            font=FONT_TITLE, text_color=C["accent"]
        ).pack(pady=(PAD_XXL, PAD_XL), padx=PAD_LG, anchor="w")

        # 导航按钮
        self.nav_buttons = {}
        for key, label in self.NAV_ITEMS:
            btn = ctk.CTkButton(
                self.sidebar,
                text=f"  {label}",
                font=FONT_BODY,
                fg_color="transparent",
                hover_color=C["surface2"],
                text_color=C["text"],
                anchor="w",
                height=42,
                corner_radius=CORNER_RADIUS,
                command=lambda k=key: self._show_page(k)
            )
            btn.pack(fill="x", padx=PAD_SM, pady=PAD_XS)
            self.nav_buttons[key] = btn

        # 日志抽屉切换按钮
        self._log_visible = False
        self.log_toggle_btn = ctk.CTkButton(
            self.sidebar,
            text="📋 终端日志",
            font=FONT_SMALL,
            fg_color=C["surface2"],
            hover_color=C["surface3"],
            text_color=C["text2"],
            anchor="w",
            height=36,
            corner_radius=CORNER_RADIUS,
            command=self._toggle_log_drawer
        )
        self.log_toggle_btn.pack(fill="x", padx=PAD_SM, pady=(PAD_LG, PAD_XS), side="bottom")

        # 底部版本
        ctk.CTkLabel(
            self.sidebar, text="v7.0 · Cyber Edition",
            font=FONT_SMALL, text_color=C["text3"]
        ).pack(side="bottom", pady=PAD_SM, padx=PAD_LG, anchor="w")

    def _show_page(self, key):
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.configure(
                    fg_color=C["accent"],
                    text_color=C["bg"],
                    hover_color=C["accent_dim"]
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=C["text"],
                    hover_color=C["surface2"]
                )
        for frame in self.page_frames.values():
            frame.pack_forget()
        self.page_frames[key].pack(side="right", fill="both", expand=True)
        self._current_page = key

    # ==================== 页面构建 ====================

    def _build_pages(self):
        self.page_frames = {}
        for key, _ in self.NAV_ITEMS:
            frame = ctk.CTkFrame(self.root, fg_color=C["bg"], corner_radius=0)
            self.page_frames[key] = frame

        # 构建全局日志抽屉（初始隐藏）
        self._build_log_drawer()

        self._build_page_script(self.page_frames["Script"])
        self._build_page_visuals(self.page_frames["Visuals"])
        self._build_page_vidu(self.page_frames["Vidu"])
        self._build_page_voice(self.page_frames["Voice"])
        self._build_page_api(self.page_frames["API"])
        self._build_page_assembly(self.page_frames["Assembly"])


    # ==================== MiMo 全局悬浮按钮 ====================

    def _build_floating_mimo_button(self):
        """右下角悬浮 MiMo 按钮 — 全局置顶"""
        self._mimo_fab = ctk.CTkButton(
            self.root,
            text="🤖",
            font=("Segoe UI Emoji", 22),
            width=52,
            height=52,
            corner_radius=26,
            fg_color=C["accent"],
            hover_color=C["accent_dim"],
            text_color=C["bg"],
            command=self._open_mimo_floating_chat,
        )
        # place 绝对定位，右下角
        self._mimo_fab.place(relx=1.0, rely=1.0, x=-24, y=-24, anchor="se")
        self.root.bind("<Configure>", self._reposition_mimo_fab)

    def _reposition_mimo_fab(self, event=None):
        if hasattr(self, "_mimo_fab") and self._mimo_fab.winfo_exists():
            self._mimo_fab.place(relx=1.0, rely=1.0, x=-24, y=-24, anchor="se")

    def _open_mimo_floating_chat(self):
        """打开 MiMo 悬浮聊天窗口"""
        if hasattr(self, "_mimo_chat_win") and self._mimo_chat_win is not None and self._mimo_chat_win.winfo_exists():
            self._mimo_chat_win.lift()
            self._mimo_chat_win.focus_force()
            return

        win = ctk.CTkToplevel(self.root)
        win.title("🤖 MiMo AI 智能体")
        win.geometry("480x600")
        win.configure(fg_color=C["bg"])
        win.attributes("-topmost", True)
        self._mimo_chat_win = win

        header = ctk.CTkFrame(win, fg_color=C["surface"], corner_radius=0)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="🤖 MiMo AI 智能体", font=FONT_H2,
                     text_color=C["accent"]).pack(side="left", padx=PAD_MD, pady=PAD_SM)
        ctk.CTkButton(header, text="✕", font=FONT_BODY, width=30,
                       fg_color="transparent", hover_color=C["accent3"],
                       text_color=C["text2"], corner_radius=4,
                       command=win.destroy).pack(side="right", padx=PAD_SM)

        ctk.CTkLabel(win, text="💡 命令: 提取script提示词 / 第3条改成xxx / 全部优化 / 开始生成",
                     font=FONT_SMALL, text_color=C["text3"],
                     wraplength=440).pack(anchor="w", padx=PAD_MD, pady=(PAD_SM, 2))

        chat_frame = ctk.CTkFrame(win, fg_color=C["surface2"], corner_radius=8,
                                   border_width=1, border_color=C["border"])
        chat_frame.pack(fill="both", expand=True, padx=PAD_MD, pady=(0, PAD_SM))

        self.agent_chat_history = ctk.CTkTextbox(
            chat_frame, font=FONT_BODY, fg_color="transparent",
            text_color=C["text"], corner_radius=0
        )
        self.agent_chat_history.pack(fill="both", expand=True, padx=4, pady=4)
        self.agent_chat_history.configure(state="disabled")

        input_row = ctk.CTkFrame(win, fg_color="transparent")
        input_row.pack(fill="x", padx=PAD_MD, pady=(0, PAD_MD))

        self.agent_input = ctk.CTkEntry(
            input_row, font=FONT_BODY,
            fg_color=C["surface2"], border_color=C["border"],
            corner_radius=8, placeholder_text="输入命令给 MiMo..."
        )
        self.agent_input.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(input_row, text="发送", font=FONT_BODY, width=60,
                       fg_color=C["accent"], text_color=C["bg"],
                       hover_color=C["accent2"], corner_radius=8,
                       command=self._agent_send_command).pack(side="left")
        self.agent_input.bind("<Return>", lambda e: self._agent_send_command())

        def _on_close():
            self._mimo_chat_win = None
            win.destroy()
        win.protocol("WM_DELETE_WINDOW", _on_close)

    def _build_log_drawer(self):
        """构建全局日志抽屉面板"""
        self.log_drawer = ctk.CTkFrame(
            self.root, fg_color=C["surface"], width=350,
            corner_radius=0, border_width=0
        )
        # 初始状态隐藏

        # 抽屉头部
        drawer_header = ctk.CTkFrame(self.log_drawer, fg_color=C["surface2"], corner_radius=0)
        drawer_header.pack(fill="x")
        ctk.CTkLabel(drawer_header, text="📋 终端日志", font=FONT_H2,
                     text_color=C["accent"]).pack(side="left", padx=PAD_MD, pady=PAD_SM)
        ctk.CTkButton(drawer_header, text="✕", font=FONT_BODY, width=30,
                       fg_color="transparent", hover_color=C["accent3"],
                       text_color=C["text2"], corner_radius=4,
                       command=self._toggle_log_drawer).pack(side="right", padx=PAD_SM)

        # 日志内容区
        self.global_log = LogBox(self.log_drawer)
        self.global_log.pack(fill="both", expand=True, padx=PAD_SM, pady=PAD_SM)

        # 清空按钮
        ctk.CTkButton(self.log_drawer, text="清空日志", font=FONT_SMALL,
                       fg_color=C["surface2"], hover_color=C["accent3"],
                       text_color=C["text2"], corner_radius=CORNER_RADIUS,
                       height=BTN_HEIGHT_SM,
                       command=self.global_log.clear_all).pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))

    def _toggle_log_drawer(self):
        """切换日志抽屉显示/隐藏"""
        if self._log_visible:
            self.log_drawer.pack_forget()
            self._log_visible = False
            self.log_toggle_btn.configure(fg_color=C["surface2"], text_color=C["text2"])
        else:
            self.log_drawer.pack(side="right", fill="y", before=self.page_frames.get(self._current_page, self.page_frames["Script"]))
            self._log_visible = True
            self.log_toggle_btn.configure(fg_color=C["accent"], text_color=C["bg"])

    def _global_log_msg(self, msg):
        """写入全局日志"""
        ts = time.strftime("%H:%M:%S")
        self.safe_after( lambda: self.global_log.append(f"[{ts}] {msg}"))

    # ---------- Script 页面 ----------

    def _build_page_script(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color=C["bg"])
        scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(scroll, text="动态剧本与分镜生成", font=FONT_TITLE,
                     text_color=C["text"]).pack(anchor="w", padx=20, pady=(16, 8))

        # 输入区
        card = SectionCard(scroll, title="故事创意 / 剧情大纲")
        card.pack(fill="x", padx=20, pady=(0, 12))

        self.story_input = ctk.CTkTextbox(card, height=100, font=FONT_BODY,
                                           fg_color=C["surface2"], text_color=C["text"],
                                           corner_radius=8, border_width=1,
                                           border_color=C["border"])
        self.story_input.pack(fill="x", padx=16, pady=(4, 12))
        self.story_input.insert("end", "例：一个废弃的太空站里，唯一的幸存者发现AI已经开始自己做梦...")

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 12))
        self.generate_btn = ctk.CTkButton(btn_row, text="生成动态镜头脚本",
                                           font=FONT_BODY, fg_color=C["accent"],
                                           text_color=C["bg"], hover_color=C["accent2"],
                                           corner_radius=10, height=38,
                                           command=self.start_generate_script)
        self.generate_btn.pack(side="left")
        ctk.CTkButton(btn_row, text="清空", font=FONT_BODY, width=70,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text"], corner_radius=10, height=38,
                       command=lambda: self.story_input.delete("1.0", "end")
                       ).pack(side="left", padx=8)
        ctk.CTkButton(btn_row, text="导出 TXT", font=FONT_BODY, width=90,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text"], corner_radius=10, height=38,
                       command=self.export_script).pack(side="left")
        ctk.CTkButton(btn_row, text="复制全部", font=FONT_BODY, width=80,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text"], corner_radius=10, height=38,
                       command=self.copy_script).pack(side="left", padx=8)

        # 输出区
        card2 = SectionCard(scroll, title="生成的镜头脚本")
        card2.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.script_output = ctk.CTkTextbox(card2, font=FONT_MONO,
                                             fg_color=C["surface2"], text_color=C["text"],
                                             corner_radius=8, border_width=1,
                                             border_color=C["border"])
        self.script_output.pack(fill="both", expand=True, padx=16, pady=(4, 16))

    # ---------- Visuals 页面 ----------

    def _build_page_visuals(self, parent):
        # 垂直流布局 — 全宽滚动
        scroll = ctk.CTkScrollableFrame(
            parent, fg_color=C["bg"],
            scrollbar_button_color=C["border"],
            scrollbar_button_hover_color=C["text3"]
        )
        scroll.pack(fill="both", expand=True, padx=PAD_MD, pady=PAD_MD)

        # ---- 图片批处理 ----
        ctk.CTkLabel(scroll, text="图片批处理", font=FONT_H2,
                     text_color=C["accent"]).pack(anchor="w", pady=(0, 12))

        card = SectionCard(scroll, title="选择图片")
        card.pack(fill="x", pady=(0, 8))
        file_btn_row = ctk.CTkFrame(card, fg_color="transparent")
        file_btn_row.pack(fill="x", padx=16, pady=(4, 4))
        ctk.CTkButton(file_btn_row, text="添加图片", font=FONT_SMALL, width=80,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text"], corner_radius=6, height=28,
                       command=self.select_images).pack(side="left")
        ctk.CTkButton(file_btn_row, text="清空列表", font=FONT_SMALL, width=80,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text2"], corner_radius=6, height=28,
                       command=self.clear_list).pack(side="left", padx=6)
        self.file_count_label = ctk.CTkLabel(file_btn_row, text="已选: 0 张",
                                              font=FONT_SMALL, text_color=C["text3"])
        self.file_count_label.pack(side="left", padx=8)

        card = SectionCard(scroll, title="处理模式")
        card.pack(fill="x", pady=(0, 8))
        self.mode_var = tk.StringVar(value="resize")
        mode_row = ctk.CTkFrame(card, fg_color="transparent")
        mode_row.pack(fill="x", padx=16, pady=(4, 4))
        ctk.CTkRadioButton(mode_row, text="调整尺寸", variable=self.mode_var, value="resize",
                            font=FONT_BODY, fg_color=C["accent"], text_color=C["text"],
                            hover_color=C["accent2"]).pack(side="left", padx=(0, 16))
        ctk.CTkRadioButton(mode_row, text="九宫格切分", variable=self.mode_var, value="nine_grid",
                            font=FONT_BODY, fg_color=C["accent"], text_color=C["text"],
                            hover_color=C["accent2"]).pack(side="left")

        self.size_row = ctk.CTkFrame(card, fg_color="transparent")
        self.size_row.pack(fill="x", padx=16, pady=(4, 4))
        ctk.CTkLabel(self.size_row, text="宽:", font=FONT_SMALL, text_color=C["text2"]).pack(side="left")
        self.width_var = tk.StringVar(value=self.config.get("image_width", "1920"))
        ctk.CTkEntry(self.size_row, textvariable=self.width_var, width=80, font=FONT_MONO,
                      fg_color=C["surface2"], border_color=C["border"],
                      corner_radius=8).pack(side="left", padx=(2, 12))
        ctk.CTkLabel(self.size_row, text="高:", font=FONT_SMALL, text_color=C["text2"]).pack(side="left")
        self.height_var = tk.StringVar(value=self.config.get("image_height", "1080"))
        ctk.CTkEntry(self.size_row, textvariable=self.height_var, width=80, font=FONT_MONO,
                      fg_color=C["surface2"], border_color=C["border"],
                      corner_radius=8).pack(side="left", padx=(2, 0))

        # ---- 九宫格可视化预览面板 ----
        self.nine_grid_panel = ctk.CTkFrame(scroll, fg_color=C["surface"],
                                             corner_radius=12, border_width=1, border_color=C["border"])

        # 九宫格参考线位置（相对坐标 0~1）
        self.ng_col_lines = [0.333, 0.667]
        self.ng_row_lines = [0.333, 0.667]
        self.ng_dragging = None
        self.ng_image_scale = 1.0
        self.ng_img_offset = (0, 0)
        self.ng_img_display_size = (0, 0)

        ng_header = ctk.CTkFrame(self.nine_grid_panel, fg_color="transparent")
        ng_header.pack(fill="x", padx=12, pady=(8, 4))
        ctk.CTkLabel(ng_header, text="九宫格可视化切分", font=FONT_H2,
                     text_color=C["accent"]).pack(side="left")
        self.ng_info_label = ctk.CTkLabel(ng_header, text="请先添加图片",
                                           font=FONT_SMALL, text_color=C["text3"])
        self.ng_info_label.pack(side="left", padx=12)

        ng_toolbar = ctk.CTkFrame(self.nine_grid_panel, fg_color="transparent")
        ng_toolbar.pack(fill="x", padx=12, pady=(0, 4))

        ctk.CTkLabel(ng_toolbar, text="列线1:", font=FONT_SMALL, text_color=C["text2"]).pack(side="left")
        self.ng_col1_var = tk.StringVar(value="33.3%")
        ctk.CTkEntry(ng_toolbar, textvariable=self.ng_col1_var, width=60, font=FONT_MONO_SM,
                      fg_color=C["surface2"], border_color=C["border"], corner_radius=6).pack(side="left", padx=2)
        ctk.CTkLabel(ng_toolbar, text="列线2:", font=FONT_SMALL, text_color=C["text2"]).pack(side="left", padx=(8, 0))
        self.ng_col2_var = tk.StringVar(value="66.7%")
        ctk.CTkEntry(ng_toolbar, textvariable=self.ng_col2_var, width=60, font=FONT_MONO_SM,
                      fg_color=C["surface2"], border_color=C["border"], corner_radius=6).pack(side="left", padx=2)
        ctk.CTkLabel(ng_toolbar, text="行线1:", font=FONT_SMALL, text_color=C["text2"]).pack(side="left", padx=(8, 0))
        self.ng_row1_var = tk.StringVar(value="33.3%")
        ctk.CTkEntry(ng_toolbar, textvariable=self.ng_row1_var, width=60, font=FONT_MONO_SM,
                      fg_color=C["surface2"], border_color=C["border"], corner_radius=6).pack(side="left", padx=2)
        ctk.CTkLabel(ng_toolbar, text="行线2:", font=FONT_SMALL, text_color=C["text2"]).pack(side="left", padx=(8, 0))
        self.ng_row2_var = tk.StringVar(value="66.7%")
        ctk.CTkEntry(ng_toolbar, textvariable=self.ng_row2_var, width=60, font=FONT_MONO_SM,
                      fg_color=C["surface2"], border_color=C["border"], corner_radius=6).pack(side="left", padx=2)

        ctk.CTkButton(ng_toolbar, text="应用", font=FONT_SMALL, width=50,
                       fg_color=C["accent"], text_color=C["bg"], hover_color=C["accent2"],
                       corner_radius=6, height=26, command=self._ng_apply_manual).pack(side="left", padx=6)
        ctk.CTkButton(ng_toolbar, text="重置", font=FONT_SMALL, width=50,
                       fg_color=C["surface2"], text_color=C["text2"], hover_color=C["border"],
                       corner_radius=6, height=26, command=self._ng_reset_lines).pack(side="left")

        # 像素坐标显示
        self.ng_pixel_label = ctk.CTkLabel(self.nine_grid_panel, text="像素坐标: --",
                                            font=FONT_MONO_SM, text_color=C["text3"])
        self.ng_pixel_label.pack(anchor="w", padx=12, pady=(0, 4))

        # 画布区域
        canvas_container = ctk.CTkFrame(self.nine_grid_panel, fg_color=C["bg"],
                                         corner_radius=8, border_width=1, border_color=C["border"])
        canvas_container.pack(fill="both", expand=True, padx=12, pady=(0, 4))

        self.ng_canvas = tk.Canvas(canvas_container, bg="#111111", highlightthickness=0)
        self.ng_canvas.pack(fill="both", expand=True)

        self.ng_canvas.bind("<Button-1>", self._ng_on_mouse_down)
        self.ng_canvas.bind("<B1-Motion>", self._ng_on_mouse_drag)
        self.ng_canvas.bind("<ButtonRelease-1>", self._ng_on_mouse_up)
        self.ng_canvas.bind("<Motion>", self._ng_on_mouse_move)
        self.ng_canvas.bind("<Configure>", lambda e: self._ng_redraw())

        # 右侧九宫格预览缩略图
        preview_row = ctk.CTkFrame(self.nine_grid_panel, fg_color="transparent")
        preview_row.pack(fill="x", padx=12, pady=(0, 8))
        ctk.CTkLabel(preview_row, text="切分预览:", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w", pady=(0, 4))

        preview_grid = ctk.CTkFrame(preview_row, fg_color="transparent")
        preview_grid.pack(anchor="w")
        self.ng_preview_labels = []
        for i in range(9):
            lbl = ctk.CTkLabel(preview_grid, text="", width=60, height=60,
                                fg_color=C["surface2"], corner_radius=4)
            lbl.grid(row=i // 3, column=i % 3, padx=2, pady=2)
            self.ng_preview_labels.append(lbl)

        # 模式切换回调
        self.mode_var.trace_add("write", self._on_mode_switch)
        self._on_mode_switch()

        ctk.CTkButton(scroll, text="开始处理", font=FONT_H2,
                       fg_color=C["accent"], text_color=C["bg"],
                       hover_color=C["accent2"], corner_radius=12, height=40,
                       command=self.start_processing).pack(fill="x", padx=20, pady=(0, 4))
        ctk.CTkButton(scroll, text="打开输出目录", font=FONT_SMALL,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text2"], corner_radius=8, height=28,
                       command=self.open_output_dir).pack(anchor="w", padx=20, pady=(0, 16))

        # ---- 百炼视觉引擎 ----
        ctk.CTkLabel(scroll, text="阿里云百炼视觉引擎", font=FONT_H2,
                     text_color=C["accent"]).pack(anchor="w", pady=(0, 12))

        # API Key
        card = SectionCard(scroll, title="百炼 API Key")
        card.pack(fill="x", pady=(0, 8))
        self.bailian_key_var = tk.StringVar(value=self.config.get("bailian_api_key", ""))
        self.bailian_key_entry = ctk.CTkEntry(card, textvariable=self.bailian_key_var,
                                               show="*", font=FONT_MONO,
                                               fg_color=C["surface2"], border_color=C["border"],
                                               corner_radius=8)
        self.bailian_key_entry.pack(fill="x", padx=16, pady=(4, 4))
        key_row = ctk.CTkFrame(card, fg_color="transparent")
        key_row.pack(fill="x", padx=16, pady=(0, 10))
        self.bailian_key_visible = tk.BooleanVar(value=False)
        ctk.CTkButton(key_row, text="显示/隐藏", width=80, font=FONT_SMALL,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text2"], corner_radius=6, height=28,
                       command=self.toggle_bailian_key_vis).pack(side="left")
        ctk.CTkLabel(key_row, text="在阿里云百炼控制台获取",
                     font=FONT_SMALL, text_color=C["text3"]).pack(side="left", padx=8)

        # 生成模式
        card = SectionCard(scroll, title="生成模式")
        card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(card, text="第一步：选择模式类别", font=FONT_SMALL,
                     text_color=C["text2"]).pack(anchor="w", padx=16, pady=(4, 0))
        self.bailian_mode_var = tk.StringVar(value=self.config.get("bailian_mode", list(BAILIAN_MODEL_MAP.keys())[0]))
        self.bailian_mode_combo = ctk.CTkComboBox(card, variable=self.bailian_mode_var,
                                                    values=list(BAILIAN_MODEL_MAP.keys()),
                                                    font=FONT_BODY, dropdown_font=FONT_BODY,
                                                    fg_color=C["surface2"], border_color=C["border"],
                                                    button_color=C["border"], button_hover_color=C["text3"],
                                                    corner_radius=8, command=self._on_mode_changed)
        self.bailian_mode_combo.pack(fill="x", padx=16, pady=(2, 8))

        ctk.CTkLabel(card, text="第二步：选择具体模型", font=FONT_SMALL,
                     text_color=C["text2"]).pack(anchor="w", padx=16)
        self.bailian_model_var = tk.StringVar(value=self.config.get("bailian_model", ""))
        self.bailian_model_combo = ctk.CTkComboBox(card, variable=self.bailian_model_var,
                                                    values=[], font=FONT_MONO,
                                                    fg_color=C["surface2"], border_color=C["border"],
                                                    button_color=C["border"], button_hover_color=C["text3"],
                                                    corner_radius=8, command=self._on_model_changed)
        self.bailian_model_combo.pack(fill="x", padx=16, pady=(2, 12))
        self._update_model_combo()

        # 画面比例
        card = SectionCard(scroll, title="画面比例")
        card.pack(fill="x", pady=(0, 8))

        self.ratio_map = {
            "1:1 (正方形)":       {"size": "1024*1024", "w": 1024, "h": 1024},
            "16:9 (横屏宽屏)":    {"size": "1280*720",  "w": 1280, "h": 720},
            "9:16 (竖屏短视频)":  {"size": "720*1280",  "w": 720,  "h": 1280},
            "4:3 (传统横屏)":     {"size": "1024*768",  "w": 1024, "h": 768},
            "3:4 (传统竖屏)":     {"size": "768*1024",  "w": 768,  "h": 1024},
            "3:2 (摄影横屏)":     {"size": "1152*768",  "w": 1152, "h": 768},
            "2:3 (摄影竖屏)":     {"size": "768*1152",  "w": 768,  "h": 1152},
        }
        ratio_names = list(self.ratio_map.keys())
        saved_ratio = self.config.get("bailian_ratio", ratio_names[0])
        if saved_ratio not in self.ratio_map:
            saved_ratio = ratio_names[0]

        self.bailian_ratio_var = tk.StringVar(value=saved_ratio)
        self.bailian_ratio_combo = ctk.CTkComboBox(card, variable=self.bailian_ratio_var,
                                                    values=ratio_names, font=FONT_BODY,
                                                    dropdown_font=FONT_BODY,
                                                    fg_color=C["surface2"], border_color=C["border"],
                                                    button_color=C["border"], button_hover_color=C["text3"],
                                                    corner_radius=8, command=self._on_ratio_changed)
        self.bailian_ratio_combo.pack(fill="x", padx=16, pady=(4, 4))
        self.ratio_hint = ctk.CTkLabel(card, text=f"输出尺寸: {self.ratio_map[saved_ratio]['size']}",
                                        font=FONT_MONO_SM, text_color=C["text3"])
        self.ratio_hint.pack(anchor="w", padx=16, pady=(0, 12))

        # 视频设置
        self.video_settings_frame = SectionCard(scroll, title="视频设置")
        ctk.CTkLabel(self.video_settings_frame, text="视频时长 (秒):", font=FONT_SMALL,
                     text_color=C["text2"]).pack(anchor="w", padx=16, pady=(4, 0))
        dur_row = ctk.CTkFrame(self.video_settings_frame, fg_color="transparent")
        dur_row.pack(fill="x", padx=16, pady=(2, 8))
        self.video_duration_var = tk.StringVar(value=self.config.get("bailian_video_duration", "5"))
        ctk.CTkEntry(dur_row, textvariable=self.video_duration_var, width=80,
                      font=FONT_MONO, fg_color=C["surface2"], border_color=C["border"],
                      corner_radius=8).pack(side="left")
        ctk.CTkLabel(dur_row, text="秒  (建议 3~10)", font=FONT_SMALL,
                     text_color=C["text3"]).pack(side="left", padx=8)

        # 管线类型横幅（醒目提示当前模式）
        self.pipeline_type_banner = ctk.CTkFrame(
            self.video_settings_frame, fg_color=C["green"],
            corner_radius=8, height=36
        )
        self.pipeline_type_banner.pack(fill="x", padx=16, pady=(8, 4))
        self.pipeline_type_banner.pack_propagate(False)
        self.pipeline_type_label = ctk.CTkLabel(
            self.pipeline_type_banner,
            text="📝 Text-to-Video — 无需参考图，纯文本驱动",
            font=FONT_H2,
            text_color=C["bg"]
        )
        self.pipeline_type_label.pack(expand=True)

        # 参考图区域（根据模型类型动态显示/隐藏）
        self.ref_image_frame = ctk.CTkFrame(self.video_settings_frame, fg_color="transparent")
        self.ref_image_frame.pack(fill="x", padx=0, pady=0)

        ctk.CTkLabel(self.ref_image_frame, text="参考图 (i2v/r2v/videoedit 必填):",
                     font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w", padx=16, pady=(4, 0))
        ref_row = ctk.CTkFrame(self.ref_image_frame, fg_color="transparent")
        ref_row.pack(fill="x", padx=16, pady=(2, 12))
        self.ref_image_path_var = tk.StringVar(value="")
        ctk.CTkEntry(ref_row, textvariable=self.ref_image_path_var, font=FONT_MONO_SM,
                      fg_color=C["surface2"], border_color=C["border"],
                      corner_radius=8).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(ref_row, text="浏览", width=60, font=FONT_SMALL,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text"], corner_radius=6, height=30,
                       command=self._browse_ref_image).pack(side="left", padx=(6, 0))
        self._toggle_video_settings()

        # Prompt
        card = SectionCard(scroll, title="Prompt / 描述")
        card.pack(fill="x", pady=(0, 8))

        # 镜头选择器
        shot_row = ctk.CTkFrame(card, fg_color="transparent")
        shot_row.pack(fill="x", padx=16, pady=(4, 4))
        ctk.CTkButton(shot_row, text="从 Script 提取 Prompt", font=FONT_SMALL,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["blue"], corner_radius=6, height=28,
                       command=self._fill_prompt_from_tab1).pack(side="left")
        self._parsed_shots = []
        self.bailian_shot_combo = ctk.CTkComboBox(
            shot_row, values=["请先提取"], font=FONT_SMALL, width=140,
            dropdown_font=FONT_SMALL, fg_color=C["surface2"], border_color=C["border"],
            button_color=C["border"], button_hover_color=C["text3"],
            corner_radius=8, command=self._on_shot_selected)
        self.bailian_shot_combo.pack(side="left", padx=(8, 0))
        self.bailian_shot_combo.set("请先提取")

        self.bailian_prompt_input = ctk.CTkTextbox(card, height=80, font=FONT_BODY,
                                                     fg_color=C["surface2"], text_color=C["text"],
                                                     corner_radius=8, border_width=1,
                                                     border_color=C["border"])
        self.bailian_prompt_input.pack(fill="x", padx=16, pady=(4, 8))

        # 生成按钮
        gen_row = ctk.CTkFrame(scroll, fg_color="transparent")
        gen_row.pack(fill="x", padx=20, pady=(0, 8))
        self.bailian_gen_btn = ctk.CTkButton(gen_row, text="生成当前镜头", font=FONT_H2,
                                              fg_color=C["accent"], text_color=C["bg"],
                                              hover_color=C["accent2"], corner_radius=12,
                                              height=44, command=self.start_bailian_generate)
        self.bailian_gen_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.bailian_batch_btn = ctk.CTkButton(gen_row, text="批量生成所有镜头", font=FONT_BODY,
                                                fg_color=C["surface2"], text_color=C["accent"],
                                                hover_color=C["border"], corner_radius=12,
                                                height=44, command=self._batch_generate_all_shots)
        self.bailian_batch_btn.pack(side="left")
        ctk.CTkButton(scroll, text="打开输出目录", font=FONT_SMALL,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text2"], corner_radius=8, height=30,
                       command=self._open_bailian_output).pack(anchor="w", padx=20, pady=(0, 16))

        # MiMo 智能体已移至全局悬浮按钮（右下角 🤖）

        # ========== 批量图生视频模块（重构版） ==========
        self.i2v_batch_card = SectionCard(scroll, title="批量图生视频 (Image-to-Video)")
        self.i2v_batch_card.pack(fill="x", padx=20, pady=(0, 16))

        # 顶部操作栏
        top_action_row = ctk.CTkFrame(self.i2v_batch_card, fg_color="transparent")
        top_action_row.pack(fill="x", padx=16, pady=(8, 4))
        ctk.CTkButton(
            top_action_row, text="+ 添加图片", font=FONT_SMALL, width=80,
            fg_color=C["accent"], hover_color=C["accent2"],
            text_color=C["bg"], corner_radius=6, height=28,
            command=self._i2v_batch_add_images
        ).pack(side="left")
        ctk.CTkButton(
            top_action_row, text="清空", font=FONT_SMALL, width=50,
            fg_color=C["surface2"], hover_color=C["border"],
            text_color=C["text2"], corner_radius=6, height=28,
            command=self._i2v_batch_clear
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            top_action_row, text="从 Script 提取", font=FONT_SMALL, width=100,
            fg_color=C["surface2"], hover_color=C["border"],
            text_color=C["blue"], corner_radius=6, height=28,
            command=self._i2v_extract_prompts_from_script
        ).pack(side="left", padx=4)
        self.i2v_batch_count_label = ctk.CTkLabel(
            top_action_row, text="0 图 / 0 提示词",
            font=FONT_SMALL, text_color=C["text3"]
        )
        self.i2v_batch_count_label.pack(side="right")

        # 视频时长设置
        duration_row = ctk.CTkFrame(self.i2v_batch_card, fg_color="transparent")
        duration_row.pack(fill="x", padx=16, pady=(4, 4))
        ctk.CTkLabel(duration_row, text="时长:", font=FONT_SMALL, text_color=C["text2"]).pack(side="left")
        self.i2v_duration_mode = tk.StringVar(value="auto")
        ctk.CTkRadioButton(duration_row, text="自动", variable=self.i2v_duration_mode, value="auto",
                           font=FONT_SMALL, fg_color=C["accent"], text_color=C["text"],
                           hover_color=C["accent2"], command=self._on_duration_mode_change).pack(side="left", padx=4)
        ctk.CTkRadioButton(duration_row, text="手动", variable=self.i2v_duration_mode, value="manual",
                           font=FONT_SMALL, fg_color=C["accent"], text_color=C["text"],
                           hover_color=C["accent2"], command=self._on_duration_mode_change).pack(side="left", padx=4)
        self.i2v_duration_entry = ctk.CTkEntry(duration_row, width=50, font=FONT_MONO_SM,
                                               fg_color=C["surface2"], border_color=C["border"],
                                               corner_radius=6, state="disabled")
        self.i2v_duration_entry.pack(side="left", padx=4)
        self.i2v_duration_entry.insert(0, "5")
        ctk.CTkLabel(duration_row, text="秒", font=FONT_SMALL, text_color=C["text3"]).pack(side="left")

        # 图片-提示词对应关系列表（核心区域）
        ctk.CTkLabel(self.i2v_batch_card, text="图片 ↔ 提示词对应关系:",
                     font=FONT_SMALL, text_color=C["text"]).pack(anchor="w", padx=16, pady=(8, 2))

        # 对应关系表格框架
        self.i2v_mapping_frame = ctk.CTkScrollableFrame(
            self.i2v_batch_card, fg_color=C["surface2"],
            corner_radius=8, border_width=1, border_color=C["border"],
            height=200
        )
        self.i2v_mapping_frame.pack(fill="x", padx=16, pady=(0, 8))

        # 表头
        header_row = ctk.CTkFrame(self.i2v_mapping_frame, fg_color="transparent")
        header_row.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(header_row, text="#", font=FONT_SMALL, text_color=C["text3"], width=30).pack(side="left")
        ctk.CTkLabel(header_row, text="预览", font=FONT_SMALL, text_color=C["text3"], width=60).pack(side="left", padx=2)
        ctk.CTkLabel(header_row, text="提示词", font=FONT_SMALL, text_color=C["text3"]).pack(side="left", padx=2, fill="x", expand=True)
        ctk.CTkLabel(header_row, text="时长", font=FONT_SMALL, text_color=C["text3"], width=40).pack(side="left", padx=2)
        ctk.CTkLabel(header_row, text="操作", font=FONT_SMALL, text_color=C["text3"], width=60).pack(side="left", padx=2)

        # 初始空状态提示
        self.i2v_empty_label = ctk.CTkLabel(
            self.i2v_mapping_frame, text="请先添加图片",
            font=FONT_SMALL, text_color=C["text3"]
        )
        self.i2v_empty_label.pack(pady=20)

        # 底部操作栏
        bottom_action_row = ctk.CTkFrame(self.i2v_batch_card, fg_color="transparent")
        bottom_action_row.pack(fill="x", padx=16, pady=(4, 12))
        ctk.CTkButton(
            bottom_action_row, text="MiMo 智能优化全部", font=FONT_SMALL, width=120,
            fg_color=C["blue"], hover_color="#3AA5E0",
            text_color="#FFF", corner_radius=6, height=32,
            command=self._i2v_mimo_analyze_all
        ).pack(side="left")
        ctk.CTkButton(
            bottom_action_row, text="开始批量生成", font=FONT_H2,
            fg_color=C["accent"], text_color=C["bg"],
            hover_color=C["accent2"], corner_radius=10, height=36,
            command=self._start_i2v_batch_generate
        ).pack(side="right")

        # 初始化批量图生视频数据
        self._i2v_batch_images = []
        self._i2v_mapping_rows = []  # 存储每一行的UI组件引用

        # 日志引用指向全局日志抽屉
        self.bailian_log = self.global_log

    # ==================== Vidu 视频页面 ====================

    def _build_page_vidu(self, parent):
        scroll = ctk.CTkScrollableFrame(
            parent, fg_color=C["bg"],
            scrollbar_button_color=C["border"],
            scrollbar_button_hover_color=C["text3"]
        )
        scroll.pack(fill="both", expand=True, padx=PAD_MD, pady=PAD_MD)

        # ---- 标题 ----
        ctk.CTkLabel(scroll, text="🎬 Vidu 视频生成引擎", font=FONT_H2,
                     text_color=C["accent"]).pack(anchor="w", pady=(0, 12))

        # ---- API Key ----
        card = SectionCard(scroll, title="🔑 API Key 认证")
        card.pack(fill="x", pady=(0, 8))
        key_row = ctk.CTkFrame(card, fg_color="transparent")
        key_row.pack(fill="x", padx=16, pady=(4, 4))
        self.vidu_key_var = tk.StringVar(value=self.config.get("vidu_api_key", ""))
        self.vidu_key_entry = ctk.CTkEntry(
            key_row, textvariable=self.vidu_key_var, show="•",
            font=FONT_MONO, fg_color=C["surface2"], border_color=C["border"],
            corner_radius=8, placeholder_text="输入 Vidu API Key..."
        )
        self.vidu_key_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.vidu_key_visible = tk.BooleanVar(value=False)
        ctk.CTkButton(key_row, text="👁", font=FONT_SMALL, width=36,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text2"], corner_radius=6, height=32,
                       command=self._toggle_vidu_key_vis).pack(side="left", padx=(0, 6))
        ctk.CTkButton(key_row, text="验证 Key", font=FONT_SMALL, width=70,
                       fg_color=C["accent"], text_color=C["bg"],
                       hover_color=C["accent_dim"], corner_radius=6, height=32,
                       command=self._vidu_validate_key).pack(side="left")

        # 积分显示
        self.vidu_credits_label = ctk.CTkLabel(
            card, text="积分: --", font=FONT_SMALL, text_color=C["text3"]
        )
        self.vidu_credits_label.pack(anchor="w", padx=16, pady=(0, 4))
        ctk.CTkButton(card, text="查询积分", font=FONT_SMALL, width=70,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text2"], corner_radius=6, height=26,
                       command=self._vidu_query_credits).pack(anchor="w", padx=16, pady=(0, 8))

        # ---- 模型 & 参数 ----
        card = SectionCard(scroll, title="⚙️ 渲染参数")
        card.pack(fill="x", pady=(0, 8))

        # 模型选择
        ctk.CTkLabel(card, text="模型", font=FONT_SMALL,
                     text_color=C["text2"]).pack(anchor="w", padx=16, pady=(4, 0))
        self.vidu_model_var = tk.StringVar(value=self.config.get("vidu_model", VIDU_MODELS[0]))
        ctk.CTkComboBox(card, variable=self.vidu_model_var, values=VIDU_MODELS,
                         font=FONT_MONO, fg_color=C["surface2"], border_color=C["border"],
                         button_color=C["accent"], button_hover_color=C["accent_dim"],
                         dropdown_fg_color=C["surface2"], dropdown_hover_color=C["surface3"],
                         corner_radius=8, command=lambda _: self._vidu_on_model_changed()
                         ).pack(fill="x", padx=16, pady=(0, 8))

        # 时长 & 分辨率
        param_row = ctk.CTkFrame(card, fg_color="transparent")
        param_row.pack(fill="x", padx=16, pady=(0, 8))

        # 时长
        dur_frame = ctk.CTkFrame(param_row, fg_color="transparent")
        dur_frame.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkLabel(dur_frame, text="时长 (秒)", font=FONT_SMALL,
                     text_color=C["text2"]).pack(anchor="w")
        self.vidu_duration_var = tk.StringVar(value=self.config.get("vidu_duration", "5"))
        self.vidu_duration_combo = ctk.CTkComboBox(
            dur_frame, variable=self.vidu_duration_var,
            values=self._vidu_get_duration_options(),
            font=FONT_MONO, fg_color=C["surface2"], border_color=C["border"],
            button_color=C["accent"], button_hover_color=C["accent_dim"],
            dropdown_fg_color=C["surface2"], corner_radius=8,
            command=lambda _: self._on_vidu_param_changed()
        )
        self.vidu_duration_combo.pack(fill="x", pady=(2, 0))

        # 分辨率
        res_frame = ctk.CTkFrame(param_row, fg_color="transparent")
        res_frame.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(res_frame, text="分辨率", font=FONT_SMALL,
                     text_color=C["text2"]).pack(anchor="w")
        self.vidu_resolution_var = tk.StringVar(value=self.config.get("vidu_resolution", "720p"))
        ctk.CTkComboBox(res_frame, variable=self.vidu_resolution_var,
                         values=VIDU_RESOLUTIONS,
                         font=FONT_MONO, fg_color=C["surface2"], border_color=C["border"],
                         button_color=C["accent"], button_hover_color=C["accent_dim"],
                         dropdown_fg_color=C["surface2"], corner_radius=8,
                         command=lambda _: self._on_vidu_param_changed()
                         ).pack(fill="x", pady=(2, 0))

        # 积分预估标签
        self.vidu_cost_label = ctk.CTkLabel(
            card, text="预估积分: --", font=FONT_MONO_SM, text_color=C["warn"]
        )
        self.vidu_cost_label.pack(anchor="w", padx=16, pady=(0, 8))

        # ---- 高级参数（两列） ----
        card = SectionCard(scroll, title="🎛️ 高级参数")
        card.pack(fill="x", pady=(0, 8))

        adv_row1 = ctk.CTkFrame(card, fg_color="transparent")
        adv_row1.pack(fill="x", padx=16, pady=(4, 4))

        # 风格
        sty_f = ctk.CTkFrame(adv_row1, fg_color="transparent")
        sty_f.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkLabel(sty_f, text="风格 (q1/v1)", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w")
        self.vidu_style_var = tk.StringVar(value=self.config.get("vidu_style", "general"))
        ctk.CTkComboBox(sty_f, variable=self.vidu_style_var, values=VIDU_STYLES,
                         font=FONT_MONO, fg_color=C["surface2"], border_color=C["border"],
                         button_color=C["accent"], dropdown_fg_color=C["surface2"],
                         corner_radius=8, command=lambda _: self._save_vidu_config()
                         ).pack(fill="x", pady=(2, 0))

        # 比例
        ar_f = ctk.CTkFrame(adv_row1, fg_color="transparent")
        ar_f.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(ar_f, text="画面比例", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w")
        self.vidu_aspect_var = tk.StringVar(value=self.config.get("vidu_aspect_ratio", "16:9"))
        ctk.CTkComboBox(ar_f, variable=self.vidu_aspect_var, values=VIDU_ASPECT_RATIOS,
                         font=FONT_MONO, fg_color=C["surface2"], border_color=C["border"],
                         button_color=C["accent"], dropdown_fg_color=C["surface2"],
                         corner_radius=8, command=lambda _: self._save_vidu_config()
                         ).pack(fill="x", pady=(2, 0))

        adv_row2 = ctk.CTkFrame(card, fg_color="transparent")
        adv_row2.pack(fill="x", padx=16, pady=(4, 4))

        # 运动幅度
        mv_f = ctk.CTkFrame(adv_row2, fg_color="transparent")
        mv_f.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkLabel(mv_f, text="运动幅度 (q1/v1)", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w")
        self.vidu_movement_var = tk.StringVar(value=self.config.get("vidu_movement_amplitude", "auto"))
        ctk.CTkComboBox(mv_f, variable=self.vidu_movement_var, values=VIDU_MOVEMENT_AMPLITUDES,
                         font=FONT_MONO, fg_color=C["surface2"], border_color=C["border"],
                         button_color=C["accent"], dropdown_fg_color=C["surface2"],
                         corner_radius=8, command=lambda _: self._save_vidu_config()
                         ).pack(fill="x", pady=(2, 0))

        # 随机种子
        sd_f = ctk.CTkFrame(adv_row2, fg_color="transparent")
        sd_f.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(sd_f, text="随机种子 (0=随机)", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w")
        self.vidu_seed_var = tk.StringVar(value=self.config.get("vidu_seed", "0"))
        ctk.CTkEntry(sd_f, textvariable=self.vidu_seed_var, font=FONT_MONO,
                      fg_color=C["surface2"], border_color=C["border"], corner_radius=8
                      ).pack(fill="x", pady=(2, 0))

        # 开关选项行
        toggle_row = ctk.CTkFrame(card, fg_color="transparent")
        toggle_row.pack(fill="x", padx=16, pady=(8, 4))

        self.vidu_bgm_var = tk.BooleanVar(value=self.config.get("vidu_bgm", False))
        ctk.CTkCheckBox(toggle_row, text="背景音乐 (q1/v1)", variable=self.vidu_bgm_var,
                         font=FONT_SMALL, fg_color=C["accent"], text_color=C["text2"],
                         hover_color=C["accent_dim"], corner_radius=4,
                         command=self._save_vidu_config).pack(side="left", padx=(0, 16))

        self.vidu_audio_var = tk.BooleanVar(value=self.config.get("vidu_audio", True))
        ctk.CTkCheckBox(toggle_row, text="音画同步 (q3)", variable=self.vidu_audio_var,
                         font=FONT_SMALL, fg_color=C["accent"], text_color=C["text2"],
                         hover_color=C["accent_dim"], corner_radius=4,
                         command=self._save_vidu_config).pack(side="left", padx=(0, 16))

        self.vidu_offpeak_var = tk.BooleanVar(value=self.config.get("vidu_off_peak", False))
        ctk.CTkCheckBox(toggle_row, text="错峰模式 (省积分)", variable=self.vidu_offpeak_var,
                         font=FONT_SMALL, fg_color=C["accent"], text_color=C["text2"],
                         hover_color=C["accent_dim"], corner_radius=4,
                         command=self._save_vidu_config).pack(side="left", padx=(0, 16))

        self.vidu_watermark_var = tk.BooleanVar(value=self.config.get("vidu_watermark", False))
        ctk.CTkCheckBox(toggle_row, text="添加水印", variable=self.vidu_watermark_var,
                         font=FONT_SMALL, fg_color=C["accent"], text_color=C["text2"],
                         hover_color=C["accent_dim"], corner_radius=4,
                         command=self._save_vidu_config).pack(side="left")

        # ---- 图生视频（可选参考图） ----
        card = SectionCard(scroll, title="🖼️ 图生视频 (可选)")
        card.pack(fill="x", pady=(0, 8))
        ref_row = ctk.CTkFrame(card, fg_color="transparent")
        ref_row.pack(fill="x", padx=16, pady=(4, 8))
        self.vidu_ref_path_var = tk.StringVar(value="")
        ctk.CTkEntry(ref_row, textvariable=self.vidu_ref_path_var,
                      font=FONT_MONO_SM, fg_color=C["surface2"], border_color=C["border"],
                      corner_radius=8, placeholder_text="留空则文生视频，选择图片则图生视频"
                      ).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(ref_row, text="浏览", font=FONT_SMALL, width=56,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text2"], corner_radius=6, height=32,
                       command=self._browse_vidu_ref_image).pack(side="left")


        # ========== 分镜列表面板 — 从 Script 同步 ==========
        self.vidu_shot_card = SectionCard(scroll, title="📋 Script 分镜列表 (一键导入)")
        self.vidu_shot_card.pack(fill="x", pady=(0, 8))

        shot_top_row = ctk.CTkFrame(self.vidu_shot_card, fg_color="transparent")
        shot_top_row.pack(fill="x", padx=16, pady=(4, 4))
        ctk.CTkButton(shot_top_row, text="🔄 从 Script 同步分镜", font=FONT_SMALL, width=140,
                       fg_color=C["accent"], hover_color=C["accent_dim"],
                       text_color=C["bg"], corner_radius=6, height=28,
                       command=self._vidu_sync_shots_from_script).pack(side="left")
        ctk.CTkButton(shot_top_row, text="全部复制", font=FONT_SMALL, width=80,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text2"], corner_radius=6, height=28,
                       command=self._vidu_copy_all_shots).pack(side="left", padx=6)
        self.vidu_shot_count_label = ctk.CTkLabel(shot_top_row, text="未同步",
                                                    font=FONT_SMALL, text_color=C["text3"])
        self.vidu_shot_count_label.pack(side="right")

        self.vidu_shot_list_frame = ctk.CTkScrollableFrame(
            self.vidu_shot_card, fg_color=C["surface2"],
            corner_radius=8, border_width=1, border_color=C["border"], height=200
        )
        self.vidu_shot_list_frame.pack(fill="x", padx=16, pady=(0, 8))

        self.vidu_shot_empty_label = ctk.CTkLabel(
            self.vidu_shot_list_frame,
            text="请点击「从 Script 同步分镜」加载镜头列表",
            font=FONT_SMALL, text_color=C["text3"]
        )
        self.vidu_shot_empty_label.pack(pady=16)
        self._vidu_shot_rows = []

        # ---- 提示词 ----
        card = SectionCard(scroll, title="📝 创作提示词 (最多5000字符)")
        card.pack(fill="x", pady=(0, 8))
        self.vidu_prompt_text = ctk.CTkTextbox(
            card, height=100, font=FONT_BODY, fg_color=C["surface2"],
            border_color=C["border"], border_width=1, corner_radius=8,
            text_color=C["text"], wrap="word"
        )
        self.vidu_prompt_text.pack(fill="x", padx=16, pady=(4, 8))

        # ---- 操作按钮 ----
        btn_row = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, 8))
        self.vidu_gen_btn = ctk.CTkButton(
            btn_row, text="🚀 生成视频", font=FONT_H2,
            fg_color=C["accent"], text_color=C["bg"],
            hover_color=C["accent_dim"], corner_radius=10, height=48,
            command=self.start_vidu_generate
        )
        self.vidu_gen_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        # ---- 结果展示 ----
        self.vidu_result_frame = SectionCard(scroll, title="📺 输出结果")
        self.vidu_result_frame.pack(fill="x", pady=(0, 8))
        self.vidu_result_label = ctk.CTkLabel(
            self.vidu_result_frame, text="等待生成...",
            font=FONT_SMALL, text_color=C["text3"], wraplength=500
        )
        self.vidu_result_label.pack(anchor="w", padx=16, pady=(4, 4))
        self.vidu_download_btn = ctk.CTkButton(
            self.vidu_result_frame, text="📂 打开输出目录", font=FONT_SMALL,
            fg_color=C["surface2"], hover_color=C["border"],
            text_color=C["text2"], corner_radius=6, height=28,
            command=lambda: self._open_output_dir("output_video")
        )
        self.vidu_download_btn.pack(anchor="w", padx=16, pady=(0, 8))

        # 初始化积分预估
        self._on_vidu_param_changed()


    # ---------- Vidu 分镜同步方法 ----------

    def _vidu_sync_shots_from_script(self):
        """从 Script 页面读取脚本，解析分镜，展示到 Vidu 分镜列表"""
        content = self.script_output.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo("提示", "Script 页面中没有脚本内容，请先在「剧本生成」页面生成镜头脚本。")
            return
        shots = self._parse_script_shots(content)
        if not shots:
            prompts = self._extract_prompts_loose(content)
            if not prompts:
                messagebox.showinfo("提示", "未从脚本中找到英文 Prompt，请检查脚本格式。")
                return
            shots = [{"num": i + 1, "label": f"镜头 {i+1}", "prompt": p, "duration": self._estimate_duration(p)}
                     for i, p in enumerate(prompts)]
        # 清空旧列表
        for row in self._vidu_shot_rows:
            row["frame"].destroy()
        self._vidu_shot_rows = []
        self.vidu_shot_empty_label.pack_forget()
        for shot in shots:
            self._vidu_add_shot_row(shot)
        self.vidu_shot_count_label.configure(text=f"已同步 {len(shots)} 个镜头", text_color=C["green"])
        self._vidu_log_msg(f"已从 Script 同步 {len(shots)} 个分镜")

    def _vidu_add_shot_row(self, shot):
        """在 Vidu 分镜列表中添加一行"""
        row_frame = ctk.CTkFrame(self.vidu_shot_list_frame, fg_color="transparent")
        row_frame.pack(fill="x", pady=2)
        num_label = ctk.CTkLabel(row_frame, text=f"#{shot['num']}", font=FONT_SMALL,
                                  text_color=C["accent"], width=30)
        num_label.pack(side="left")
        prompt_text = ctk.CTkTextbox(row_frame, height=40, font=FONT_MONO_SM,
                                      fg_color=C["surface"], text_color=C["text"],
                                      corner_radius=4, border_width=1, border_color=C["border"])
        prompt_text.pack(side="left", padx=4, fill="x", expand=True)
        prompt_text.insert("1.0", shot["prompt"])
        prompt_text.configure(state="disabled")
        btn_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        btn_frame.pack(side="left", padx=2)
        def _copy_prompt(p=shot["prompt"]):
            self.root.clipboard_clear()
            self.root.clipboard_append(p)
            self._vidu_log_msg(f"已复制镜头 {shot['num']} 的 Prompt")
        ctk.CTkButton(btn_frame, text="📋", font=FONT_SMALL, width=28,
                       fg_color=C["accent"], hover_color=C["accent_dim"],
                       text_color=C["bg"], corner_radius=4, height=26,
                       command=_copy_prompt).pack(side="left", padx=1)
        def _send_to_vidu(p=shot["prompt"]):
            self.vidu_prompt_text.delete("1.0", "end")
            self.vidu_prompt_text.insert("1.0", p)
            self._vidu_log_msg(f"镜头 {shot['num']} 的 Prompt 已填入提示词框")
        ctk.CTkButton(btn_frame, text="▶", font=FONT_SMALL, width=28,
                       fg_color=C["blue"], hover_color="#3AA5E0",
                       text_color="#FFF", corner_radius=4, height=26,
                       command=_send_to_vidu).pack(side="left", padx=1)
        dur_label = ctk.CTkLabel(row_frame, text=f"{shot.get('duration', 5)}s",
                                   font=FONT_MONO_SM, text_color=C["warn"], width=30)
        dur_label.pack(side="left", padx=2)
        self._vidu_shot_rows.append({
            "frame": row_frame, "num_label": num_label,
            "prompt_text": prompt_text, "dur_label": dur_label,
            "prompt": shot["prompt"],
        })

    def _vidu_copy_all_shots(self):
        """复制所有分镜的提示词"""
        if not self._vidu_shot_rows:
            messagebox.showinfo("提示", "请先同步分镜列表")
            return
        all_prompts = [row["prompt"] for row in self._vidu_shot_rows]
        combined = "\n\n".join(all_prompts)
        self.root.clipboard_clear()
        self.root.clipboard_append(combined)
        self._vidu_log_msg(f"已复制全部 {len(all_prompts)} 条 Prompt 到剪贴板")

    # ---------- Vidu 工具方法 ----------

    def _toggle_vidu_key_vis(self):
        self.vidu_key_visible.set(not self.vidu_key_visible.get())
        self.vidu_key_entry.configure(show="" if self.vidu_key_visible.get() else "•")

    def _vidu_get_duration_options(self):
        """根据当前模型返回可用时长列表"""
        model = self.vidu_model_var.get() if hasattr(self, 'vidu_model_var') else VIDU_MODELS[0]
        dur_range = VIDU_MODEL_DURATION.get(model, (1, 16))
        return [str(d) for d in range(dur_range[0], dur_range[1] + 1)]

    def _vidu_on_model_changed(self):
        """模型切换时更新时长选项和积分预估"""
        options = self._vidu_get_duration_options()
        self.vidu_duration_combo.configure(values=options)
        # 如果当前时长不在范围内，重置
        if self.vidu_duration_var.get() not in options:
            self.vidu_duration_var.set(options[len(options) // 2] if len(options) > 1 else options[0])
        self._on_vidu_param_changed()
        self._save_vidu_config()

    def _on_vidu_param_changed(self):
        """参数变化时更新积分预估"""
        try:
            resolution = self.vidu_resolution_var.get()
            duration = int(self.vidu_duration_var.get())
            rate = VIDU_CREDIT_RATES.get(resolution, 20)
            cost = rate * duration
            self.vidu_cost_label.configure(
                text=f"预估积分: {cost} ({resolution} × {duration}s = {rate}/秒 × {duration})",
                text_color=C["warn"]
            )
        except (ValueError, AttributeError):
            pass
        self._save_vidu_config()

    def _vidu_calculate_cost(self):
        """计算所需积分"""
        resolution = self.vidu_resolution_var.get()
        duration = int(self.vidu_duration_var.get())
        rate = VIDU_CREDIT_RATES.get(resolution, 20)
        return rate * duration

    def _save_vidu_config(self):
        self.config["vidu_api_key"] = self.vidu_key_var.get().strip()
        self.config["vidu_model"] = self.vidu_model_var.get()
        self.config["vidu_duration"] = self.vidu_duration_var.get()
        self.config["vidu_resolution"] = self.vidu_resolution_var.get()
        self.config["vidu_style"] = self.vidu_style_var.get()
        self.config["vidu_aspect_ratio"] = self.vidu_aspect_var.get()
        self.config["vidu_seed"] = self.vidu_seed_var.get()
        self.config["vidu_movement_amplitude"] = self.vidu_movement_var.get()
        self.config["vidu_bgm"] = self.vidu_bgm_var.get()
        self.config["vidu_audio"] = self.vidu_audio_var.get()
        self.config["vidu_off_peak"] = self.vidu_offpeak_var.get()
        self.config["vidu_watermark"] = self.vidu_watermark_var.get()
        save_config(self.config)

    def _vidu_log_msg(self, msg):
        ts = time.strftime("%H:%M:%S")
        self.safe_after( lambda: self.global_log.append(f"[{ts}] [Vidu] {msg}"))

    def _browse_vidu_ref_image(self):
        path = filedialog.askopenfilename(
            title="选择参考图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.webp")]
        )
        if path:
            self.vidu_ref_path_var.set(path)

    def _open_output_dir(self, sub_dir):
        out_dir = self._get_output_dir(sub_dir)
        os.makedirs(out_dir, exist_ok=True)
        os.startfile(out_dir)

    # ---------- Vidu API 方法 ----------

    def _vidu_validate_key(self):
        api_key = self.vidu_key_var.get().strip()
        if not api_key:
            messagebox.showwarning("提示", "请先输入 API Key")
            return
        self._save_vidu_config()
        self._vidu_log_msg("正在验证 API Key...")

        def _worker():
            try:
                headers = {"Authorization": f"Token {api_key}"}
                resp = requests.get(f"{VIDU_BASE_URL}/ent/v2/credits?show_detail=true",
                                    headers=headers, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    remains = data.get("remains", [])
                    if remains:
                        credit = remains[0].get("credit_remain", 0)
                        self._vidu_log_msg(f"✅ API Key 有效！剩余积分: {credit}")
                        self.safe_after( lambda: self.vidu_credits_label.configure(
                            text=f"积分: {credit}", text_color=C["green"]))
                        self.safe_after( lambda: messagebox.showinfo(
                            "验证成功", f"API Key 有效！\n剩余积分: {credit}"))
                    else:
                        self._vidu_log_msg("✅ API Key 有效，但无积分数据")
                        self.safe_after( lambda: messagebox.showinfo("验证成功", "API Key 有效"))
                elif resp.status_code == 401:
                    self._vidu_log_msg("❌ API Key 无效 (401)")
                    self.safe_after( lambda: messagebox.showerror("验证失败", "API Key 无效，请检查"))
                else:
                    self._vidu_log_msg(f"❌ 验证失败: HTTP {resp.status_code}")
                    self.safe_after( lambda: messagebox.showerror(
                        "验证失败", f"HTTP {resp.status_code}: {resp.text[:200]}"))
            except Exception as e:
                self._vidu_log_msg(f"❌ 验证异常: {e}")
                self.safe_after( lambda: messagebox.showerror("验证异常", str(e)))

        threading.Thread(target=_worker, daemon=True).start()

    def _vidu_query_credits(self):
        api_key = self.vidu_key_var.get().strip()
        if not api_key:
            messagebox.showwarning("提示", "请先输入 API Key")
            return
        self._vidu_log_msg("正在查询积分...")

        def _worker():
            try:
                headers = {"Authorization": f"Token {api_key}"}
                resp = requests.get(f"{VIDU_BASE_URL}/ent/v2/credits?show_detail=true",
                                    headers=headers, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    remains = data.get("remains", [])
                    packages = data.get("packages", [])
                    credit = 0
                    if remains:
                        r = remains[0]
                        credit = r.get("credit_remain", 0)
                        concur_lim = r.get("concurrency_limit", 0)
                        concur_now = r.get("current_concurrency", 0)
                        queue = data.get("queue_count", 0)
                        self._vidu_log_msg(
                            f"📊 积分: {credit} | 并发: {concur_now}/{concur_lim} | 排队: {queue}")
                        self.safe_after( lambda: self.vidu_credits_label.configure(
                            text=f"积分: {credit} | 并发: {concur_now}/{concur_lim}",
                            text_color=C["green"]))
                    pkg_info = ""
                    if packages:
                        for p in packages:
                            name = p.get('name', '?')
                            remain = p.get('credit_remain', 0)
                            total = p.get('credit_amount', 0)
                            pkg_info += f"\n  📦 {name}: {remain}/{total} 积分"
                            self._vidu_log_msg(f"  📦 {name}: {remain}/{total} 积分")
                    self.safe_after(lambda: messagebox.showinfo(
                        "积分查询", f"剩余积分: {credit}{pkg_info}"))
                elif resp.status_code == 401:
                    self._vidu_log_msg("❌ API Key 无效 (401)")
                    self.safe_after(lambda: messagebox.showerror("查询失败", "API Key 无效，请检查"))
                else:
                    self._vidu_log_msg(f"❌ 查询失败: HTTP {resp.status_code}")
                    self.safe_after(lambda: messagebox.showerror(
                        "查询失败", f"HTTP {resp.status_code}: {resp.text[:200]}"))
            except Exception as e:
                self._vidu_log_msg(f"❌ 查询异常: {e}")
                self.safe_after(lambda: messagebox.showerror("查询异常", str(e)))

        threading.Thread(target=_worker, daemon=True).start()

    def start_vidu_generate(self):
        api_key = self.vidu_key_var.get().strip()
        if not api_key:
            messagebox.showwarning("提示", "请先输入 Vidu API Key")
            return
        prompt = self.vidu_prompt_text.get("1.0", "end").strip()
        ref_path = self.vidu_ref_path_var.get().strip()
        if not prompt and not ref_path:
            messagebox.showwarning("提示", "请输入提示词或选择参考图片")
            return
        if len(prompt) > 5000:
            messagebox.showwarning("提示", f"提示词超过5000字符限制（当前 {len(prompt)} 字符）")
            return

        # ---- 积分核算弹窗确认 ----
        cost = self._vidu_calculate_cost()
        resolution = self.vidu_resolution_var.get()
        duration = self.vidu_duration_var.get()
        rate = VIDU_CREDIT_RATES.get(resolution, 20)
        model = self.vidu_model_var.get()

        confirm_msg = (
            f"📋 积分消耗核算\n"
            f"{'─' * 32}\n"
            f"模型: {model}\n"
            f"分辨率: {resolution}\n"
            f"时长: {duration} 秒\n"
            f"单价: {rate} 积分/秒\n"
            f"{'─' * 32}\n"
            f"💰 预估消耗: {cost} 积分\n"
            f"{'─' * 32}\n\n"
            f"确认生成？"
        )
        if not messagebox.askyesno("积分核算确认", confirm_msg):
            self._vidu_log_msg("用户取消生成")
            return

        self._save_vidu_config()
        self.vidu_gen_btn.configure(state="disabled", text="⏳ 生成中...")
        self.safe_after( lambda: self.vidu_result_label.configure(
            text="正在生成，请查看终端日志...", text_color=C["accent2"]))

        threading.Thread(
            target=self._vidu_generate_worker,
            args=(api_key, model, prompt, ref_path, int(duration), resolution),
            daemon=True
        ).start()

    def _vidu_generate_worker(self, api_key, model, prompt, ref_path, duration, resolution):
        try:
            headers = {"Authorization": f"Token {api_key}", "Content-Type": "application/json"}

            # Step 1: 查询积分
            self._vidu_log_msg("🔍 查询积分...")
            try:
                cr = requests.get(f"{VIDU_BASE_URL}/ent/v2/credits?show_detail=true",
                                  headers=headers, timeout=15)
                if cr.status_code == 200:
                    remains = cr.json().get("remains", [])
                    if remains:
                        credit = remains[0].get("credit_remain", 0)
                        self._vidu_log_msg(f"📊 剩余积分: {credit}")
                        cost = self._vidu_calculate_cost()
                        if credit < cost:
                            self._vidu_log_msg(f"⚠️ 积分不足！需要 {cost}，仅有 {credit}")
            except Exception:
                self._vidu_log_msg("⚠️ 积分查询跳过")

            # Step 2: 构建请求体
            payload = {"model": model}

            # 必填：prompt（文生视频）或 images（图生视频）
            is_i2v = bool(ref_path and os.path.exists(ref_path))
            if prompt:
                payload["prompt"] = prompt

            # 可选参数
            payload["duration"] = duration
            payload["resolution"] = resolution
            payload["style"] = self.vidu_style_var.get()
            payload["aspect_ratio"] = self.vidu_aspect_var.get()

            seed_val = self.vidu_seed_var.get().strip()
            if seed_val and seed_val != "0":
                try:
                    payload["seed"] = int(seed_val)
                except ValueError:
                    pass

            movement = self.vidu_movement_var.get()
            if movement != "auto":
                payload["movement_amplitude"] = movement

            if self.vidu_bgm_var.get():
                payload["bgm"] = True

            # q3 系列的 audio 参数
            if "q3" in model:
                payload["audio"] = self.vidu_audio_var.get()

            if self.vidu_offpeak_var.get():
                payload["off_peak"] = True

            if self.vidu_watermark_var.get():
                payload["watermark"] = True

            # Step 3: 提交生成任务
            if is_i2v:
                endpoint = f"{VIDU_BASE_URL}/ent/v2/image-to-video"
                self._vidu_log_msg(f"📤 图生视频模式 | 模型: {model}")
                with open(ref_path, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode()
                ext = os.path.splitext(ref_path)[1].lower().lstrip(".")
                mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                        "webp": "image/webp"}.get(ext, "image/png")
                payload["images"] = [f"data:{mime};base64,{img_b64}"]
            else:
                endpoint = f"{VIDU_BASE_URL}/ent/v2/text-to-video"
                self._vidu_log_msg(f"📝 文生视频模式 | 模型: {model}")

            self._vidu_log_msg(f"🚀 提交生成任务 | {resolution} | {duration}s | 预估 {VIDU_CREDIT_RATES.get(resolution, 20) * duration} 积分")
            resp = requests.post(endpoint, headers=headers, json=payload, timeout=60)

            if resp.status_code not in (200, 201):
                self._vidu_log_msg(f"❌ 提交失败: HTTP {resp.status_code} - {resp.text[:300]}")
                self.safe_after( lambda: messagebox.showerror(
                    "提交失败", f"HTTP {resp.status_code}\n{resp.text[:300]}"))
                return

            task_id = resp.json().get("id", "")
            if not task_id:
                self._vidu_log_msg(f"❌ 未获取到任务 ID: {resp.text[:200]}")
                return
            self._vidu_log_msg(f"✅ 任务已提交 | ID: {task_id}")

            # Step 4: 轮询状态
            self._vidu_log_msg("⏱️ 开始轮询 (5秒间隔，10分钟超时)...")
            elapsed = 0
            max_wait = 600
            while elapsed < max_wait:
                _time.sleep(5)
                elapsed += 5
                try:
                    pr = requests.get(f"{VIDU_BASE_URL}/ent/v2/tasks/{task_id}",
                                      headers=headers, timeout=30)
                    if pr.status_code != 200:
                        self._vidu_log_msg(f"⚠️ 轮询异常: HTTP {pr.status_code}")
                        continue
                    result = pr.json()
                    status = result.get("status", "")
                    if status == "processing":
                        self._vidu_log_msg(f"⏳ 渲染中... ({elapsed}s)")
                        continue
                    elif status == "success":
                        video_url = result.get("video_url", "") or result.get("videos", [{}])[0].get("url", "")
                        self._vidu_log_msg(f"🎉 生成成功！ ({elapsed}s)")
                        if video_url:
                            self._vidu_log_msg(f"🔗 视频: {video_url}")
                            self._vidu_download_video(video_url)
                        self.safe_after( lambda: self.vidu_result_label.configure(
                            text=f"✅ 完成！视频已保存到 output_video/", text_color=C["green"]))
                        return
                    elif status == "failed":
                        err = result.get("error_msg", result.get("message", "未知错误"))
                        self._vidu_log_msg(f"❌ 生成失败: {err}")
                        self.safe_after( lambda: self.vidu_result_label.configure(
                            text=f"❌ 失败: {err}", text_color=C["red"]))
                        return
                    else:
                        self._vidu_log_msg(f"[{elapsed}s] 状态: {status}")
                except Exception as e:
                    self._vidu_log_msg(f"⚠️ 轮询异常: {e}")

            self._vidu_log_msg(f"⏰ 超时 ({max_wait}s)，任务可能仍在处理")
            self.safe_after( lambda: self.vidu_result_label.configure(
                text="⏰ 轮询超时，请稍后手动查询", text_color=C["warn"]))

        except Exception as e:
            self._vidu_log_msg(f"💥 异常: {e}")
        finally:
            self.safe_after( lambda: self.vidu_gen_btn.configure(
                state="normal", text="🚀 生成视频"))

    def _vidu_download_video(self, url):
        self._vidu_log_msg("📥 下载视频中...")
        try:
            out_dir = self._get_output_dir("output_video")
            os.makedirs(out_dir, exist_ok=True)
            filename = f"vidu_{time.strftime('%Y%m%d_%H%M%S')}.mp4"
            filepath = os.path.join(out_dir, filename)
            resp = requests.get(url, stream=True, timeout=120)
            resp.raise_for_status()
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            self._vidu_log_msg(f"✅ 已保存: {filepath}")
            self.safe_after( lambda: self.vidu_result_label.configure(
                text=f"✅ 已保存: {filename}", text_color=C["green"]))
        except Exception as e:
            self._vidu_log_msg(f"❌ 下载失败: {e}")

    # ---------- Voice 页面 ----------

    def _build_page_voice(self, parent):
        # 垂直流布局 — 全宽滚动
        scroll = ctk.CTkScrollableFrame(
            parent, fg_color=C["bg"],
            scrollbar_button_color=C["border"],
            scrollbar_button_hover_color=C["text3"]
        )
        scroll.pack(fill="both", expand=True, padx=PAD_MD, pady=PAD_MD)

        ctk.CTkLabel(scroll, text="AI 智能配音", font=FONT_TITLE,
                     text_color=C["accent"]).pack(anchor="w", pady=(0, PAD_LG))

        # 引擎选择
        self._tts_engine_card = SectionCard(scroll, title="TTS 引擎")
        self._tts_engine_card.pack(fill="x", pady=(0, 8))
        self.tts_engine_var = tk.StringVar(value=self.config.get("tts_engine", "bailian"))
        self.tts_engine_bailian_rb = ctk.CTkRadioButton(
            self._tts_engine_card, text="阿里云 DashScope TTS (云端商业)", variable=self.tts_engine_var, value="bailian",
            font=FONT_BODY, fg_color=C["accent"], text_color=C["text"],
            hover_color=C["accent2"], command=self._on_tts_engine_change)
        self.tts_engine_bailian_rb.pack(anchor="w", padx=16, pady=4)
        self.tts_engine_sovits_rb = ctk.CTkRadioButton(
            self._tts_engine_card, text="GPT-SoVITS (本地免费)", variable=self.tts_engine_var, value="sovits",
            font=FONT_BODY, fg_color=C["accent"], text_color=C["text"],
            hover_color=C["accent2"], command=self._on_tts_engine_change)
        self.tts_engine_sovits_rb.pack(anchor="w", padx=16, pady=4)
        self.tts_engine_mimo_rb = ctk.CTkRadioButton(
            self._tts_engine_card, text="小米 MiMo (百亿额度)", variable=self.tts_engine_var, value="mimo",
            font=FONT_BODY, fg_color=C["accent"], text_color=C["text"],
            hover_color=C["accent2"], command=self._on_tts_engine_change)
        self.tts_engine_mimo_rb.pack(anchor="w", padx=16, pady=(0, 10))

        # 百炼 TTS
        self.bailian_tts_frame = SectionCard(scroll, title="阿里云 DashScope TTS 配置")
        self.bailian_tts_frame.pack(fill="x", pady=(0, 8))

        self.tts_voice_map = {
            "longcheng (长城-沉稳悬疑男声)": "longcheng",
            "longxia (龙霞-沉稳女声)": "longxia",
            "longshuo (龙硕-阳光男声)": "longshuo",
            "longwan (龙婉-温柔女声)": "longwan",
        }
        saved_voice = self.config.get("tts_voice", "longcheng")
        voice_display = [k for k, v in self.tts_voice_map.items() if v == saved_voice]
        voice_default = voice_display[0] if voice_display else list(self.tts_voice_map.keys())[0]

        ctk.CTkLabel(self.bailian_tts_frame, text="预设音色:", font=FONT_SMALL,
                     text_color=C["text2"]).pack(anchor="w", padx=16, pady=(8, 0))
        self.tts_voice_var = tk.StringVar(value=voice_default)
        ctk.CTkComboBox(self.bailian_tts_frame, variable=self.tts_voice_var,
                         values=list(self.tts_voice_map.keys()), font=FONT_BODY,
                         dropdown_font=FONT_BODY, fg_color=C["surface2"],
                         border_color=C["border"], button_color=C["border"],
                         button_hover_color=C["text3"], corner_radius=8
                         ).pack(fill="x", padx=16, pady=(2, 8))

        ctk.CTkLabel(self.bailian_tts_frame, text="自定义模型 ID (可选):", font=FONT_SMALL,
                     text_color=C["text2"]).pack(anchor="w", padx=16)
        self.tts_custom_model_var = tk.StringVar(value=self.config.get("tts_custom_model", ""))
        ctk.CTkEntry(self.bailian_tts_frame, textvariable=self.tts_custom_model_var,
                      font=FONT_MONO, fg_color=C["surface2"], border_color=C["border"],
                      corner_radius=8).pack(fill="x", padx=16, pady=(2, 12))

        # VibeVoice
        self.sovits_frame = SectionCard(scroll, title="GPT-SoVITS (本地免费) 配置")

        ctk.CTkLabel(self.sovits_frame, text="VibeVoice API 地址:", font=FONT_SMALL,
                     text_color=C["text2"]).pack(anchor="w", padx=16, pady=(8, 0))
        self.sovits_url_var = tk.StringVar(value=self.config.get("sovits_url", "http://127.0.0.1:8080"))
        ctk.CTkEntry(self.sovits_frame, textvariable=self.sovits_url_var, font=FONT_MONO,
                      fg_color=C["surface2"], border_color=C["border"],
                      corner_radius=8).pack(fill="x", padx=16, pady=(2, 8))

        ctk.CTkLabel(self.sovits_frame, text="一键启动脚本 (.bat):", font=FONT_SMALL,
                     text_color=C["text2"]).pack(anchor="w", padx=16)
        bat_row = ctk.CTkFrame(self.sovits_frame, fg_color="transparent")
        bat_row.pack(fill="x", padx=16, pady=(2, 8))
        self.sovits_bat_var = tk.StringVar(value=self.config.get("sovits_bat_path", r"D:\剪映\声音克隆\一键启动.bat"))
        ctk.CTkEntry(bat_row, textvariable=self.sovits_bat_var, font=FONT_MONO_SM,
                      fg_color=C["surface2"], border_color=C["border"],
                      corner_radius=8).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(bat_row, text="浏览", width=60, font=FONT_SMALL,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text"], corner_radius=6, height=30,
                       command=self._browse_sovits_bat).pack(side="left", padx=(6, 0))

        # 角色 (Combobox) + 情绪
        ctk.CTkLabel(self.sovits_frame, text="角色名称:", font=FONT_SMALL,
                     text_color=C["text2"]).pack(anchor="w", padx=16, pady=(4, 0))
        char_row = ctk.CTkFrame(self.sovits_frame, fg_color="transparent")
        char_row.pack(fill="x", padx=16, pady=(2, 8))
        self.sovits_character_var = tk.StringVar(value=self.config.get("sovits_character", ""))
        self.sovits_character_combo = ctk.CTkComboBox(
            char_row, variable=self.sovits_character_var, values=[""],
            font=FONT_BODY, dropdown_font=FONT_BODY,
            fg_color=C["surface2"], border_color=C["border"],
            button_color=C["border"], button_hover_color=C["text3"],
            corner_radius=8, state="readonly")
        self.sovits_character_combo.pack(side="left", fill="x", expand=True)
        self.sovits_refresh_btn = ctk.CTkButton(
            char_row, text="刷新列表", width=80, font=FONT_SMALL,
            fg_color=C["accent"], text_color=C["bg"], hover_color=C["accent2"],
            corner_radius=6, height=30, command=self._refresh_vibevoice_characters)
        self.sovits_refresh_btn.pack(side="left", padx=(6, 0))

        ctk.CTkLabel(self.sovits_frame, text="情绪基调:", font=FONT_SMALL,
                     text_color=C["text2"]).pack(anchor="w", padx=16)
        self.sovits_emotion_var = tk.StringVar(value=self.config.get("sovits_emotion", "平静"))
        self.sovits_emotion_combo = ctk.CTkComboBox(
            self.sovits_frame, variable=self.sovits_emotion_var, values=["平静"],
            font=FONT_BODY, dropdown_font=FONT_BODY,
            fg_color=C["surface2"], border_color=C["border"],
            button_color=C["border"], button_hover_color=C["text3"],
            corner_radius=8)
        self.sovits_emotion_combo.pack(fill="x", padx=16, pady=(2, 12))

        # 小米 MiMo TTS
        self.mimo_tts_frame = SectionCard(scroll, title="小米 MiMo TTS 配置")

        ctk.CTkLabel(self.mimo_tts_frame, text="API Key:", font=FONT_SMALL,
                     text_color=C["text2"]).pack(anchor="w", padx=16, pady=(8, 0))
        self.mimo_api_key_var = tk.StringVar(value=self.config.get("mimo_api_key", ""))
        self.mimo_key_entry = ctk.CTkEntry(self.mimo_tts_frame, textvariable=self.mimo_api_key_var,
                                           show="*", font=FONT_MONO,
                                           fg_color=C["surface2"], border_color=C["border"],
                                           corner_radius=8)
        self.mimo_key_entry.pack(fill="x", padx=16, pady=(2, 8))
        mimo_key_row = ctk.CTkFrame(self.mimo_tts_frame, fg_color="transparent")
        mimo_key_row.pack(fill="x", padx=16, pady=(0, 8))
        self.mimo_key_visible = tk.BooleanVar(value=False)
        ctk.CTkButton(mimo_key_row, text="显示/隐藏", width=100, font=FONT_SMALL,
                      fg_color=C["surface2"], hover_color=C["border"],
                      text_color=C["text"], corner_radius=6, height=28,
                      command=self._toggle_mimo_key_vis).pack(side="left")
        ctk.CTkLabel(mimo_key_row, text="填入 MiMo API Key",
                     font=FONT_SMALL, text_color=C["text3"]).pack(side="left", padx=8)

        ctk.CTkLabel(self.mimo_tts_frame, text="模型选择:", font=FONT_SMALL,
                     text_color=C["text2"]).pack(anchor="w", padx=16)
        self.mimo_model_var = tk.StringVar(value=self.config.get("mimo_model", "MiMo-V2.5-TTS"))
        mimo_models = [
            "MiMo-V2.5-TTS (标准)",
            "MiMo-V2.5-TTS-VoiceClone (声音复刻)",
            "MiMo-V2.5-TTS-VoiceDesign (声音设计)",
        ]
        ctk.CTkComboBox(self.mimo_tts_frame, variable=self.mimo_model_var,
                        values=mimo_models, font=FONT_BODY,
                        dropdown_font=FONT_BODY, fg_color=C["surface2"],
                        border_color=C["border"], button_color=C["border"],
                        button_hover_color=C["text3"], corner_radius=8
                        ).pack(fill="x", padx=16, pady=(2, 8))

        # 预设音色下拉框
        ctk.CTkLabel(self.mimo_tts_frame, text="预设音色:", font=FONT_SMALL,
                     text_color=C["text2"]).pack(anchor="w", padx=16)
        self.mimo_voice_var = tk.StringVar(value=self.config.get("mimo_voice", "冰糖"))
        mimo_voices = [
            "冰糖 (清甜女声)",
            "茉莉 (温柔女声)",
            "苏打 (活力女声)",
            "白桦 (沉稳女声)",
            "Mia (英文女声)",
            "Chloe (英文女声)",
            "Milo (英文男声)",
            "Dean (英文男声)",
            "mimo_default (默认)",
        ]
        # 音色显示名到API ID的映射（修复音色生成错误的关键）
        self.mimo_voice_id_map = {
            "冰糖 (清甜女声)": "bingtang",
            "茉莉 (温柔女声)": "mohuali",
            "苏打 (活力女声)": "sudahuoli",
            "白桦 (沉稳女声)": "baihuashenzhu",
            "Mia (英文女声)": "mia",
            "Chloe (英文女声)": "chloe",
            "Milo (英文男声)": "milo",
            "Dean (英文男声)": "dean",
            "mimo_default (默认)": "mimo_default",
        }
        self.mimo_voice_combo = ctk.CTkComboBox(
            self.mimo_tts_frame, variable=self.mimo_voice_var,
            values=mimo_voices, font=FONT_BODY,
            dropdown_font=FONT_BODY, fg_color=C["surface2"],
            border_color=C["border"], button_color=C["border"],
            button_hover_color=C["text3"], corner_radius=8)
        self.mimo_voice_combo.pack(fill="x", padx=16, pady=(2, 12))

        self._on_tts_engine_change()

        # ============ 显眼的模式切换按钮 ============
        self.tts_adv_mode_var = tk.StringVar(value=self.config.get("tts_adv_mode", "preset"))
        mode_switch_frame = ctk.CTkFrame(scroll, fg_color=C["surface"],
                                          corner_radius=12, border_width=1, border_color=C["border"])
        mode_switch_frame.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(mode_switch_frame, text="配音模式", font=FONT_H2,
                     text_color=C["accent"]).pack(anchor="w", padx=16, pady=(12, 8))

        self._mode_btn_row = ctk.CTkFrame(mode_switch_frame, fg_color="transparent")
        self._mode_btn_row.pack(fill="x", padx=16, pady=(0, 12))

        self._btn_preset = ctk.CTkButton(
            self._mode_btn_row, text="预设音色", font=FONT_H2,
            fg_color=C["accent"], text_color=C["bg"], hover_color=C["accent2"],
            corner_radius=10, height=44,
            command=lambda: self._switch_mode("preset"))
        self._btn_preset.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self._btn_clone = ctk.CTkButton(
            self._mode_btn_row, text="声音复刻", font=FONT_H2,
            fg_color=C["surface2"], text_color=C["text"], hover_color=C["border"],
            corner_radius=10, height=44,
            command=lambda: self._switch_mode("clone"))
        self._btn_clone.pack(side="left", fill="x", expand=True, padx=(4, 0))

        self._mode_hint = ctk.CTkLabel(mode_switch_frame, text="当前：预设音色 + 情感指令驱动",
                                        font=FONT_SMALL, text_color=C["text3"])
        self._mode_hint.pack(anchor="w", padx=16, pady=(0, 12))

        # 共享高级配置：参考音频 + 情感指令
        self._tts_advanced_card = SectionCard(scroll, title="高级控制")
        self._tts_advanced_card.pack(fill="x", pady=(0, 8))

        # --- 情感指令 (模式A) ---
        self.tts_prompt_label = ctk.CTkLabel(self._tts_advanced_card, text="情感/语气指令:",
                                              font=FONT_SMALL, text_color=C["text2"])
        self.tts_prompt_label.pack(anchor="w", padx=16, pady=(4, 0))

        # 情感模板下拉框
        ctk.CTkLabel(self._tts_advanced_card, text="快速模板:", font=FONT_SMALL,
                     text_color=C["text3"]).pack(anchor="w", padx=16, pady=(2, 0))
        self.tts_emotion_template_var = tk.StringVar(value="自定义")
        self._emotion_templates = {
            "自定义": "",
            "悬疑低沉": "故作神秘，压低声音，语速缓慢，带有紧张感",
            "活泼欢快": "声音明亮，语速偏快，充满活力和喜悦",
            "悲伤低落": "声音低沉，语速缓慢，带有哽咽和伤感",
            "愤怒大吼": "声音洪亮，语气强烈，充满愤怒和压迫感",
            "温柔轻语": "声音轻柔，语速缓慢，温柔体贴",
            "严肃庄重": "声音沉稳，语气正式，充满权威感",
            "俏皮可爱": "声音活泼，语调上扬，带有调皮和可爱感",
        }
        self.tts_emotion_template_combo = ctk.CTkComboBox(
            self._tts_advanced_card, variable=self.tts_emotion_template_var,
            values=list(self._emotion_templates.keys()), font=FONT_BODY,
            dropdown_font=FONT_BODY, fg_color=C["surface2"],
            border_color=C["border"], button_color=C["border"],
            button_hover_color=C["text3"], corner_radius=8,
            command=self._on_emotion_template_change)
        self.tts_emotion_template_combo.pack(fill="x", padx=16, pady=(2, 4))

        self.tts_prompt_text_var = tk.StringVar(value=self.config.get("tts_prompt_text", ""))
        self.tts_prompt_entry = ctk.CTkEntry(self._tts_advanced_card, textvariable=self.tts_prompt_text_var,
                                              font=FONT_BODY,
                                              placeholder_text="如：用悲伤且颤抖的声音缓缓道来",
                                              fg_color=C["surface2"], border_color=C["border"],
                                              corner_radius=8)
        self.tts_prompt_entry.pack(fill="x", padx=16, pady=(2, 8))

        # --- 参考音频 (模式B) ---
        self.tts_ref_label = ctk.CTkLabel(self._tts_advanced_card, text="参考音频 (用于声音复刻):",
                                           font=FONT_SMALL, text_color=C["text2"])
        self.tts_ref_label.pack(anchor="w", padx=16)
        ref_row = ctk.CTkFrame(self._tts_advanced_card, fg_color="transparent")
        ref_row.pack(fill="x", padx=16, pady=(2, 12))
        self.tts_ref_audio_var = tk.StringVar(value=self.config.get("tts_ref_audio", ""))
        self.tts_ref_entry = ctk.CTkEntry(ref_row, textvariable=self.tts_ref_audio_var, font=FONT_MONO_SM,
                                           placeholder_text="选择 .wav 参考音频文件",
                                           fg_color=C["surface2"], border_color=C["border"],
                                           corner_radius=8)
        self.tts_ref_entry.pack(side="left", fill="x", expand=True)
        self.tts_ref_btn = ctk.CTkButton(ref_row, text="浏览", width=60, font=FONT_SMALL,
                                          fg_color=C["surface2"], hover_color=C["border"],
                                          text_color=C["text"], corner_radius=6, height=30,
                                          command=self._browse_tts_ref_audio)
        self.tts_ref_btn.pack(side="left", padx=(6, 0))

        # 根据配置初始化按钮样式（必须在所有组件创建之后）
        self._switch_mode(self.config.get("tts_adv_mode", "preset"))

        # 台词输入
        card = SectionCard(scroll, title="台词 / 旁白")
        card.pack(fill="both", expand=True, pady=(0, 8))

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(4, 4))
        ctk.CTkButton(btn_row, text="从 Script 提取", font=FONT_SMALL, width=100,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["blue"], corner_radius=6, height=28,
                       command=self._extract_dialogue).pack(side="left")
        ctk.CTkButton(btn_row, text="清空", font=FONT_SMALL, width=50,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text2"], corner_radius=6, height=28,
                       command=lambda: self.tts_text.delete("1.0", "end")
                       ).pack(side="left", padx=6)

        self.tts_text = ctk.CTkTextbox(card, font=FONT_BODY, fg_color=C["surface2"],
                                         text_color=C["text"], corner_radius=8,
                                         border_width=1, border_color=C["border"])
        self.tts_text.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        # 音频保存目录选择
        ctk.CTkLabel(card, text="音频保存目录:", font=FONT_SMALL,
                     text_color=C["text2"]).pack(anchor="w", padx=16, pady=(4, 0))
        audio_dir_row = ctk.CTkFrame(card, fg_color="transparent")
        audio_dir_row.pack(fill="x", padx=16, pady=(2, 8))
        self.tts_audio_dir_var = tk.StringVar(value="")
        self.tts_audio_dir_entry = ctk.CTkEntry(audio_dir_row, textvariable=self.tts_audio_dir_var,
                                                  font=FONT_MONO_SM, placeholder_text="留空则使用默认 output_audio 目录",
                                                  fg_color=C["surface2"], border_color=C["border"],
                                                  corner_radius=8)
        self.tts_audio_dir_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(audio_dir_row, text="选择目录", width=80, font=FONT_SMALL,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text"], corner_radius=6, height=30,
                       command=self._browse_tts_audio_dir).pack(side="left", padx=(6, 0))

        self.tts_gen_btn = CyberButton(scroll, text="⚡ 一键批量生成音频",
                                       variant="primary", height=BTN_HEIGHT_LG,
                                       command=self.start_tts_generate)
        self.tts_gen_btn.pack(fill="x", padx=PAD_LG, pady=(PAD_SM, PAD_MD))

        # 日志引用指向全局日志抽屉
        self.tts_log = self.global_log

    # ---------- API / Settings 页面 ----------

    def _build_page_api(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color=C["bg"])
        scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(scroll, text="API 与全局设置", font=FONT_TITLE,
                     text_color=C["accent"]).pack(anchor="w", padx=20, pady=(16, 16))

        # Base URL
        card = SectionCard(scroll, title="API Base URL")
        card.pack(fill="x", padx=20, pady=(0, 12))
        self.api_url_var = tk.StringVar(value=self.config.get("api_base_url", DEFAULT_CONFIG["api_base_url"]))
        ctk.CTkEntry(card, textvariable=self.api_url_var, font=FONT_MONO,
                      fg_color=C["surface2"], border_color=C["border"],
                      corner_radius=8).pack(fill="x", padx=16, pady=(4, 4))
        ctk.CTkLabel(card, text="Anthropic 兼容接口地址，末尾不需要加 /v1",
                     font=FONT_SMALL, text_color=C["text3"]).pack(anchor="w", padx=16, pady=(0, 10))

        # API Key
        card = SectionCard(scroll, title="API Key")
        card.pack(fill="x", padx=20, pady=(0, 12))
        key_row = ctk.CTkFrame(card, fg_color="transparent")
        key_row.pack(fill="x", padx=16, pady=(4, 4))
        self.api_key_var = tk.StringVar(value=self.config.get("api_key", DEFAULT_CONFIG["api_key"]))
        self.key_entry = ctk.CTkEntry(key_row, textvariable=self.api_key_var, show="*",
                                       font=FONT_MONO, fg_color=C["surface2"],
                                       border_color=C["border"], corner_radius=8)
        self.key_entry.pack(side="left", fill="x", expand=True)
        self.key_visible = tk.BooleanVar(value=False)
        self.toggle_key_btn = ctk.CTkButton(key_row, text="显示", width=60, font=FONT_SMALL,
                                             fg_color=C["surface2"], hover_color=C["border"],
                                             text_color=C["text"], corner_radius=6, height=30,
                                             command=self.toggle_key_visibility)
        self.toggle_key_btn.pack(side="left", padx=(8, 0))
        ctk.CTkLabel(card, text="密钥将以掩码显示",
                     font=FONT_SMALL, text_color=C["text3"]).pack(anchor="w", padx=16, pady=(0, 10))

        # Model
        card = SectionCard(scroll, title="模型名称")
        card.pack(fill="x", padx=20, pady=(0, 12))
        self.api_model_var = tk.StringVar(value=self.config.get("api_model", DEFAULT_CONFIG["api_model"]))
        ctk.CTkEntry(card, textvariable=self.api_model_var, font=FONT_MONO,
                      fg_color=C["surface2"], border_color=C["border"],
                      corner_radius=8).pack(fill="x", padx=16, pady=(4, 12))

        # 按钮
        btn_row = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(8, 4))
        ctk.CTkButton(btn_row, text="保存设置", font=FONT_BODY, fg_color=C["accent"],
                       text_color=C["bg"], hover_color=C["accent2"],
                       corner_radius=10, height=38,
                       command=self.save_settings).pack(side="left")
        ctk.CTkButton(btn_row, text="恢复默认", font=FONT_BODY, width=100,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text"], corner_radius=10, height=38,
                       command=self.reset_settings).pack(side="left", padx=10)

        self.settings_status = ctk.CTkLabel(scroll, text="", font=FONT_BODY,
                                             text_color=C["green"])
        self.settings_status.pack(anchor="w", padx=20, pady=(8, 0))

    # ---------- Assembly / 一键总装 页面 ----------

    def _build_page_assembly(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color=C["bg"])
        scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(scroll, text="一键总装 (FFmpeg)", font=FONT_TITLE,
                     text_color=C["accent"]).pack(anchor="w", padx=20, pady=(16, 8))

        # 状态卡片
        card = SectionCard(scroll, title="总装状态")
        card.pack(fill="x", padx=20, pady=(0, 12))

        self.asm_status_label = ctk.CTkLabel(card, text="正在检测镜头...",
                                              font=FONT_H2, text_color=C["text"])
        self.asm_status_label.pack(anchor="w", padx=16, pady=(8, 4))

        self.asm_detail_label = ctk.CTkLabel(card, text="视频: -- | 音频: -- | 台词: --",
                                              font=FONT_SMALL, text_color=C["text3"])
        self.asm_detail_label.pack(anchor="w", padx=16, pady=(0, 12))

        ctk.CTkButton(card, text="刷新检测", font=FONT_SMALL, width=80,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text"], corner_radius=6, height=28,
                       command=self._refresh_assembly_status).pack(anchor="w", padx=16, pady=(0, 12))

        # 项目命名与保存路径
        card = SectionCard(scroll, title="项目设置")
        card.pack(fill="x", padx=20, pady=(0, 12))

        ctk.CTkLabel(card, text="项目名称:", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w", padx=16, pady=(6, 0))
        self.project_name_var = tk.StringVar(value=self.config.get("project_name", ""))
        ctk.CTkEntry(card, textvariable=self.project_name_var, font=FONT_MONO,
                      placeholder_text="留空则使用 shot",
                      fg_color=C["surface2"], border_color=C["border"],
                      corner_radius=8).pack(fill="x", padx=16, pady=(2, 8))

        ctk.CTkLabel(card, text="保存路径:", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w", padx=16)
        save_row = ctk.CTkFrame(card, fg_color="transparent")
        save_row.pack(fill="x", padx=16, pady=(2, 4))
        self.save_path_var = tk.StringVar(value=self.config.get("save_path", ""))
        ctk.CTkEntry(save_row, textvariable=self.save_path_var, font=FONT_MONO_SM,
                      placeholder_text="留空则使用程序根目录",
                      fg_color=C["surface2"], border_color=C["border"],
                      corner_radius=8).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(save_row, text="浏览", width=60, font=FONT_SMALL,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text"], corner_radius=6, height=30,
                       command=self._browse_save_path).pack(side="left", padx=(6, 0))
        ctk.CTkLabel(card, text="音频/视频/成片均保存在此目录下",
                     font=FONT_SMALL, text_color=C["text3"]).pack(anchor="w", padx=16, pady=(0, 10))

        # 视频来源目录
        card = SectionCard(scroll, title="视频来源目录")
        card.pack(fill="x", padx=20, pady=(0, 12))
        dir_row = ctk.CTkFrame(card, fg_color="transparent")
        dir_row.pack(fill="x", padx=16, pady=(4, 4))
        self.asm_video_dir_var = tk.StringVar(value=os.path.join(os.path.dirname(os.path.abspath(__file__)), "output_video"))
        ctk.CTkEntry(dir_row, textvariable=self.asm_video_dir_var, font=FONT_MONO_SM,
                      fg_color=C["surface2"], border_color=C["border"],
                      corner_radius=8).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(dir_row, text="浏览", width=60, font=FONT_SMALL,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text"], corner_radius=6, height=30,
                       command=self._browse_asm_video_dir).pack(side="left", padx=(6, 0))
        ctk.CTkLabel(card, text="程序会自动将视频按创建时间映射为 shot_X.mp4",
                     font=FONT_SMALL, text_color=C["text3"]).pack(anchor="w", padx=16, pady=(0, 10))

        # 核心按钮
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(4, 12))

        self.asm_start_btn = ctk.CTkButton(
            btn_frame, text="开始一键高质量合片", font=FONT_H2,
            fg_color=C["accent"], text_color=C["bg"],
            hover_color=C["accent2"], corner_radius=12, height=48,
            command=self._start_assembly)
        self.asm_start_btn.pack(fill="x", pady=(0, 8))

        ctk.CTkButton(btn_frame, text="打开最终成片目录", font=FONT_BODY,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text"], corner_radius=10, height=38,
                       command=self._open_final_output).pack(anchor="w")

        # 日志
        ctk.CTkLabel(scroll, text="总装日志", font=FONT_H2,
                     text_color=C["text"]).pack(anchor="w", padx=20, pady=(8, 4))
        self.asm_log = LogBox(scroll)
        self.asm_log.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        # 启动时自动检测
        self.root.after(300, self._refresh_assembly_status)

    # ==================== Assembly 逻辑 ====================

    def _get_project_prefix(self):
        """获取项目文件名前缀，如 'my_project' 或 'shot'"""
        name = self.project_name_var.get().strip()
        return name if name else "shot"

    def _archive_old_files(self, sub_dirs=("output_video", "output_audio")):
        """将指定目录下的旧文件归档到 archive_history/[项目名]_备份_时间戳/"""
        import shutil
        base = os.path.dirname(os.path.abspath(__file__))
        save = self.save_path_var.get().strip()
        root = save if save and os.path.isdir(save) else base

        # 检查是否有需要归档的文件
        files_to_archive = []
        for sub in sub_dirs:
            d = os.path.join(root, sub)
            if os.path.isdir(d):
                for f in os.listdir(d):
                    full = os.path.join(d, f)
                    if os.path.isfile(full):
                        files_to_archive.append((sub, f, full))

        if not files_to_archive:
            return 0

        # 创建归档目录
        ts = time.strftime("%Y%m%d_%H%M%S")
        project = self.project_name_var.get().strip()
        folder_name = f"{project}_备份_{ts}" if project else f"默认项目_备份_{ts}"
        archive_dir = os.path.join(root, "archive_history", folder_name)
        os.makedirs(archive_dir, exist_ok=True)

        # 移动文件
        moved = 0
        for sub, fname, fpath in files_to_archive:
            dest_sub = os.path.join(archive_dir, sub)
            os.makedirs(dest_sub, exist_ok=True)
            dest = os.path.join(dest_sub, fname)
            try:
                shutil.move(fpath, dest)
                moved += 1
            except Exception:
                pass

        return moved

    def _shot_name(self, idx, ext=""):
        """生成 shot 文件名：有项目名 → 'proj_shot_0.mp4'，无项目名 → 'shot_0.mp4'"""
        name = self.project_name_var.get().strip()
        base = f"{name}_shot_{idx}" if name else f"shot_{idx}"
        return base + ext if ext else base

    def _tts_audio_name(self, idx, voice_name, text, ext=".wav"):
        """生成带音色名和台词前缀的音频文件名，防止覆盖"""
        import re
        # 预设音色名称
        voice = voice_name.strip() if voice_name else "默认"
        # 台词前4个字，清理特殊字符
        clean = text[:4] if text else ""
        clean = re.sub(r'[\\/:*?"<>|，。！？、；：\s\.\!\?\,\;\:]', '', clean)
        fname = f"{voice}_{clean}_{idx}{ext}"
        return fname

    def _get_output_dir(self, sub_dir):
        """根据用户保存路径配置，解析实际输出目录"""
        base = os.path.dirname(os.path.abspath(__file__))
        save = self.save_path_var.get().strip()
        if save and os.path.isdir(save):
            return os.path.join(save, sub_dir)
        return os.path.join(base, sub_dir)

    def _asm_log(self, msg):
        self.safe_after( lambda: self.global_log.append(f"[{time.strftime('%H:%M:%S')}] {msg}"))

    def _browse_save_path(self):
        path = filedialog.askdirectory(title="选择保存路径")
        if path:
            self.save_path_var.set(path)
            self._save_assembly_config()
            self._refresh_assembly_status()

    def _browse_asm_video_dir(self):
        path = filedialog.askdirectory(title="选择视频来源目录")
        if path:
            self.asm_video_dir_var.set(path)
            self._refresh_assembly_status()

    def _save_assembly_config(self):
        self.config["project_name"] = self.project_name_var.get().strip()
        self.config["save_path"] = self.save_path_var.get().strip()
        self.config["bailian_video_duration"] = self.video_duration_var.get()
        save_config(self.config)

    def _open_final_output(self):
        final_dir = self._get_output_dir("output_final")
        os.makedirs(final_dir, exist_ok=True)
        os.startfile(final_dir)

    def _find_file(self, directory, shot_num, ext):
        """在目录中查找匹配 shot_X.ext / {name}_shot_X.ext / {voice}_{text}_X.ext 的文件"""
        target = self._shot_name(shot_num, ext)
        exact = os.path.join(directory, target)
        if os.path.isfile(exact):
            return exact
        # 回退匹配任何 *_shot_X.ext 或 shot_X.ext
        import re
        pattern = re.compile(rf"shot_{shot_num}{re.escape(ext)}$", re.IGNORECASE)
        if os.path.isdir(directory):
            for f in os.listdir(directory):
                if pattern.search(f):
                    return os.path.join(directory, f)
        # 兼容新命名: 任意前缀_数字.ext（如 冰糖_你好世界_1.wav）
        pattern2 = re.compile(rf"_{shot_num}{re.escape(ext)}$", re.IGNORECASE)
        if os.path.isdir(directory):
            for f in os.listdir(directory):
                if pattern2.search(f):
                    return os.path.join(directory, f)
        return exact

    def _refresh_assembly_status(self):
        import re, shutil
        prefix = self._get_project_prefix()
        video_dir = self.asm_video_dir_var.get().strip()
        audio_dir = self._get_tts_audio_dir()

        # ---- 按时间顺序重命名：只处理非 shot_ 开头的 mp4 文件 ----
        renamed_count = 0
        if os.path.isdir(video_dir):
            # 先收集已有的 shot_X 编号
            existing_shots = set()
            unsorted_files = []
            for f in os.listdir(video_dir):
                if not f.lower().endswith(".mp4"):
                    continue
                full = os.path.join(video_dir, f)
                # 已经是 shot_ 开头的文件，记录编号，绝不重命名
                m = re.match(r"(?:.+_)?shot_(\d+)\.mp4$", f, re.IGNORECASE)
                if m:
                    existing_shots.add(int(m.group(1)))
                else:
                    ctime = os.path.getctime(full)
                    unsorted_files.append((ctime, f, full))

            # 按创建时间排序，分配不冲突的编号
            unsorted_files.sort(key=lambda x: x[0])
            next_num = 0
            for ctime, fname, fpath in unsorted_files:
                while next_num in existing_shots:
                    next_num += 1
                target_name = self._shot_name(next_num, ".mp4")
                target = os.path.join(video_dir, target_name)
                if fpath != target:
                    try:
                        shutil.copy2(fpath, target)
                        renamed_count += 1
                        existing_shots.add(next_num)
                    except Exception:
                        pass
                next_num += 1

        # ---- 检测视频（匹配 {prefix}_shot_X 或 shot_X）----
        video_shots = set()
        if os.path.isdir(video_dir):
            for f in os.listdir(video_dir):
                if f.lower().endswith(".mp4"):
                    m = re.match(r"(?:.+_)?shot_(\d+)\.mp4$", f, re.IGNORECASE)
                    if m:
                        video_shots.add(int(m.group(1)))

        # ---- 检测音频（匹配 shot_X / {voice}_{text}_X / {text}_X）----
        audio_shots = set()
        if os.path.isdir(audio_dir):
            for f in os.listdir(audio_dir):
                if f.lower().endswith(".wav"):
                    # 兼容旧格式 shot_X.wav
                    m = re.match(r"(?:.+_)?shot_(\d+)\.wav$", f, re.IGNORECASE)
                    if m:
                        audio_shots.add(int(m.group(1)))
                        continue
                    # 新格式: 任意前缀_数字.wav（如 冰糖_你好世界_1.wav）
                    m = re.match(r".+_(\d+)\.wav$", f, re.IGNORECASE)
                    if m:
                        audio_shots.add(int(m.group(1)))

        # 检测台词 (从 TTS 文本框)
        dialogue_count = 0
        try:
            content = self.tts_text.get("1.0", "end").strip()
            if content:
                dialogue_count = len([l for l in content.split("\n") if l.strip()])
        except Exception:
            pass

        matched = sorted(video_shots & audio_shots)
        total_video = len(video_shots)
        total_audio = len(audio_shots)

        if renamed_count:
            self.asm_status_label.configure(
                text=f"已自动映射 {renamed_count} 个视频 → 就绪镜头：{len(matched)} 个",
                text_color=C["green"] if matched else C["warn"])
        elif matched:
            self.asm_status_label.configure(
                text=f"当前准备就绪的镜头数量：{len(matched)} 个",
                text_color=C["green"])
        else:
            self.asm_status_label.configure(
                text="当前准备就绪的镜头数量：0 个",
                text_color=C["warn"])

        self.asm_detail_label.configure(
            text=f"项目: {prefix} | 视频: {total_video} | 音频: {total_audio} | 台词: {dialogue_count} | 匹配: {len(matched)}")

        self._matched_shots = matched
        self._video_shots_set = video_shots
        self._audio_shots_set = audio_shots

    def _start_assembly(self):
        self._save_assembly_config()
        self._refresh_assembly_status()
        if not hasattr(self, "_matched_shots") or not self._matched_shots:
            messagebox.showwarning("提示",
                "没有匹配的音画镜头！\n\n"
                "请确保：\n"
                "1. 视频目录下有 .mp4 文件\n"
                "2. 音频目录下有 shot_X.wav 文件\n\n"
                "程序会自动将视频按创建时间映射为 shot_X.mp4。\n"
                "可在上方修改「保存路径」和「项目名称」。")
            return

        # 收集台词
        dialogue_map = {}
        try:
            content = self.tts_text.get("1.0", "end").strip()
            if content:
                for i, line in enumerate(content.split("\n"), 1):
                    stripped = line.strip()
                    if stripped:
                        dialogue_map[i] = stripped
        except Exception:
            pass

        self.asm_start_btn.configure(state="disabled", text="合片中...")
        self.asm_log.clear_all()
        self._asm_log(f"开始总装，共 {len(self._matched_shots)} 个镜头")

        threading.Thread(target=self._assembly_worker,
                         args=(self._matched_shots, dialogue_map),
                         daemon=True).start()

    def _assembly_worker(self, shots, dialogue_map):
        import re, struct, subprocess

        prefix = self._get_project_prefix()
        video_dir = self.asm_video_dir_var.get().strip()
        audio_dir = self._get_tts_audio_dir()
        final_dir = self._get_output_dir("output_final")
        os.makedirs(final_dir, exist_ok=True)

        # 获取视频预设时长
        try:
            video_duration = float(self.video_duration_var.get())
        except Exception:
            video_duration = 5.0

        success, fail = 0, 0

        for shot_num in shots:
            # 智能查找视频文件（兼容 shot_X.mp4 和 {prefix}_shot_X.mp4）
            video_path = self._find_file(video_dir, shot_num, ".mp4")
            # 智能查找音频文件
            audio_path = self._find_file(audio_dir, shot_num, ".wav")
            srt_path = os.path.join(audio_dir, self._shot_name(shot_num, ".srt"))
            out_path = os.path.join(final_dir, self._shot_name(shot_num, "_FINAL.mp4"))

            if not os.path.isfile(video_path):
                self._asm_log(f"[{shot_num}] 视频不存在: {video_path}")
                fail += 1
                continue
            if not os.path.isfile(audio_path):
                self._asm_log(f"[{shot_num}] 音频不存在: {audio_path}")
                fail += 1
                continue

            # Step 1: 计算音频时长
            try:
                audio_duration = self._get_wav_duration(audio_path)
                self._asm_log(f"[{shot_num}] 音频时长: {audio_duration:.2f}s")
            except Exception as e:
                self._asm_log(f"[{shot_num}] 读取音频失败: {e}")
                fail += 1
                continue

            # Step 2: 生成 SRT 字幕
            dialogue_text = dialogue_map.get(shot_num, f"Shot {shot_num}")
            try:
                self._generate_srt(srt_path, dialogue_text, audio_duration)
                self._asm_log(f"[{shot_num}] 字幕已生成: {os.path.basename(srt_path)}")
            except Exception as e:
                self._asm_log(f"[{shot_num}] 字幕生成失败: {e}")
                fail += 1
                continue

            # Step 3: 计算 tpad 差值
            pad_len = max(0, audio_duration - video_duration)
            self._asm_log(f"[{shot_num}] 视频时长: {video_duration:.2f}s, 需延长: {pad_len:.2f}s")

            # Step 4: FFmpeg 合成
            try:
                self._run_ffmpeg_assembly(video_path, audio_path, srt_path, out_path, pad_len)
                self._asm_log(f"[镜头 {shot_num}] 合成成功！已压制高清字幕与本地克隆配音")
                success += 1
            except Exception as e:
                self._asm_log(f"[{shot_num}] FFmpeg 合成失败: {e}")
                fail += 1

        self._asm_log(f"{'='*40}")
        self._asm_log(f"总装完成: 成功 {success}，失败 {fail}")
        if success:
            self._asm_log(f"成片目录: {final_dir}")
        self.safe_after( lambda: self.asm_start_btn.configure(
            state="normal", text="开始一键高质量合片"))

    def _get_wav_duration(self, wav_path):
        import wave
        with wave.open(wav_path, "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            channels = wf.getnchannels()
            sw = wf.getsampwidth()
            header_dur = frames / rate
        # VibeVoice 生成的 wav 头部 frame count 可能不准确，用文件大小校验
        file_size = os.path.getsize(wav_path)
        data_bytes = file_size - 44  # 标准 WAV 头 44 字节
        calc_dur = data_bytes / (rate * channels * sw)
        # 如果头部时长超过文件大小计算值的 2 倍，说明头部有误
        if header_dur > calc_dur * 2:
            return calc_dur
        return header_dur

    def _generate_srt(self, srt_path, text, duration):
        def _fmt_ts(seconds):
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = int(seconds % 60)
            ms = int((seconds - int(seconds)) * 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(f"1\n")
            f.write(f"00:00:00,000 --> {_fmt_ts(duration)}\n")
            f.write(f"{text}\n")

    def _run_ffmpeg_assembly(self, video_path, audio_path, srt_path, out_path, pad_len):
        import subprocess

        # 使用libmp3lame编码器（兼容性更好）
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-f", "s16le",
            "-ar", "24000",
            "-ac", "1",
            "-i", audio_path,
            "-map", "0:v",
            "-map", "1:a",
            "-c:v", "copy",
            "-c:a", "libmp3lame",
            "-b:a", "128k",
            "-shortest",
            out_path
        ]

        self._asm_log(f"[{os.path.basename(out_path)}] FFmpeg 编码中...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(result.stderr[-300:] if result.stderr else "Unknown error")

    # ==================== VibeVoice 自动唤醒 ====================

    def _check_sovits_status(self, api_url):
        try:
            resp = requests.get(api_url, timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    def _refresh_vibevoice_characters(self):
        """智能唤醒 + 拉取角色列表（全自动闭环）"""
        api_url = self.sovits_url_var.get().strip().rstrip("/")
        if not api_url:
            self._tts_log_msg("错误: 请填写 VibeVoice API 地址！")
            return

        self.sovits_refresh_btn.configure(state="disabled", text="拉取中...")

        def _worker():
            # 1. 检测端口
            if not self._check_sovits_status(api_url):
                self._tts_log_msg("[自动化] VibeVoice 未运行，正在拉起...")
                bat_path = self.sovits_bat_var.get().strip()
                if bat_path and os.path.exists(bat_path):
                    import subprocess
                    try:
                        subprocess.Popen(["cmd", "/c", bat_path],
                                         creationflags=subprocess.CREATE_NEW_CONSOLE)
                        self._tts_log_msg(f"[自动化] 已执行: {bat_path}")
                    except Exception as e:
                        self._tts_log_msg(f"[自动化] 启动失败: {e}")
                        self._enable_refresh_btn()
                        return
                else:
                    self._tts_log_msg(f"[自动化] 未找到启动脚本: {bat_path}")
                    self._enable_refresh_btn()
                    return

                # 2. 智能等待
                self._tts_log_msg("[自动化] 等待引擎启动（每 2 秒检测，最多 60 秒）...")
                for elapsed in range(2, 62, 2):
                    _time.sleep(2)
                    if self._check_sovits_status(api_url):
                        self._tts_log_msg(f"[自动化] 引擎唤醒成功！（耗时 {elapsed} 秒）")
                        break
                    self._tts_log_msg(f"[自动化] 等待中... ({elapsed}/60s)")
                else:
                    self._tts_log_msg("[自动化] 超时：60 秒内引擎未响应")
                    self._enable_refresh_btn()
                    return
            else:
                self._tts_log_msg("[自动化] VibeVoice 已在线")

            # 3. 拉取角色列表
            try:
                resp = requests.get(f"{api_url}/api/characters", timeout=5)
                if resp.status_code != 200:
                    self._tts_log_msg(f"获取角色列表失败: HTTP {resp.status_code}")
                    self._enable_refresh_btn()
                    return
                chars = resp.json()
                if not chars:
                    self._tts_log_msg("角色列表为空，请先在 VibeVoice 中创建角色")
                    self._enable_refresh_btn()
                    return

                names = [c.get("name", "?") for c in chars]
                # 建立 name → id 映射
                self._char_name_to_id = {c.get("name", ""): c.get("id", "") for c in chars}
                current = self.sovits_character_var.get().strip()
                target = chars[0]
                for c in chars:
                    if c.get("name") == current:
                        target = c
                        break
                emotions = list(target.get("emotions", {}).keys())

                self.safe_after( lambda: self._apply_character(target, emotions, names))
            except Exception as e:
                self._tts_log_msg(f"连接 VibeVoice 失败: {e}")

            self._enable_refresh_btn()

        threading.Thread(target=_worker, daemon=True).start()

    def _enable_refresh_btn(self):
        self.safe_after( lambda: self.sovits_refresh_btn.configure(
            state="normal", text="刷新列表"))

    def _apply_character(self, char_info, emotions, all_names=None):
        if all_names:
            self.sovits_character_combo.configure(values=all_names)
        self.sovits_character_var.set(char_info.get("name", ""))
        if emotions:
            self.sovits_emotion_combo.configure(values=emotions)
            default_emo = char_info.get("default_emotion", emotions[0])
            self.sovits_emotion_var.set(default_emo if default_emo in emotions else emotions[0])
        self._tts_log_msg(f"已加载角色: {char_info.get('name', '?')}，情绪: {', '.join(emotions)}")

    # ==================== TTS 引擎切换 ====================

    def _on_tts_engine_change(self):
        engine = self.tts_engine_var.get()
        if engine == "bailian":
            self.sovits_frame.pack_forget()
            self.mimo_tts_frame.pack_forget()
            self.bailian_tts_frame.pack(fill="x", pady=(0, 8), after=self._tts_engine_card)
        elif engine == "mimo":
            self.bailian_tts_frame.pack_forget()
            self.sovits_frame.pack_forget()
            self.mimo_tts_frame.pack(fill="x", pady=(0, 8), after=self._tts_engine_card)
        else:  # sovits
            self.bailian_tts_frame.pack_forget()
            self.mimo_tts_frame.pack_forget()
            self.sovits_frame.pack(fill="x", pady=(0, 8), after=self._tts_engine_card)

    def _toggle_mimo_key_vis(self):
        if self.mimo_key_visible.get():
            self.mimo_key_entry.configure(show="")
            self.mimo_key_visible.set(False)
        else:
            self.mimo_key_entry.configure(show="*")
            self.mimo_key_visible.set(True)

    def _switch_mode(self, mode):
        """切换预设音色 / 声音复刻模式，更新按钮样式"""
        self.tts_adv_mode_var.set(mode)
        if mode == "preset":
            self._btn_preset.configure(fg_color=C["accent"], text_color=C["bg"], hover_color=C["accent2"])
            self._btn_clone.configure(fg_color=C["surface2"], text_color=C["text"], hover_color=C["border"])
            self._mode_hint.configure(text="当前：预设音色 + 情感指令驱动")
        else:
            self._btn_clone.configure(fg_color=C["accent"], text_color=C["bg"], hover_color=C["accent2"])
            self._btn_preset.configure(fg_color=C["surface2"], text_color=C["text"], hover_color=C["border"])
            self._mode_hint.configure(text="当前：声音复刻 (克隆参考音频)")
        self._on_adv_mode_change()

    def _on_adv_mode_change(self):
        mode = self.tts_adv_mode_var.get()
        if mode == "preset":
            self.tts_prompt_entry.configure(state="normal")
            self.tts_prompt_label.configure(text_color=C["text2"])
            self.tts_ref_entry.configure(state="normal")
            self.tts_ref_entry.delete(0, "end")
            self.tts_ref_entry.configure(state="disabled")
            self.tts_ref_btn.configure(state="disabled")
            self.tts_ref_label.configure(text_color=C["text3"])
        else:
            self.tts_ref_entry.configure(state="normal")
            self.tts_ref_label.configure(text_color=C["text2"])
            self.tts_ref_btn.configure(state="normal")
            self.tts_prompt_entry.configure(state="normal")
            self.tts_prompt_entry.delete(0, "end")
            self.tts_prompt_entry.configure(state="disabled")
            self.tts_prompt_label.configure(text_color=C["text3"])

    def _on_emotion_template_change(self, choice):
        """情感模板联动：选择模板后自动填充到文本框"""
        template_text = self._emotion_templates.get(choice, "")
        if template_text:
            self.tts_prompt_text_var.set(template_text)
        # 如果选择"自定义"，清空文本框让用户自己输入
        if choice == "自定义":
            self.tts_prompt_text_var.set("")

    # ==================== 百炼视觉引擎 ====================

    def _on_mode_changed(self, value=None):
        self._update_model_combo()
        self._toggle_video_settings()
        self._save_bailian_config()

    def _on_model_changed(self, value=None):
        # 从显示名 'wan2.7-i2v (📎 需要参考图)' 还原出模型ID 'wan2.7-i2v'
        display = self.bailian_model_var.get()
        model_id = _extract_model_id(display)
        self.bailian_model_var.set(model_id)
        self.bailian_info_label.configure(text=model_id)
        self._toggle_video_settings()
        self._save_bailian_config()

    def _on_ratio_changed(self, value=None):
        ratio = self.bailian_ratio_var.get()
        info = self.ratio_map.get(ratio, {})
        self.ratio_hint.configure(text=f"输出尺寸: {info.get('size', '')}")
        self._save_bailian_config()

    def _update_model_combo(self):
        mode = self.bailian_mode_var.get()
        models = BAILIAN_MODEL_MAP.get(mode, [])
        display_names = [_model_hint(m) for m in models]
        self._bailian_display_names = display_names  # 缓存
        self._bailian_model_ids = models
        self.bailian_model_combo.configure(values=display_names)
        # 确保当前选中的模型在列表里
        current_id = self.bailian_model_var.get()
        if current_id in models:
            idx = models.index(current_id)
            self.bailian_model_combo.set(display_names[idx])
        elif models:
            self.bailian_model_var.set(models[0])
            self.bailian_model_combo.set(display_names[0])
        if hasattr(self, "bailian_info_label"):
            self.bailian_info_label.configure(text=self.bailian_model_var.get())

    def _toggle_video_settings(self):
        model = self.bailian_model_var.get()
        if model in VIDEO_MODELS:
            self.video_settings_frame.pack(fill="x", pady=(0, 8))
            # 更新管线类型横幅
            pipeline_type = MODEL_PIPELINE_CACHE.get(model, PipelineType.IMAGE_GEN)
            type_labels = {
                PipelineType.TEXT_TO_VIDEO: ("📝 Text-to-Video", "无需参考图，纯文本驱动", C["green"]),
                PipelineType.IMAGE_TO_VIDEO: ("🖼️ Image-to-Video", "⚠️ 必须提供参考图！", C["warn"]),
                PipelineType.REF_TO_VIDEO: ("🎬 Reference-to-Video", "⚠️ 必须提供参考视频！", C["accent3"]),
                PipelineType.VIDEO_EDIT: ("✂️ Video Edit", "⚠️ 必须提供素材！", C["accent3"]),
            }
            label, hint, bg_color = type_labels.get(pipeline_type, ("❓ 未知", "", C["text3"]))
            self.pipeline_type_banner.configure(fg_color=bg_color)
            self.pipeline_type_label.configure(
                text=f"{label} — {hint}",
                text_color=C["bg"]
            )
            # 根据管线类型显示/隐藏参考图输入
            if pipeline_type in (PipelineType.IMAGE_TO_VIDEO, PipelineType.REF_TO_VIDEO, PipelineType.VIDEO_EDIT):
                self.ref_image_frame.pack(fill="x", padx=0, pady=0)
            else:
                self.ref_image_frame.pack_forget()
        else:
            self.video_settings_frame.pack_forget()

    def _browse_ref_image(self):
        path = filedialog.askopenfilename(
            title="选择参考图片",
            filetypes=[("图片", "*.png *.jpg *.jpeg *.webp"), ("所有文件", "*.*")])
        if path:
            self.ref_image_path_var.set(path)

    def _fill_prompt_from_tab1(self):
        import re
        content = self.script_output.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo("提示", "Script 页面中没有脚本内容，请先生成镜头脚本。")
            return

        shots = self._parse_script_shots(content)
        if not shots:
            messagebox.showinfo("提示", "未从脚本中找到 **英文 Prompt**: 关键词，请检查脚本格式。")
            return

        self._parsed_shots = shots
        shot_labels = [s["label"] for s in shots]
        self.bailian_shot_combo.configure(values=shot_labels)
        self.bailian_shot_combo.set(shot_labels[0])
        self._apply_shot(0)
        self._bailian_log_msg(f"已解析 {len(shots)} 个镜头，可用下拉菜单切换")

    # ========== MiMo 智能体命令处理 ==========

    def _agent_log(self, msg):
        """在智能体聊天框显示消息"""
        self.agent_chat_history.configure(state="normal")
        self.agent_chat_history.insert("end", msg + "\n")
        self.agent_chat_history.see("end")
        self.agent_chat_history.configure(state="disabled")

    def _agent_get_logs(self, lines=50):
        """收集最近的错误日志供智能体分析"""
        log_parts = []
        # 读取 crash.log 最后 N 行
        try:
            if os.path.exists(LOG_PATH):
                with open(LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
                    crash_lines = f.readlines()[-lines:]
                    if crash_lines:
                        log_parts.append("=== crash.log ===\n" + "".join(crash_lines))
        except Exception:
            pass
        # 读取 global_log 最后 N 行（LogBox 本身是 CTkTextbox）
        try:
            content = self.global_log.get(f"end-{lines}l", "end").strip()
            if content:
                log_parts.append(f"=== 应用日志 (最近{lines}行) ===\n" + content)
        except Exception:
            pass
        return "\n\n".join(log_parts) if log_parts else "暂无日志记录"

    def _agent_send_command(self):
        """处理智能体命令"""
        cmd = self.agent_input.get().strip()
        if not cmd:
            return
        self.agent_input.delete(0, "end")
        self._agent_log(f"🧑: {cmd}")

        # 简单命令匹配
        cmd_lower = cmd.lower()

        if any(k in cmd_lower for k in ["提取", "script", "导入提示词", "导入prompt"]):
            self._agent_log("🤖: 正在从Script提取提示词...")
            self._agent_extract_prompts()
        elif any(k in cmd_lower for k in ["清空", "清除", "删除所有"]):
            self._agent_log("🤖: 正在清空所有数据...")
            self._i2v_batch_clear()
            self._agent_log("🤖: ✅ 已清空")
        elif any(k in cmd_lower for k in ["开始生成", "开始批量", "生成视频"]):
            self._agent_log("🤖: 正在启动批量生成...")
            self._start_i2v_batch_generate()
        elif any(k in cmd_lower for k in ["全部优化", "优化全部", "优化提示词"]):
            self._agent_log("🤖: 正在调用MiMo优化全部提示词...")
            self._i2v_mimo_analyze_all()
        elif "第" in cmd and ("改成" in cmd or "修改为" in cmd or "改为" in cmd):
            self._agent_modify_single(cmd)
        elif "添加图片" in cmd or "选择图片" in cmd:
            self._agent_log("🤖: 正在打开图片选择...")
            self._i2v_batch_add_images()
        else:
            # 使用MiMo理解复杂命令
            self._agent_mimo_understand(cmd)

    def _agent_extract_prompts(self):
        """智能体提取提示词（自动创建图片占位）"""
        content = self.script_output.get("1.0", "end").strip()
        if not content:
            self._agent_log("🤖: ❌ Script页面没有脚本内容")
            return
        shots = self._parse_script_shots(content)
        if not shots:
            # 尝试用更宽松的方式提取
            self._agent_log("🤖: 未找到标准Prompt，尝试宽松提取...")
            prompts = self._extract_prompts_loose(content)
            if not prompts:
                self._agent_log("🤖: ❌ 无法提取提示词，请检查脚本格式")
                return
        else:
            prompts = [s["prompt"] for s in shots if s["prompt"]]

        # 清空现有数据
        self._i2v_batch_clear()

        # 为每个提示词创建一行（没有图片时创建占位）
        for i, prompt in enumerate(prompts):
            self._i2v_add_mapping_row("", prompt)  # 空图片路径

        self._i2v_batch_update_count()
        self._agent_log(f"🤖: ✅ 已提取 {len(prompts)} 条提示词")
        self._agent_log(f"🤖: 请添加对应数量的图片")

    def _extract_prompts_loose(self, content):
        """宽松提取提示词（兼容中文脚本）"""
        import re
        prompts = []
        # 尝试匹配各种格式
        patterns = [
            r"(?:英文|English)\s*Prompt\s*[:：]\s*(.+)",
            r"Prompt\s*[:：]\s*(.+)",
            r"描述\s*[:：]\s*(.+)",
            r"画面\s*[:：]\s*(.+)",
            r"Visual\s*[:：]\s*(.+)",
        ]
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            for pattern in patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    text = match.group(1).strip()
                    text = re.sub(r"\*+", "", text).strip()
                    if text and len(text) > 10:  # 过滤太短的
                        prompts.append(text)
                        break
        return prompts

    def _agent_modify_single(self, cmd):
        """修改单条提示词"""
        import re
        # 解析 "第X条改成xxx" 或 "第X个改为xxx"
        match = re.search(r"第(\d+)(?:条|个|行).*(?:改成|修改为|改为)\s*(.+)", cmd)
        if match:
            idx = int(match.group(1)) - 1
            new_text = match.group(2).strip()
            if idx < len(self._i2v_mapping_rows):
                entry = self._i2v_mapping_rows[idx]["prompt_entry"]
                entry.delete(0, "end")
                entry.insert(0, new_text)
                self._agent_log(f"🤖: ✅ 已修改第 {idx+1} 条提示词")
            else:
                self._agent_log(f"🤖: ❌ 第 {idx+1} 条不存在，当前共 {len(self._i2v_mapping_rows)} 条")
        else:
            self._agent_log("🤖: 格式不对，请用: 第X条改成xxx")

    def _agent_mimo_understand(self, cmd):
        """使用MiMo理解复杂命令"""
        api_key = self.config.get("mimo_api_key", "").strip()
        if not api_key:
            self._agent_log("🤖: ❌ 请先配置MiMo API Key")
            return

        self._agent_log("🤖: 正在理解命令...")

        # 当前状态
        img_count = len(self._i2v_batch_images)
        prompt_count = len(self._i2v_mapping_rows)
        current_prompts = []
        for row in self._i2v_mapping_rows:
            p = row["prompt_entry"].get().strip()
            if p:
                current_prompts.append(p[:50])

        status = f"当前状态: {img_count}张图片, {prompt_count}条提示词"
        if current_prompts:
            status += f"\n已有提示词: {', '.join(current_prompts[:3])}..."

        threading.Thread(target=self._agent_mimo_worker,
                        args=(cmd, status), daemon=True).start()

    def _agent_mimo_worker(self, cmd, status):
        """MiMo理解命令的工作线程"""
        # 从配置读取API设置，而不是硬编码
        api_key = self.config.get("mimo_api_key", "").strip()
        if not api_key:
            # 尝试使用全局API Key
            api_key = self.config.get("api_key", "").strip()

        # 使用配置中的base_url
        base_url = self.config.get("api_base_url", "https://token-plan-cn.xiaomimimo.com/anthropic").strip()
        # 确保使用OpenAI兼容端点
        if "/anthropic" in base_url:
            base_url = base_url.replace("/anthropic", "/v1")
        elif not base_url.endswith("/v1"):
            base_url = base_url.rstrip("/") + "/v1"

        # 使用配置中的模型名称
        model = self.config.get("api_model", "mimo-v2.5-pro").strip()

        self.safe_after(lambda m=f"🤖: 正在调用 {model} 分析命令...": self._agent_log(m))

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json; charset=utf-8",
        }
        system_prompt = f"""你是AI视频生成助手的命令解析器。{status}

用户会给你命令，请输出JSON格式的操作指令：
{{"action": "操作类型", "params": {{参数}}}}

支持的操作：
1. extract_prompts - 提取提示词
2. clear_all - 清空所有
3. start_generate - 开始生成
4. optimize_all - 优化全部提示词
5. modify_single - 修改单条 (params: {{"idx": 0, "text": "新提示词"}})
6. add_images - 添加图片
7. chat_reply - 普通回复 (params: {{"reply": "回复内容"}})
8. read_logs - 当用户问"哪里出错了"、"看看日志"、"帮我诊断"或遇到问题时，读取应用日志并诊断问题 (params: {{"reply": "诊断结果和解决建议"}})

只输出JSON，不要有其他内容。"""

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": cmd}
            ],
            "temperature": 0.3,
            "max_tokens": 1000000,
        }
        try:
            resp = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                timeout=120  # 长消息需要更多时间
            )
            if resp.status_code == 200:
                result = resp.json()
                ai_reply = result["choices"][0]["message"]["content"].strip()
                if not ai_reply:
                    self.safe_after( lambda: self._agent_log("🤖: ⚠️ MiMo 返回了空回复"))
                    return
                self.safe_after( lambda: self._agent_process_ai_command(ai_reply))
            else:
                error_msg = resp.text[:200] if resp.text else f"HTTP {resp.status_code}"
                logs = self._agent_get_logs(30)
                self.safe_after( lambda m=f"🤖: ❌ API错误: {error_msg}\n📋 最近日志:\n{logs[:800]}": self._agent_log(m))
        except requests.exceptions.Timeout:
            logs = self._agent_get_logs(30)
            self.safe_after( lambda m=f"🤖: ❌ 请求超时（120秒），消息可能过长\n📋 最近日志:\n{logs[:800]}": self._agent_log(m))
        except Exception as e:
            logs = self._agent_get_logs(30)
            self.safe_after( lambda m=f"🤖: ❌ 错误: {e}\n📋 最近日志:\n{logs[:800]}": self._agent_log(m))

    def _agent_process_ai_command(self, ai_reply):
        """处理AI返回的命令"""
        try:
            # 尝试解析JSON
            import re
            json_match = re.search(r'\{.*\}', ai_reply, re.DOTALL)
            if json_match:
                cmd_data = json.loads(json_match.group())
                action = cmd_data.get("action", "")
                params = cmd_data.get("params", {})

                if action == "extract_prompts":
                    self._agent_extract_prompts()
                elif action == "clear_all":
                    self._i2v_batch_clear()
                    self._agent_log("🤖: ✅ 已清空")
                elif action == "start_generate":
                    self._start_i2v_batch_generate()
                elif action == "optimize_all":
                    self._i2v_mimo_analyze_all()
                elif action == "modify_single":
                    idx = params.get("idx", 0)
                    text = params.get("text", "")
                    if idx < len(self._i2v_mapping_rows) and text:
                        entry = self._i2v_mapping_rows[idx]["prompt_entry"]
                        entry.delete(0, "end")
                        entry.insert(0, text)
                        self._agent_log(f"🤖: ✅ 已修改第 {idx+1} 条")
                    else:
                        self._agent_log("🤖: ❌ 索引超范围或文本为空")
                elif action == "add_images":
                    self._i2v_batch_add_images()
                elif action == "chat_reply":
                    self._agent_log(f"🤖: {params.get('reply', '')}")
                elif action == "read_logs":
                    self._agent_log(f"🤖: {params.get('reply', '')}")
                    logs = self._agent_get_logs()
                    self._agent_log(f"📋 最近日志:\n{logs[:1000]}")
                else:
                    self._agent_log(f"🤖: {ai_reply}")
            else:
                self._agent_log(f"🤖: {ai_reply}")
        except Exception as e:
            self._agent_log(f"🤖: ❌ 解析AI回复失败: {e}")
            self._agent_log(f"🤖: 原始回复: {ai_reply[:200]}")

    # ========== 批量图生视频 (I2V Batch) 核心函数 ==========

    def _on_duration_mode_change(self):
        """切换自动/手动时长模式"""
        if self.i2v_duration_mode.get() == "manual":
            self.i2v_duration_entry.configure(state="normal")
        else:
            self.i2v_duration_entry.configure(state="disabled")

    def _i2v_batch_update_count(self):
        """更新计数显示"""
        img_count = len(self._i2v_batch_images)
        prompt_count = len(self._i2v_mapping_rows)
        color = C["green"] if img_count == prompt_count and img_count > 0 else C["warn"]
        self.i2v_batch_count_label.configure(
            text=f"{img_count} 图 / {prompt_count} 提示词",
            text_color=color
        )

    def _i2v_batch_add_images(self):
        """批量添加参考图片"""
        files = filedialog.askopenfilenames(
            title="选择参考图片（可多选）",
            filetypes=[("图片", "*.png *.jpg *.jpeg *.webp"), ("所有文件", "*.*")]
        )
        if files:
            old_img_count = len(self._i2v_batch_images)
            self._i2v_batch_images.extend(files)
            # 为每张新图片创建对应的表格行
            for img_path in files:
                self._i2v_add_mapping_row(img_path, "")
            self._i2v_batch_update_count()
            # 检查数量是否匹配
            new_img_count = len(self._i2v_batch_images)
            prompt_count = len(self._i2v_mapping_rows)
            if prompt_count > 0 and new_img_count != prompt_count:
                messagebox.showwarning("数量不匹配",
                    f"⚠️ 当前图片 ({new_img_count}) 与已有提示词 ({prompt_count}) 数量不一致！\n\n"
                    f"请补充提示词或删除多余图片。")

    def _i2v_add_mapping_row(self, img_path, prompt):
        """添加一行图片-提示词对应关系"""
        # 隐藏空状态提示
        self.i2v_empty_label.pack_forget()

        row_idx = len(self._i2v_mapping_rows) + 1
        row_frame = ctk.CTkFrame(self.i2v_mapping_frame, fg_color="transparent")
        row_frame.pack(fill="x", pady=1)

        # 序号
        num_label = ctk.CTkLabel(row_frame, text=str(row_idx), font=FONT_SMALL,
                                 text_color=C["text3"], width=30)
        num_label.pack(side="left")

        # 图片预览缩略图
        preview_label = ctk.CTkLabel(row_frame, text="", width=50, height=50,
                                     fg_color=C["surface"], corner_radius=4)
        preview_label.pack(side="left", padx=2)
        try:
            img = Image.open(img_path)
            img.thumbnail((45, 45), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            preview_label.configure(image=photo, text="")
            preview_label.image = photo  # 保持引用
        except Exception:
            preview_label.configure(text="❌")

        # 提示词输入框
        prompt_entry = ctk.CTkEntry(row_frame, font=FONT_SMALL,
                                    fg_color=C["surface"], border_color=C["border"],
                                    corner_radius=4, placeholder_text="输入提示词...")
        prompt_entry.pack(side="left", padx=2, fill="x", expand=True)
        if prompt:
            prompt_entry.insert(0, prompt)

        # 时长输入
        duration_entry = ctk.CTkEntry(row_frame, width=40, font=FONT_MONO_SM,
                                      fg_color=C["surface"], border_color=C["border"],
                                      corner_radius=4)
        duration_entry.pack(side="left", padx=2)
        duration_entry.insert(0, "5")

        # 操作按钮
        btn_row = ctk.CTkFrame(row_frame, fg_color="transparent")
        btn_row.pack(side="left", padx=2)
        ctk.CTkButton(btn_row, text="💬", font=FONT_SMALL, width=24,
                      fg_color=C["accent"], hover_color=C["accent2"],
                      text_color=C["bg"], corner_radius=4, height=24,
                      command=lambda idx=row_idx-1: self._i2v_open_chat(idx)).pack(side="left", padx=1)
        ctk.CTkButton(btn_row, text="AI", font=FONT_SMALL, width=30,
                      fg_color=C["blue"], hover_color="#3AA5E0",
                      text_color="#FFF", corner_radius=4, height=24,
                      command=lambda idx=row_idx-1: self._i2v_mimo_analyze_single(idx)).pack(side="left", padx=1)
        ctk.CTkButton(btn_row, text="×", font=FONT_SMALL, width=24,
                      fg_color=C["red"], hover_color="#FF5555",
                      text_color="#FFF", corner_radius=4, height=24,
                      command=lambda idx=row_idx-1: self._i2v_remove_mapping_row(idx)).pack(side="left", padx=1)

        self._i2v_mapping_rows.append({
            "frame": row_frame,
            "num_label": num_label,
            "preview_label": preview_label,
            "prompt_entry": prompt_entry,
            "duration_entry": duration_entry,
            "img_path": img_path,
        })

    def _i2v_remove_mapping_row(self, idx):
        """删除指定行"""
        if idx >= len(self._i2v_mapping_rows):
            return
        row = self._i2v_mapping_rows[idx]
        row["frame"].destroy()
        self._i2v_mapping_rows.pop(idx)
        self._i2v_batch_images.pop(idx)
        # 重新编号
        for i, row_data in enumerate(self._i2v_mapping_rows):
            row_data["num_label"].configure(text=str(i + 1))
        # 更新所有按钮的索引
        for i, row_data in enumerate(self._i2v_mapping_rows):
            btn_row = row_data["frame"].winfo_children()[-1]  # 最后一个子组件是btn_row
            if isinstance(btn_row, ctk.CTkFrame):
                for btn in btn_row.winfo_children():
                    text = btn.cget("text")
                    if text == "💬":
                        btn.configure(command=lambda idx=i: self._i2v_open_chat(idx))
                    elif text == "AI":
                        btn.configure(command=lambda idx=i: self._i2v_mimo_analyze_single(idx))
                    elif text == "×":
                        btn.configure(command=lambda idx=i: self._i2v_remove_mapping_row(idx))
        self._i2v_batch_update_count()
        # 如果删除后为空，显示空状态提示
        if not self._i2v_mapping_rows:
            self.i2v_empty_label.pack(pady=20)

    def _i2v_extract_prompts_from_script(self):
        """从 Script 页面提取提示词到对应行（支持中英文）"""
        content = self.script_output.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo("提示", "Script 页面中没有脚本内容。")
            return

        # 优先尝试标准格式
        shots = self._parse_script_shots(content)
        if shots:
            prompts = [s["prompt"] for s in shots if s["prompt"]]
        else:
            # 使用宽松提取
            prompts = self._extract_prompts_loose(content)
            if not prompts:
                # 最后尝试：按段落提取（每个镜头的描述）
                prompts = self._extract_prompts_by_paragraph(content)

        if not prompts:
            messagebox.showinfo("提示",
                "未从脚本中找到提示词。\n\n"
                "支持的格式：\n"
                "• 英文 Prompt: xxx\n"
                "• 画面描述: xxx\n"
                "• 每个镜头段落的描述文字")
            return

        # 检测数量是否匹配
        img_count = len(self._i2v_batch_images)
        prompt_count = len(prompts)
        if img_count > 0 and img_count != prompt_count:
            result = messagebox.askyesno("数量不匹配",
                f"⚠️ 图片数量 ({img_count}) ≠ 提示词数量 ({prompt_count})\n\n"
                f"是否继续提取？\n"
                f"• 点击「是」：提取后请手动调整对应关系\n"
                f"• 点击「否」：取消操作")
            if not result:
                return

        # 清空现有提示词行（保留图片）
        for row in self._i2v_mapping_rows:
            row["prompt_entry"].delete(0, "end")

        # 填入提示词
        for i, prompt in enumerate(prompts):
            if i < len(self._i2v_mapping_rows):
                self._i2v_mapping_rows[i]["prompt_entry"].insert(0, prompt)
            else:
                # 没有对应图片，创建空图占位
                self._i2v_add_mapping_row("", prompt)

        self._i2v_batch_update_count()
        self._bailian_log_msg(f"已提取 {len(prompts)} 条提示词")
        if img_count > 0 and img_count != prompt_count:
            messagebox.showwarning("注意",
                f"图片 ({img_count}) 与提示词 ({prompt_count}) 数量不一致！\n"
                "请检查对应关系，可点击某行的「×」删除多余项。")

    def _extract_prompts_by_paragraph(self, content):
        """按段落提取提示词（每个镜头块取描述）"""
        import re
        prompts = []
        # 按分隔线或空行分割
        blocks = re.split(r'[-=]{3,}|\n\s*\n', content)
        for block in blocks:
            block = block.strip()
            if not block or len(block) < 20:
                continue
            # 取最长的那行作为描述
            lines = [l.strip() for l in block.split("\n") if l.strip() and len(l.strip()) > 15]
            if lines:
                # 过滤掉纯标题行
                desc_lines = [l for l in lines if not re.match(r'^(镜头|Shot|#|\d+[:：])', l)]
                if desc_lines:
                    prompts.append(desc_lines[0])
                elif len(lines) > 1:
                    prompts.append(lines[1])
        return prompts[:15]  # 最多15个镜头

    def _i2v_mimo_analyze_single(self, idx):
        """使用MiMo优化单条提示词（结合图片上下文）"""
        if idx >= len(self._i2v_mapping_rows):
            return
        row = self._i2v_mapping_rows[idx]
        prompt = row["prompt_entry"].get().strip()
        img_path = row["img_path"]
        img_name = os.path.basename(img_path) if img_path else "无图片"
        self._bailian_log_msg(f"MiMo 正在优化第 {idx+1} 条提示词 (图片: {img_name})...")
        threading.Thread(target=self._i2v_mimo_worker, args=([{"idx": idx, "prompt": prompt, "img_name": img_name}],), daemon=True).start()

    def _i2v_open_chat(self, idx):
        """打开MiMo聊天窗口来修改指定提示词"""
        if idx >= len(self._i2v_mapping_rows):
            return
        row = self._i2v_mapping_rows[idx]
        current_prompt = row["prompt_entry"].get().strip()
        img_path = row["img_path"]
        img_name = os.path.basename(img_path) if img_path else "无图片"

        # 创建聊天窗口
        chat_window = ctk.CTkToplevel(self.root)
        chat_window.title(f"MiMo AI 聊天 - 第 {idx+1} 行 (图片: {img_name})")
        chat_window.geometry("600x550")
        chat_window.configure(fg_color=C["bg"])
        chat_window.transient(self.root)
        chat_window.grab_set()

        # 当前提示词显示（实时更新）
        ctk.CTkLabel(chat_window, text=f"📷 当前图片: {img_name}", font=FONT_SMALL,
                     text_color=C["text3"]).pack(anchor="w", padx=16, pady=(12, 2))
        ctk.CTkLabel(chat_window, text="📝 当前提示词 (实时更新):", font=FONT_SMALL,
                     text_color=C["text2"]).pack(anchor="w", padx=16, pady=(0, 2))
        prompt_display = ctk.CTkTextbox(chat_window, height=70, font=FONT_MONO_SM,
                                        fg_color=C["surface2"], text_color=C["accent"],
                                        corner_radius=8, border_width=1, border_color=C["border"])
        prompt_display.pack(fill="x", padx=16, pady=(0, 8))
        prompt_display.insert("1.0", current_prompt)
        prompt_display.configure(state="disabled")

        # 聊天记录区
        ctk.CTkLabel(chat_window, text="对话:", font=FONT_SMALL,
                     text_color=C["text"]).pack(anchor="w", padx=16, pady=(4, 2))
        chat_history = ctk.CTkTextbox(chat_window, height=200, font=FONT_BODY,
                                      fg_color=C["surface2"], text_color=C["text"],
                                      corner_radius=8, border_width=1, border_color=C["border"])
        chat_history.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        chat_history.configure(state="disabled")

        # 输入区
        input_frame = ctk.CTkFrame(chat_window, fg_color="transparent")
        input_frame.pack(fill="x", padx=16, pady=(0, 8))
        chat_input = ctk.CTkEntry(input_frame, font=FONT_BODY,
                                  fg_color=C["surface2"], border_color=C["border"],
                                  corner_radius=8, placeholder_text="输入你想怎么修改提示词...")
        chat_input.pack(side="left", fill="x", expand=True, padx=(0, 8))

        def send_message():
            user_msg = chat_input.get().strip()
            if not user_msg:
                return
            chat_input.delete(0, "end")
            # 显示用户消息
            chat_history.configure(state="normal")
            chat_history.insert("end", f"你: {user_msg}\n\n")
            chat_history.configure(state="disabled")
            chat_history.see("end")
            # 调用MiMo
            threading.Thread(target=_chat_with_mimo,
                           args=(user_msg, current_prompt, img_name, idx),
                           daemon=True).start()

        def _chat_with_mimo(user_msg, prompt, img_name, chat_idx):
            api_key = self.config.get("mimo_api_key", "").strip()
            if not api_key:
                self.safe_after( lambda: _show_ai_response("错误: 请先配置 MiMo API Key！"))
                return
            # 使用配置中的base_url
            base_url = self.config.get("api_base_url", "https://token-plan-cn.xiaomimimo.com/anthropic").strip()
            if "/anthropic" in base_url:
                base_url = base_url.replace("/anthropic", "/v1")
            elif not base_url.endswith("/v1"):
                base_url = base_url.rstrip("/") + "/v1"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json; charset=utf-8",
            }
            system_prompt = f"""你是AI视频生成提示词优化助手。
当前图片文件名: {img_name}
当前提示词: {prompt}

用户会告诉你如何修改提示词。请根据用户的要求，直接输出修改后的完整英文提示词。
注意：
1. 只输出修改后的提示词，不要有其他解释
2. 保持英文，适合AI视频生成使用
3. 控制在50-100词"""
            payload = {
                "model": "mimo-v2.5-pro",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg}
                ],
                "temperature": 0.7,
                "max_tokens": 500,
            }
            try:
                resp = requests.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                    timeout=60
                )
                if resp.status_code == 200:
                    result = resp.json()
                    ai_response = result["choices"][0]["message"]["content"].strip()
                    self.safe_after( lambda: _show_ai_response(ai_response, chat_idx))
                else:
                    self.safe_after( lambda: _show_ai_response(f"API错误: {resp.status_code}"))
            except Exception as e:
                self.safe_after( lambda: _show_ai_response(f"错误: {e}"))

        def _show_ai_response(response, chat_idx=None):
            chat_history.configure(state="normal")
            chat_history.insert("end", f"MiMo: {response}\n\n")
            chat_history.configure(state="disabled")
            chat_history.see("end")
            # 自动更新提示词到对应的输入框
            if chat_idx is not None and response and not response.startswith("错误") and not response.startswith("API错误"):
                self.root.after(100, lambda: _auto_apply_prompt(response, chat_idx))

        def _auto_apply_prompt(new_prompt, chat_idx):
            """自动将AI回复应用到提示词输入框"""
            if chat_idx < len(self._i2v_mapping_rows):
                entry = self._i2v_mapping_rows[chat_idx]["prompt_entry"]
                entry.delete(0, "end")
                entry.insert(0, new_prompt)
                # 同步更新聊天窗口中的提示词显示
                prompt_display.configure(state="normal")
                prompt_display.delete("1.0", "end")
                prompt_display.insert("1.0", new_prompt)
                prompt_display.configure(state="disabled")
                # 显示成功提示
                chat_history.configure(state="normal")
                chat_history.insert("end", f"✅ 提示词已自动更新！可继续修改或关闭窗口\n\n")
                chat_history.configure(state="disabled")
                chat_history.see("end")

        send_btn = ctk.CTkButton(input_frame, text="发送", font=FONT_BODY, width=60,
                                 fg_color=C["accent"], text_color=C["bg"],
                                 hover_color=C["accent2"], corner_radius=8,
                                 command=send_message)
        send_btn.pack(side="left")

        # 底部按钮
        btn_frame = ctk.CTkFrame(chat_window, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkLabel(btn_frame, text="💡 MiMo回复后会自动更新提示词，可多次对话调整",
                     font=FONT_SMALL, text_color=C["accent"]).pack(side="left")
        ctk.CTkButton(btn_frame, text="关闭", font=FONT_BODY, width=80,
                      fg_color=C["surface2"], text_color=C["text"],
                      hover_color=C["border"], corner_radius=8,
                      command=chat_window.destroy).pack(side="right", padx=4)

        chat_input.bind("<Return>", lambda e: send_message())

    def _i2v_mimo_analyze_all(self):
        """使用MiMo批量优化所有提示词"""
        if not self._i2v_mapping_rows:
            messagebox.showinfo("提示", "请先添加图片和提示词！")
            return
        data_list = []
        for i, row in enumerate(self._i2v_mapping_rows):
            prompt = row["prompt_entry"].get().strip()
            img_name = os.path.basename(row["img_path"]) if row["img_path"] else "无图片"
            data_list.append({"idx": i, "prompt": prompt, "img_name": img_name})
        self._bailian_log_msg(f"MiMo 正在批量优化 {len(data_list)} 条提示词...")
        threading.Thread(target=self._i2v_mimo_worker, args=(data_list,), daemon=True).start()

    def _i2v_mimo_worker(self, data_list):
        """MiMo API分析优化提示词的工作线程（结合图片上下文）"""
        api_key = self.config.get("mimo_api_key", "").strip()
        if not api_key:
            self._bailian_log_msg("错误: 请先在「智能配音」页面配置 MiMo API Key！")
            return

        # 使用配置中的base_url
        base_url = self.config.get("api_base_url", "https://token-plan-cn.xiaomimimo.com/anthropic").strip()
        if "/anthropic" in base_url:
            base_url = base_url.replace("/anthropic", "/v1")
        elif not base_url.endswith("/v1"):
            base_url = base_url.rstrip("/") + "/v1"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json; charset=utf-8",
        }
        system_prompt = """你是AI视频生成提示词优化专家。用户会提供图片文件名和初始提示词。
请根据图片文件名推测可能的画面内容，并优化提示词：
1. 保持原始创意核心不变
2. 根据文件名推测场景并增加具体视觉细节（光影、构图、色彩、氛围）
3. 添加运镜方式（推拉摇移跟升降）
4. 添加电影级画面描述词
5. 确保英文表达准确流畅
6. 优化后的提示词控制在50-100词

请直接输出优化后的英文提示词，不要有其他解释。"""

        success_count = 0
        for data in data_list:
            idx = data["idx"]
            prompt = data["prompt"]
            img_name = data["img_name"]
            if not prompt:
                self._bailian_log_msg(f"[{idx+1}] 跳过：无提示词")
                continue
            try:
                user_content = f"图片文件名: {img_name}\n初始提示词: {prompt}\n\n请优化这个视频生成提示词。"
                payload = {
                    "model": "mimo-v2.5-pro",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 500,
                }
                resp = requests.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                    timeout=60
                )
                if resp.status_code == 200:
                    result = resp.json()
                    optimized = result["choices"][0]["message"]["content"].strip()
                    # 更新UI
                    self.safe_after( lambda i=idx, opt=optimized: self._i2v_apply_single(i, opt))
                    success_count += 1
                    self._bailian_log_msg(f"[{idx+1}/{len(data_list)}] ✓ 优化完成")
                else:
                    self._bailian_log_msg(f"[{idx+1}/{len(data_list)}] ✗ API错误: {resp.status_code}")
            except Exception as e:
                self._bailian_log_msg(f"[{idx+1}/{len(data_list)}] ✗ 失败: {e}")

        self._bailian_log_msg(f"优化完成: {success_count}/{len(data_list)}")
        if success_count > 0:
            messagebox.showinfo("完成", f"MiMo 已优化 {success_count} 条提示词！")

    def _i2v_apply_single(self, idx, optimized_prompt):
        """应用单条优化后的提示词"""
        if idx >= len(self._i2v_mapping_rows):
            return
        entry = self._i2v_mapping_rows[idx]["prompt_entry"]
        entry.delete(0, "end")
        entry.insert(0, optimized_prompt)

    def _i2v_batch_clear(self):
        """清空全部数据"""
        self._i2v_batch_images = []
        for row in self._i2v_mapping_rows:
            row["frame"].destroy()
        self._i2v_mapping_rows = []
        self.i2v_empty_label.pack(pady=20)
        self._i2v_batch_update_count()

    def _start_i2v_batch_generate(self):
        """启动批量图生视频生成"""
        api_key = self.bailian_key_var.get().strip()
        if not api_key:
            messagebox.showwarning("提示", "请先填写百炼 API Key！")
            return

        model = self.bailian_model_var.get()
        pipeline_type = MODEL_PIPELINE_CACHE.get(model, PipelineType.IMAGE_GEN)
        if pipeline_type != PipelineType.IMAGE_TO_VIDEO:
            messagebox.showwarning("提示",
                f"当前模型 {model} 不是 Image-to-Video 类型！\n请在「生成模式」中选择 i2v 模型（如 wan2.7-i2v）。")
            return

        if not self._i2v_mapping_rows:
            messagebox.showwarning("提示", "请先添加图片和提示词！")
            return

        # 收集数据并校验
        data_pairs = []
        for i, row in enumerate(self._i2v_mapping_rows):
            img_path = row["img_path"]
            prompt = row["prompt_entry"].get().strip()
            if not img_path:
                messagebox.showerror("校验失败", f"第 {i+1} 行缺少图片！")
                return
            if not prompt:
                messagebox.showerror("校验失败", f"第 {i+1} 行缺少提示词！")
                return
            # 获取时长
            if self.i2v_duration_mode.get() == "auto":
                duration = self._estimate_duration_from_prompt(prompt)
            else:
                try:
                    duration = int(self.i2v_duration_entry.get())
                except ValueError:
                    duration = 5
            data_pairs.append((img_path, prompt, duration))

        self._save_bailian_config()
        archived = self._archive_old_files(("output_video",))
        if archived:
            self._bailian_log_msg(f"[归档] 已将 {archived} 个旧文件移入 archive_history")

        self._bailian_log_msg(f"{'='*40}")
        self._bailian_log_msg(f"批量图生视频启动: {len(data_pairs)} 组")
        self._bailian_log_msg(f"模型: {model}")
        self._bailian_log_msg(f"时长模式: {'自动' if self.i2v_duration_mode.get() == 'auto' else '手动'}")
        self._bailian_log_msg(f"{'='*40}")

        threading.Thread(
            target=self._i2v_batch_worker,
            args=(api_key, model, data_pairs),
            daemon=True
        ).start()

    def _estimate_duration_from_prompt(self, prompt):
        """根据提示词自动估算合适的视频时长"""
        word_count = len(prompt.split())
        if word_count < 15:
            return 3
        elif word_count < 30:
            return 5
        elif word_count < 50:
            return 7
        else:
            return 10

    def _i2v_batch_worker(self, api_key, model, data_pairs):
        """批量图生视频后台工作线程"""
        ok, fail = 0, 0
        total = len(data_pairs)
        for i, (img_path, prompt, duration) in enumerate(data_pairs, 1):
            # 熔断检查
            if BatchProcessor._bailian_circuit_open:
                self._bailian_log_msg(f"⚠️ 熔断已触发，中止剩余 {total - i + 1} 个任务")
                break
            img_name = os.path.basename(img_path)
            self._bailian_log_msg(f"[{i}/{total}] {img_name} | {duration}s")
            self._bailian_log_msg(f"[{i}/{total}] Prompt: {prompt[:50]}...")
            try:
                self._bailian_generate_video(api_key, model, prompt, img_path, str(duration))
                ok += 1
                self._bailian_log_msg(f"[{i}/{total}] 任务已提交")
            except Exception as e:
                fail += 1
                self._bailian_log_msg(f"[{i}/{total}] 失败: {e}")

        # 使用用户配置的保存路径
        out_dir = self._get_output_dir("output_video")
        self._bailian_log_msg(f"{'='*40}")
        self._bailian_log_msg(f"完成: 成功 {ok}, 失败 {fail}")
        self._bailian_log_msg(f"视频保存目录: {out_dir}")
        if ok > 0:
            result = messagebox.askyesno("完成",
                f"批量图生视频完成！\n成功: {ok}\n失败: {fail}\n\n"
                f"视频正在后台生成中...\n"
                f"保存位置: {out_dir}\n\n"
                f"是否打开输出目录？")
            if result:
                os.startfile(out_dir)

    def _parse_script_shots(self, content):
        import re
        # ---- 全量抓取：用正则搜索所有 英文 Prompt 和 时长 ----
        # 匹配 **英文 Prompt**: xxx / English Prompt: xxx / 英文Prompt：xxx 等任意格式
        prompt_pattern = re.compile(
            r"(?:英文|English)\s*\*{0,2}\s*Prompt\s*\*{0,2}\s*[:：]\s*(.+)",
            re.IGNORECASE,
        )
        duration_pattern = re.compile(
            r"(?:时长|時長|Duration)\s*\*{0,2}\s*[:：]\s*(\d+(?:\.\d+)?)\s*(?:s|秒|sec)?",
            re.IGNORECASE,
        )

        # 逐行扫描，按出现顺序收集 prompt 和 duration
        raw_prompts = []
        raw_durations = []
        for line in content.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            # 尝试匹配 Prompt
            pm = prompt_pattern.search(stripped)
            if pm:
                text = self._clean_prompt(pm.group(1))
                if text:
                    raw_prompts.append(text)
                continue
            # 尝试匹配时长
            dm = duration_pattern.search(stripped)
            if dm:
                raw_durations.append(float(dm.group(1)))

        if not raw_prompts:
            return []

        # ---- 组装 shots 列表 ----
        shots = []
        for i, prompt in enumerate(raw_prompts):
            num = i + 1
            duration = raw_durations[i] if i < len(raw_durations) else None
            if duration is None:
                duration = self._estimate_duration(prompt)
            shots.append({
                "num": num,
                "label": f"镜头 {num}",
                "prompt": prompt,
                "duration": duration,
            })

        return shots

    def _clean_prompt(self, raw_text):
        import re
        text = re.sub(r"\*+", "", raw_text).strip()
        # 过滤文学性修饰词，保留核心视觉描述
        literary = [
            r"\b(?:breathtaking|stunning|gorgeous|magnificent|exquisite)\b",
            r"\b(?:masterpiece|award-winning|cinematic masterpiece)\b",
            r"\b(?:unparalleled|extraordinary|sublime|ethereal)\b",
            r"\b(?:captivating|mesmerizing|enchanting|awe-inspiring)\b",
            r"\b(?:无与伦比|令人叹为观止|美轮美奂|如诗如画)\b",
        ]
        for pat in literary:
            text = re.sub(pat, "", text, flags=re.IGNORECASE)
        # 清理多余标点和空格（去掉连续逗号、逗号+空格+逗号等）
        text = re.sub(r"[,，]\s*[,，]+", ",", text)
        text = re.sub(r"\s{2,}", " ", text).strip().strip(",").strip("，")
        return text

    def _estimate_duration(self, prompt):
        if not prompt:
            return 5.0
        word_count = len(prompt.split())
        if word_count < 15:
            return 3.0
        elif word_count < 25:
            return 5.0
        elif word_count < 40:
            return 6.0
        else:
            return 8.0

    def _apply_shot(self, index):
        if not hasattr(self, "_parsed_shots") or index >= len(self._parsed_shots):
            return
        shot = self._parsed_shots[index]
        self.bailian_prompt_input.delete("1.0", "end")
        if shot["prompt"]:
            self.bailian_prompt_input.insert("end", shot["prompt"])
        self.video_duration_var.set(str(int(shot["duration"])))
        self._bailian_log_msg(f"已加载镜头 {shot['num']}: {shot['prompt'][:50]}... | 时长 {shot['duration']}s")

    def _on_shot_selected(self, choice):
        labels = [s["label"] for s in self._parsed_shots] if hasattr(self, "_parsed_shots") else []
        idx = labels.index(choice) if choice in labels else 0
        self._apply_shot(idx)

    def _batch_generate_all_shots(self):
        if not hasattr(self, "_parsed_shots") or not self._parsed_shots:
            messagebox.showinfo("提示", "请先点击「从 Script 提取 Prompt」解析镜头。")
            return
        api_key = self.bailian_key_var.get().strip()
        if not api_key:
            messagebox.showwarning("提示", "请先填写百炼 API Key！")
            return
        # 智能归档旧文件
        archived = self._archive_old_files(("output_video", "output_audio"))
        if archived:
            self._bailian_log_msg(f"[归档] 已将 {archived} 个旧文件移入 archive_history")
        model = self.bailian_model_var.get()
        mode = self.bailian_mode_var.get()
        is_video = model in VIDEO_MODELS
        self.bailian_gen_btn.configure(state="disabled", text="批量生成中...")
        self._bailian_log_msg(f"开始批量生成 {len(self._parsed_shots)} 个镜头 (模式: {mode})")
        threading.Thread(target=self._batch_gen_worker, args=(api_key, model, is_video), daemon=True).start()

    def _batch_gen_worker(self, api_key, model, is_video):
        ok, fail = 0, 0
        # 需要媒体的模型（i2v/r2v/videoedit）必须提供参考图
        if is_video and model in (EDIT_MODELS + I2V_MODELS + R2V_MODELS):
            ref_path = self.ref_image_path_var.get().strip()
            if not ref_path or not os.path.exists(ref_path):
                self._bailian_log_msg(f"错误: 模型 {model} 需要参考素材！请在「参考图」中选择图片或视频。")
                self.safe_after( lambda: self.bailian_gen_btn.configure(state="normal", text="生成当前镜头"))
                return
        for i, shot in enumerate(self._parsed_shots):
            # 熔断检查 — 前一轮已触发则立即终止批量
            if BatchProcessor._bailian_circuit_open:
                self._bailian_log_msg(f"⚠️ 熔断已触发，中止剩余 {len(self._parsed_shots) - i} 个镜头")
                break
            prompt = shot["prompt"]
            if not prompt:
                self._bailian_log_msg(f"[镜头 {shot['num']}] 跳过：无 Prompt")
                fail += 1
                continue
            self._bailian_log_msg(f"[镜头 {shot['num']}] 生成中: {prompt[:40]}... (时长 {shot['duration']}s)")
            try:
                if is_video:
                    ref_path = self.ref_image_path_var.get().strip()
                    self._bailian_generate_video(api_key, model, prompt, ref_path, str(int(shot["duration"])))
                else:
                    self._bailian_generate_image(api_key, model, prompt)
                ok += 1
            except Exception as e:
                self._bailian_log_msg(f"[镜头 {shot['num']}] 失败: {e}")
                fail += 1
        self._bailian_log_msg(f"{'='*30} 批量完成: 成功 {ok}，失败 {fail}")
        self.safe_after( lambda: self.bailian_gen_btn.configure(state="normal", text="生成当前镜头"))

    def _save_bailian_config(self):
        self.config["bailian_api_key"] = self.bailian_key_var.get().strip()
        self.config["bailian_mode"] = self.bailian_mode_var.get()
        self.config["bailian_model"] = self.bailian_model_var.get()
        self.config["bailian_ratio"] = self.bailian_ratio_var.get()
        self.config["bailian_video_duration"] = self.video_duration_var.get()
        save_config(self.config)

    def toggle_bailian_key_vis(self):
        self.bailian_key_visible.set(not self.bailian_key_visible.get())
        self.bailian_key_entry.configure(show="" if self.bailian_key_visible.get() else "*")

    def _bailian_log_msg(self, msg):
        ts = time.strftime("%H:%M:%S")
        self.safe_after( lambda: self.global_log.append(f"[{ts}] {msg}"))

    def _clear_bailian_log(self):
        self.bailian_log.clear_all()

    def _open_bailian_output(self):
        out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bailian_output")
        if os.path.exists(out_dir):
            os.startfile(out_dir)
        else:
            self._bailian_log_msg("输出目录尚未创建，生成后会自动创建。")

    # ---------- 百炼熔断机制 ----------
    _bailian_circuit_open = False  # 类级别熔断标志

    def _bailian_check_response(self, resp):
        """检查百炼 API 响应，返回 (is_blocked, error_msg)
        is_blocked=True 表示触发熔断，调用方应立即中止。
        """
        code = resp.status_code
        body = resp.text.lower()

        # 429 限流 / 配额耗尽
        if code == 429:
            return True, "API 触发限流 (HTTP 429)，请稍后再试或更换 Key。"

        # 业务层配额耗尽（HTTP 200 但 body 里报错）
        quota_keywords = ["exceeded your current quota", "quota exceeded",
                          "insufficient balance", "insufficient_quota",
                          "balance is not enough", "余额不足", "配额不足",
                          "throttling", "rate limit"]
        if any(kw in body for kw in quota_keywords):
            return True, "百炼 API 免费算力已耗尽 / 余额不足，请更换 Key 或充值。"

        # 401/403 认证失败
        if code in (401, 403):
            return True, f"API Key 无效或已过期 (HTTP {code})，请检查百炼 Key。"

        return False, ""

    def _bailian_block(self, msg):
        """触发熔断：弹窗 + 日志 + 禁用按钮"""
        BatchProcessor._bailian_circuit_open = True
        logging.error("百炼熔断: %s", msg)
        self._bailian_log_msg(f"⚠️ 熔断: {msg}")
        self.safe_after(lambda: messagebox.showerror("算力熔断", msg))
        self.safe_after(lambda: self.bailian_gen_btn.configure(
            state="disabled", text="⛔ 算力已耗尽"))

    def start_bailian_generate(self):
        # 熔断检查 — 已触发则拒绝请求
        if BatchProcessor._bailian_circuit_open:
            messagebox.showwarning("熔断中", "百炼算力已耗尽，请更换 Key 或重启应用后重试。")
            return
        api_key = self.bailian_key_var.get().strip()
        model = self.bailian_model_var.get().strip()
        prompt = self.bailian_prompt_input.get("1.0", "end").strip()
        if not api_key:
            messagebox.showwarning("提示", "请先填写百炼 API Key！")
            return
        if not prompt:
            messagebox.showwarning("提示", "请输入 Prompt！")
            return
        self._save_bailian_config()
        self.bailian_gen_btn.configure(state="disabled", text="生成中...")
        if model in IMAGE_MODELS:
            threading.Thread(target=self._bailian_generate_image,
                             args=(api_key, model, prompt), daemon=True).start()
        else:
            ref_path = self.ref_image_path_var.get().strip()
            duration = self.video_duration_var.get().strip() or "5"
            threading.Thread(target=self._bailian_generate_video,
                             args=(api_key, model, prompt, ref_path, duration), daemon=True).start()

    def _bailian_generate_image(self, api_key, model, prompt):
        self._bailian_log_msg(f"调用图像生成，模型: {model}")
        try:
            ratio_info = self.ratio_map.get(self.bailian_ratio_var.get(), {})
            img_size = ratio_info.get("size", "1024*1024")
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

            if "qwen-image-2.0" in model:
                self._bailian_log_msg("使用 multimodal-generation 接口")
                payload = {"model": model, "input": {"messages": [{"role": "user", "content": [{"text": prompt}]}]},
                           "parameters": {"size": img_size}}
                resp = requests.post(f"{BAILIAN_BASE_URL}/services/aigc/multimodal-generation/generation",
                                     headers=headers, json=payload, timeout=120)
                # 熔断拦截
                blocked, msg = self._bailian_check_response(resp)
                if blocked:
                    self._bailian_block(msg)
                    return
                if resp.status_code == 200:
                    result = resp.json()
                    choices = result.get("output", {}).get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", [])
                        img_url = None
                        for item in content:
                            if isinstance(item, dict):
                                for key in ("image", "image_url", "url"):
                                    if key in item:
                                        img_url = item[key]; break
                            if img_url: break
                        if img_url:
                            self._bailian_log_msg("图片生成成功")
                            self._bailian_download_result(img_url, "image")
                        else:
                            self._bailian_log_msg(f"返回: {json.dumps(content, ensure_ascii=False)[:300]}")
                else:
                    self._bailian_log_msg(f"HTTP {resp.status_code}: {resp.text[:300]}")
                    raise RuntimeError(f"图像生成失败: HTTP {resp.status_code}")
            else:
                self._bailian_log_msg("使用 text2image 接口 (异步)")
                headers["X-DashScope-Async"] = "enable"
                payload = {"model": model, "input": {"prompt": prompt},
                           "parameters": {"n": 1, "size": img_size}}
                resp = requests.post(f"{BAILIAN_BASE_URL}/services/aigc/text2image/image-synthesis",
                                     headers=headers, json=payload, timeout=120)
                # 熔断拦截
                blocked, msg = self._bailian_check_response(resp)
                if blocked:
                    self._bailian_block(msg)
                    return
                if resp.status_code == 200:
                    task_id = resp.json().get("output", {}).get("task_id", "")
                    if task_id:
                        self._bailian_log_msg(f"任务已提交: {task_id}")
                        self._bailian_poll_task(api_key, task_id, "image")
                else:
                    self._bailian_log_msg(f"HTTP {resp.status_code}: {resp.text[:300]}")
                    raise RuntimeError(f"图像生成失败: HTTP {resp.status_code}")
        except Exception as e:
            self._bailian_log_msg(f"错误: {e}")
            raise
        finally:
            self.safe_after( lambda: self.bailian_gen_btn.configure(state="normal", text="生成当前镜头"))

    def _bailian_generate_video(self, api_key, model, prompt, ref_path, duration):
        self._bailian_log_msg(f"调用视频生成，模型: {model}")
        try:
            # 直接使用requests方式（更稳定）
            self._bailian_log_msg("使用 requests 提交")
            self._submit_video_via_requests(api_key, model, prompt, ref_path, duration)
        except Exception as e:
            self._bailian_log_msg(f"错误: {e}")
            raise
        finally:
            self.safe_after( lambda: self.bailian_gen_btn.configure(state="normal", text="生成当前镜头"))

    def _submit_video_via_requests(self, api_key, model, prompt, ref_path, duration):
        self._bailian_log_msg("通过 requests 提交视频任务...")
        ratio_info = self.ratio_map.get(self.bailian_ratio_var.get(), {})
        vid_w, vid_h = ratio_info.get("w", 1280), ratio_info.get("h", 720)

        # 统一处理时长
        dur = int(duration) if isinstance(duration, str) and duration.isdigit() else int(duration) if isinstance(duration, (int, float)) else 5

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
                   "X-DashScope-Async": "enable"}
        payload = {"model": model, "input": {"prompt": prompt},
                   "parameters": {"size": f"{vid_w}*{vid_h}", "duration": dur}}

        # 需要上传媒体的模型
        if model in (EDIT_MODELS + I2V_MODELS + R2V_MODELS):
            if not ref_path or not os.path.exists(ref_path):
                raise ValueError(f"模型 {model} 需要参考素材（图片/视频），请在「参考图」中选择文件。")
            oss_url = self._upload_to_bailian_oss(api_key, os.path.abspath(ref_path))
            if oss_url:
                # 根据模型类型设置media type
                if model in I2V_MODELS:
                    media_type = "first_frame"
                elif model in R2V_MODELS:
                    media_type = "first_clip"
                else:
                    media_type = "first_frame"
                payload["input"]["media"] = [{"type": media_type, "url": oss_url}]
                self._bailian_log_msg(f"媒体已上传: {oss_url[:50]}...")
            else:
                self._bailian_log_msg("错误: 媒体上传失败！")
                return

        resp = requests.post(f"{BAILIAN_BASE_URL}/services/aigc/video-generation/video-synthesis",
                             headers=headers, json=payload, timeout=120)
        # 熔断拦截
        blocked, msg = self._bailian_check_response(resp)
        if blocked:
            self._bailian_block(msg)
            return
        if resp.status_code == 200:
            task_id = resp.json().get("output", {}).get("task_id", "")
            if task_id:
                self._bailian_log_msg(f"任务已提交: {task_id}")
                self._bailian_poll_task(api_key, task_id, "video")
        else:
            self._bailian_log_msg(f"HTTP {resp.status_code}: {resp.text[:300]}")
            raise RuntimeError(f"视频生成失败: HTTP {resp.status_code}")

    def _to_data_uri(self, local_path):
        mime = "image/png"
        ext = os.path.splitext(local_path)[1].lower()
        mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                    ".webp": "image/webp", ".mp4": "video/mp4", ".avi": "video/avi"}
        mime = mime_map.get(ext, "application/octet-stream")
        with open(local_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f"data:{mime};base64,{b64}"

    def _upload_to_bailian_oss(self, api_key, local_path):
        self._bailian_log_msg(f"上传文件到 OSS: {os.path.basename(local_path)}")
        headers = {"Authorization": f"Bearer {api_key}"}
        for endpoint in [f"{BAILIAN_BASE_URL}/uploads",
                         "https://dashscope.aliyuncs.com/api/v1/uploads"]:
            try:
                with open(local_path, "rb") as f:
                    resp = requests.post(endpoint, headers=headers,
                                         files={"file": (os.path.basename(local_path), f)},
                                         data={"target": "model-service"}, timeout=120)
                if resp.status_code in (200, 201):
                    result = resp.json()
                    url = (result.get("data", {}).get("upload_url", "")
                           or result.get("output", {}).get("upload_url", "")
                           or result.get("upload_url", ""))
                    if url:
                        self._bailian_log_msg(f"OSS 上传成功")
                        return url
            except Exception:
                continue
        self._bailian_log_msg("OSS 上传失败，尝试 base64 内嵌")
        return self._to_data_uri(local_path)

    def _bailian_poll_task(self, api_key, task_id, task_type):
        headers = {"Authorization": f"Bearer {api_key}"}
        max_wait = 600
        elapsed = 0
        while elapsed < max_wait:
            _time.sleep(5)
            elapsed += 5
            try:
                resp = requests.get(f"{BAILIAN_BASE_URL}/tasks/{task_id}",
                                    headers=headers, timeout=30)
                # 熔断拦截 — 轮询接口也可能返回配额错误
                blocked, msg = self._bailian_check_response(resp)
                if blocked:
                    self._bailian_block(msg)
                    return
                if resp.status_code != 200:
                    continue
                result = resp.json()
                status = result.get("output", {}).get("task_status", "")
                self._bailian_log_msg(f"[{elapsed}s] 状态: {status}")
                if status == "SUCCEEDED":
                    url = self._extract_image_url(result.get("output", {}))
                    if url:
                        self._bailian_download_result(url, task_type)
                    else:
                        self._bailian_log_msg(f"任务完成但未找到 URL")
                    return
                elif status == "FAILED":
                    err = result.get("output", {}).get("message", "未知错误")
                    self._bailian_log_msg(f"任务失败: {err}")
                    # 检查失败原因是否是配额耗尽
                    err_lower = err.lower()
                    if any(kw in err_lower for kw in ["quota", "balance", "insufficient", "余额", "配额"]):
                        self._bailian_block(f"任务因算力不足失败: {err}")
                        return
                    raise RuntimeError(f"任务失败: {err}")
            except Exception:
                continue
        self._bailian_log_msg(f"超时: {max_wait} 秒")

    def _extract_image_url(self, output):
        for key in ("image_url", "output_video_url", "url", "video_url"):
            val = output.get(key, "")
            if val:
                return val
        if "results" in output:
            for r in output["results"]:
                if isinstance(r, dict) and "url" in r:
                    return r["url"]
        if "choices" in output:
            for c in output["choices"]:
                if isinstance(c, dict):
                    for item in c.get("message", {}).get("content", []):
                        if isinstance(item, dict):
                            for k in ("video_url", "image_url", "url"):
                                if k in item:
                                    return item[k]
        return ""

    def _bailian_download_result(self, url, task_type):
        self._bailian_log_msg(f"下载中...")
        ext = ".mp4" if task_type == "video" else ".png"

        # 使用用户配置的保存路径
        if task_type == "video":
            out_dir = self._get_output_dir("output_video")
        else:
            out_dir = self._get_output_dir("bailian_output")

        os.makedirs(out_dir, exist_ok=True)
        filename = f"bailian_{time.strftime('%Y%m%d_%H%M%S')}{ext}"
        out_path = os.path.join(out_dir, filename)
        try:
            dl = requests.get(url, timeout=120)
            if dl.status_code == 200:
                with open(out_path, "wb") as f:
                    f.write(dl.content)
                self._bailian_log_msg(f"已保存: {out_path}")
                self._add_to_tab2_list(out_path)
            else:
                self._bailian_log_msg(f"下载失败: HTTP {dl.status_code}")
        except Exception as e:
            self._bailian_log_msg(f"下载错误: {e}")

    def _add_to_tab2_list(self, file_path):
        if os.path.exists(file_path):
            name = os.path.basename(file_path)
            size = f"{os.path.getsize(file_path) / 1024:.1f} KB"
            # Note: Treeview not used in v6, just log
            self.log(f"已加入处理列表: {name} ({size})")

    # ==================== TTS ====================

    def _browse_tts_audio_dir(self):
        path = filedialog.askdirectory(title="选择音频保存目录")
        if path:
            self.tts_audio_dir_var.set(path)

    def _browse_sovits_bat(self):
        path = filedialog.askopenfilename(
            title="选择启动脚本",
            filetypes=[("批处理", "*.bat"), ("所有文件", "*.*")])
        if path:
            self.sovits_bat_var.set(path)

    def _browse_tts_ref_audio(self):
        path = filedialog.askopenfilename(
            title="选择参考音频 (用于声音复刻)",
            filetypes=[("音频文件", "*.wav *.mp3 *.flac *.m4a"), ("所有文件", "*.*")])
        if path:
            self.tts_ref_audio_var.set(path)

    def _tts_log_msg(self, msg):
        ts = time.strftime("%H:%M:%S")
        self.safe_after( lambda: self.global_log.append(f"[{ts}] {msg}"))

    def _clear_tts_log(self):
        self.tts_log.clear_all()

    def _open_audio_output(self):
        out_dir = self._get_tts_audio_dir()
        os.makedirs(out_dir, exist_ok=True)
        os.startfile(out_dir)

    def _get_tts_audio_dir(self):
        """获取 TTS 音频输出目录，优先使用用户自选的目录"""
        custom = self.tts_audio_dir_var.get().strip()
        if custom and os.path.isdir(custom):
            return custom
        return self._get_output_dir("output_audio")

    def _extract_dialogue(self):
        content = self.script_output.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo("提示", "Script 页面中没有脚本内容。")
            return
        import re
        # 全量抓取：搜索所有 台词/旁白/中文台词 后面的中文文本
        dialogue_pattern = re.compile(
            r"(?:台词|旁白|中文台词|对白|独白|配音文本)\s*\*{0,2}\s*[:：]\s*(.+)",
            re.IGNORECASE,
        )
        # 同时兼容 画面描述: xxx 作为备选
        visual_pattern = re.compile(
            r"(?:画面描述|Visual Description)\s*[:：]\s*(.+)",
            re.IGNORECASE,
        )
        dialogue_lines = []
        for line in content.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            dm = dialogue_pattern.search(stripped)
            if dm:
                text = dm.group(1).strip()
                # 清理 Markdown 标记
                text = re.sub(r"\*+", "", text).strip()
                if text:
                    dialogue_lines.append(text)
                continue
            vm = visual_pattern.search(stripped)
            if vm:
                text = vm.group(1).strip()
                text = re.sub(r"\*+", "", text).strip()
                if text:
                    dialogue_lines.append(text)

        if dialogue_lines:
            self.tts_text.delete("1.0", "end")
            self.tts_text.insert("end", "\n".join(dialogue_lines))
            self._tts_log_msg(f"提取到 {len(dialogue_lines)} 条台词/旁白")
        else:
            messagebox.showinfo("提示", "未从脚本中提取到台词/旁白。\n请确保脚本中有「台词：」或「旁白：」关键词。")

    def _save_tts_config(self):
        self.config["tts_engine"] = self.tts_engine_var.get()
        self.config["tts_adv_mode"] = self.tts_adv_mode_var.get()
        voice_display = self.tts_voice_var.get()
        self.config["tts_voice"] = self.tts_voice_map.get(voice_display, "sambert-zhichu-v1")
        self.config["tts_custom_model"] = self.tts_custom_model_var.get().strip()
        self.config["tts_ref_audio"] = self.tts_ref_audio_var.get().strip()
        self.config["tts_prompt_text"] = self.tts_prompt_text_var.get().strip()
        self.config["sovits_url"] = self.sovits_url_var.get().strip()
        self.config["sovits_bat_path"] = self.sovits_bat_var.get().strip()
        self.config["sovits_character"] = self.sovits_character_var.get().strip()
        self.config["sovits_emotion"] = self.sovits_emotion_var.get().strip()
        self.config["mimo_api_key"] = self.mimo_api_key_var.get().strip()
        mimo_model_display = self.mimo_model_var.get().strip()
        if " (" in mimo_model_display:
            mimo_model_display = mimo_model_display.split(" (")[0]
        self.config["mimo_model"] = mimo_model_display
        self.config["mimo_voice"] = self.mimo_voice_var.get().strip()
        save_config(self.config)

    def start_tts_generate(self):
        text_content = self.tts_text.get("1.0", "end").strip()
        if not text_content:
            messagebox.showwarning("提示", "台词区域为空，请先提取或手动输入台词！")
            return
        self._save_tts_config()
        lines = [l.strip() for l in text_content.split("\n") if l.strip()]
        if not lines:
            messagebox.showwarning("提示", "没有有效的台词行！")
            return
        # 智能归档旧音频
        archived = self._archive_old_files(("output_audio",))
        if archived:
            self._tts_log_msg(f"[归档] 已将 {archived} 个旧音频移入 archive_history")
        self.tts_gen_btn.configure(state="disabled", text="生成中...")
        engine = self.tts_engine_var.get()
        if engine == "bailian":
            threading.Thread(target=self._tts_generate_bailian, args=(lines,), daemon=True).start()
        elif engine == "mimo":
            threading.Thread(target=self._tts_generate_mimo, args=(lines,), daemon=True).start()
        else:
            threading.Thread(target=self._tts_generate_sovits, args=(lines,), daemon=True).start()

    def _extract_audio_data(self, response):
        """从 DashScope response 中提取音频二进制，不调用 get_audio_data() 避免 begin_time 崩溃"""
        AUDIO_KEYS = ("audio", "audio_url", "url", "speech", "audio_data")

        def _pick_audio_from_dict(d):
            for key in AUDIO_KEYS:
                val = d.get(key)
                if val:
                    return val
            return None

        def _resolve(val):
            if isinstance(val, str) and val.startswith("http"):
                return requests.get(val, timeout=30).content
            if isinstance(val, (bytes, bytearray)):
                return val
            if isinstance(val, str):
                try:
                    import base64 as _b64
                    decoded = _b64.b64decode(val)
                    if len(decoded) > 100:
                        return decoded
                except Exception:
                    pass
            return val if isinstance(val, (bytes, bytearray)) else None

        # 直接解析 output 属性（跳过 get_audio_data）
        try:
            output = getattr(response, "output", None)
            if output and isinstance(output, dict):
                # 标准格式
                val = _pick_audio_from_dict(output)
                if val:
                    return _resolve(val)
                # 嵌套 results/choices
                for key in ("results", "choices"):
                    items = output.get(key)
                    if items and isinstance(items, list):
                        for item in items:
                            if isinstance(item, dict):
                                val = _pick_audio_from_dict(item)
                                if val:
                                    return _resolve(val)
        except Exception:
            pass

        # response 本身就是 dict
        try:
            if isinstance(response, dict):
                output = response.get("output", {})
                if isinstance(output, dict):
                    val = _pick_audio_from_dict(output)
                    if val:
                        return _resolve(val)
                val = _pick_audio_from_dict(response)
                if val:
                    return _resolve(val)
                data = response.get("data")
                if isinstance(data, (bytes, bytearray)):
                    return data
        except Exception:
            pass

        return None

    def _pcm_to_wav(self, pcm_data, out_path, sample_rate=24000, channels=1, sample_width=2):
        import wave
        with wave.open(out_path, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_data)

    def _tts_generate_bailian(self, lines):
        try:
            from dashscope.audio.tts import SpeechSynthesizer
        except ImportError:
            self._tts_log_msg("错误: dashscope 未安装！请 pip install dashscope")
            self.safe_after( lambda: self.tts_gen_btn.configure(state="normal", text="一键批量生成音频"))
            return
        import dashscope
        dashscope.api_key = self.config.get("bailian_api_key", "")
        if not dashscope.api_key:
            self._tts_log_msg("错误: 请先配置百炼 API Key！")
            self.safe_after( lambda: self.tts_gen_btn.configure(state="normal", text="一键批量生成音频"))
            return

        voice_display = self.tts_voice_var.get()
        voice_id = self.tts_voice_map.get(voice_display, "longcheng")
        custom_model = self.tts_custom_model_var.get().strip()

        adv_mode = self.tts_adv_mode_var.get()

        if custom_model:
            model = custom_model
            voice = None
        else:
            # 声音复刻需要 cosyvoice-v2，预设音色用 cosyvoice-v1
            if adv_mode == "clone":
                model = "cosyvoice-v2"
            else:
                model = "cosyvoice-v1"
            voice = voice_id

        # ---- 模式隔离：严格防冲突 ----
        adv_mode = self.tts_adv_mode_var.get()
        prompt_audio_url = None
        use_clone = False

        if adv_mode == "clone":
            # 模式B：声音复刻 — 强制忽略情感指令
            ref_audio_path = self.tts_ref_audio_var.get().strip()
            prompt_text = ""
            if ref_audio_path and os.path.isfile(ref_audio_path):
                self._tts_log_msg(f"[声音复刻] 上传参考音频: {os.path.basename(ref_audio_path)}")
                try:
                    upload_resp = dashscope.Files.upload(file_path=os.path.abspath(ref_audio_path))
                    uploaded = upload_resp.output.get("uploaded_files", [])
                    if uploaded:
                        prompt_audio_url = uploaded[0].get("file_id", "")
                        use_clone = True
                        self._tts_log_msg(f"[声音复刻] 上传成功，file_id={prompt_audio_url}")
                    else:
                        failed = upload_resp.output.get("failed_uploads", [])
                        self._tts_log_msg(f"[声音复刻] 上传失败: {failed}")
                except Exception as e:
                    self._tts_log_msg(f"[声音复刻] 上传异常: {type(e).__name__}: {e}")
            else:
                self._tts_log_msg(f"[声音复刻] 未选择参考音频或文件不存在，回退到预设音色")
        else:
            # 模式A：预设音色+情感指令 — 强制忽略参考音频
            ref_audio_path = ""
            prompt_text = self.tts_prompt_text_var.get().strip()
            if prompt_text:
                self._tts_log_msg(f"[情感指令] {prompt_text}")

        out_dir = self._get_tts_audio_dir()
        os.makedirs(out_dir, exist_ok=True)
        mode_desc = "零样本复刻" if use_clone else "预设音色+情感指令"
        self._tts_log_msg(f"TTS 模型: {model} | 音色: {voice or '自定义'} | 模式: {mode_desc}")
        self._tts_log_msg(f"音频保存至: {out_dir}")
        self._tts_log_msg(f"开始批量生成，共 {len(lines)} 条台词")

        success, fail = 0, 0
        for i, line in enumerate(lines, 1):
            text = line
            for pp in ["Shot ", "SHOT ", "shot "]:
                if text.startswith(pp):
                    sep = text.find("：")
                    if sep == -1: sep = text.find(":")
                    if sep != -1: text = text[sep + 1:].strip()
                    break
            if not text:
                self._tts_log_msg(f"[{i}/{len(lines)}] 跳过空行"); continue

            final_text = f"{prompt_text}：{text}" if prompt_text else text
            self._tts_log_msg(f"[{i}/{len(lines)}] 生成中: {text[:30]}...")

            audio_data = None
            used_sample_rate = 24000
            last_error = None
            for sample_rate in [24000, 48000, 16000]:
                try:
                    kwargs = {"model": model, "text": final_text, "sample_rate": sample_rate}
                    if use_clone and prompt_audio_url:
                        kwargs["prompt_audio"] = prompt_audio_url
                    elif voice:
                        kwargs["voice"] = voice
                    kwargs = {k: v for k, v in kwargs.items() if v not in (None, "", 0)}
                    response = SpeechSynthesizer.call(**kwargs)
                    audio_data = self._extract_audio_data(response)
                    if audio_data:
                        used_sample_rate = sample_rate
                        break
                    resp_dump = ""
                    try:
                        if hasattr(response, "output"):
                            resp_dump = str(response.output)
                        elif hasattr(response, "get_response"):
                            resp_dump = str(response.get_response())
                        elif isinstance(response, dict):
                            resp_dump = json.dumps(response, ensure_ascii=False)
                        else:
                            resp_dump = str(response)
                    except Exception:
                        resp_dump = repr(response)
                    last_error = f"DashScope返回无音频 (rate={sample_rate}): {resp_dump[:500]}"
                except Exception as e:
                    err_parts = [f"{type(e).__name__}: {e}"]
                    if hasattr(e, "message") and e.message:
                        err_parts.append(f"message={e.message}")
                    if hasattr(e, "code") and e.code:
                        err_parts.append(f"code={e.code}")
                    if isinstance(e, KeyError):
                        err_parts.append(f"missing_key={repr(e.args[0]) if e.args else '?'}")
                    last_error = " | ".join(err_parts)
                    # TTS 熔断：检查配额耗尽
                    err_lower = last_error.lower()
                    if any(kw in err_lower for kw in ["quota", "balance", "insufficient", "429", "rate limit", "余额", "配额"]):
                        self._bailian_block(f"TTS 算力不足: {last_error[:200]}")
                        return
                    continue
            if audio_data:
                # 文件名：复刻模式用参考音频名，预设模式用音色名
                if use_clone and ref_audio_path:
                    name_tag = os.path.splitext(os.path.basename(ref_audio_path))[0]
                else:
                    name_tag = voice_display.split(" ")[0] if voice_display else "自定义"
                fname = self._tts_audio_name(i, name_tag, text)
                out_path = os.path.join(out_dir, fname)
                raw_bytes = base64.b64decode(audio_data) if isinstance(audio_data, str) else audio_data
                if raw_bytes[:4] == b'RIFF':
                    with open(out_path, "wb") as f:
                        f.write(raw_bytes)
                else:
                    self._pcm_to_wav(raw_bytes, out_path, sample_rate=used_sample_rate, channels=1, sample_width=2)
                self._tts_log_msg(f"[{i}/{len(lines)}] 已保存: {fname}")
                success += 1
            else:
                self._tts_log_msg(f"[{i}/{len(lines)}] 生成失败: {last_error}")
                fail += 1
            time.sleep(0.3)

        self._tts_log_msg("=" * 40)
        self._tts_log_msg(f"完成: 成功 {success}，失败 {fail}")
        self._tts_log_msg(f"音频保存至: {out_dir}")
        self.safe_after( lambda: self.tts_gen_btn.configure(state="normal", text="一键批量生成音频"))
        if success > 0:
            messagebox.showinfo("完成", f"音频生成完成！\n成功: {success}\n保存至: {out_dir}")

    def _tts_generate_sovits(self, lines):
        import subprocess
        api_url = self.sovits_url_var.get().strip().rstrip("/")
        if not api_url:
            self._tts_log_msg("错误: 请填写 VibeVoice API 地址！")
            self.safe_after( lambda: self.tts_gen_btn.configure(state="normal", text="一键批量生成音频"))
            return

        character = self.sovits_character_var.get().strip()
        emotion = self.sovits_emotion_var.get().strip()
        if not character:
            self._tts_log_msg("错误: 请填写角色名称！")
            self.safe_after( lambda: self.tts_gen_btn.configure(state="normal", text="一键批量生成音频"))
            return

        out_dir = self._get_tts_audio_dir()
        os.makedirs(out_dir, exist_ok=True)
        self._tts_log_msg(f"音频保存至: {out_dir}")
        prefix = self._get_project_prefix()
        synth_url = f"{api_url}/api/synthesize"

        # 自动检测 + 拉起
        if not self._check_sovits_status(api_url):
            self._tts_log_msg("[自动化] VibeVoice 未运行，正在拉起...")
            bat_path = self.sovits_bat_var.get().strip()
            if bat_path and os.path.exists(bat_path):
                try:
                    subprocess.Popen(["cmd", "/c", bat_path],
                                     creationflags=subprocess.CREATE_NEW_CONSOLE)
                    self._tts_log_msg(f"[自动化] 已执行: {bat_path}")
                except Exception as e:
                    self._tts_log_msg(f"[自动化] 启动失败: {e}")
                    self.safe_after( lambda: self.tts_gen_btn.configure(state="normal", text="一键批量生成音频"))
                    return
            else:
                self._tts_log_msg(f"[自动化] 未找到脚本: {bat_path}")
                self.safe_after( lambda: self.tts_gen_btn.configure(state="normal", text="一键批量生成音频"))
                return

            self._tts_log_msg("[自动化] 等待引擎启动（每 2 秒检测，最多 60 秒）...")
            for elapsed in range(2, 62, 2):
                _time.sleep(2)
                if self._check_sovits_status(api_url):
                    self._tts_log_msg(f"[自动化] 引擎唤醒成功！（耗时 {elapsed} 秒）")
                    break
                self._tts_log_msg(f"[自动化] 等待中... ({elapsed}/60s)")
            else:
                self._tts_log_msg("[自动化] 超时：60 秒内引擎未响应")
                self.safe_after( lambda: self.tts_gen_btn.configure(state="normal", text="一键批量生成音频"))
                return
        else:
            self._tts_log_msg("[自动化] VibeVoice 已在线")

        # ---- 模式隔离：严格防冲突 ----
        adv_mode = self.tts_adv_mode_var.get()
        if adv_mode == "clone":
            ref_audio_path = self.tts_ref_audio_var.get().strip()
            prompt_text = ""
            has_ref = ref_audio_path and os.path.isfile(ref_audio_path)
            if has_ref:
                self._tts_log_msg(f"[声音复刻] 参考音频: {os.path.basename(ref_audio_path)}")
            else:
                self._tts_log_msg(f"[声音复刻] 未选择参考音频或文件不存在")
        else:
            ref_audio_path = ""
            prompt_text = self.tts_prompt_text_var.get().strip()
            has_ref = False
            if prompt_text:
                self._tts_log_msg(f"[情感指令] {prompt_text}")

        self._tts_log_msg(f"角色: {character} | 情绪: {emotion or '默认'}")
        char_id = self._char_name_to_id.get(character, character)
        self._tts_log_msg(f"character_id: {char_id}")
        self._tts_log_msg(f"开始批量生成，共 {len(lines)} 条台词")

        success, fail = 0, 0
        for i, line in enumerate(lines, 1):
            text = line
            for pp in ["Shot ", "SHOT ", "shot "]:
                if text.startswith(pp):
                    sep = text.find("：")
                    if sep == -1: sep = text.find(":")
                    if sep != -1: text = text[sep + 1:].strip()
                    break
            if not text:
                self._tts_log_msg(f"[{i}/{len(lines)}] 跳过空行"); continue

            final_text = f"{prompt_text}：{text}" if prompt_text else text
            self._tts_log_msg(f"[{i}/{len(lines)}] 生成中: {text[:30]}...")

            character_id = self._char_name_to_id.get(character, character)
            params = {"character_id": character_id, "text": final_text, "emotion": emotion or "平静",
                      "top_k": 5, "top_p": 0.9, "temperature": 0.75, "text_split_method": "cut5"}
            if has_ref:
                params["ref_audio_path"] = ref_audio_path
            try:
                resp = requests.post(synth_url, json=params, timeout=120)
                if resp.status_code == 200 and resp.content:
                    # 文件名：复刻模式用参考音频名
                    if has_ref and ref_audio_path:
                        name_tag = os.path.splitext(os.path.basename(ref_audio_path))[0]
                    else:
                        name_tag = character
                    fname = self._tts_audio_name(i, name_tag, text)
                    out_path = os.path.join(out_dir, fname)
                    with open(out_path, "wb") as f:
                        f.write(resp.content)
                    self._tts_log_msg(f"[{i}/{len(lines)}] 已保存: {fname}")
                    success += 1
                else:
                    try:
                        err = resp.json().get("detail", resp.text[:200])
                    except Exception:
                        err = resp.text[:200]
                    self._tts_log_msg(f"[{i}/{len(lines)}] HTTP {resp.status_code}: {err}")
                    fail += 1
            except requests.exceptions.ConnectionError:
                self._tts_log_msg(f"[{i}/{len(lines)}] 连接中断，重新拉起...")
                bat_path = self.sovits_bat_var.get().strip()
                if bat_path and os.path.exists(bat_path):
                    subprocess.Popen(["cmd", "/c", bat_path],
                                     creationflags=subprocess.CREATE_NEW_CONSOLE)
                    _time.sleep(10)
                    if self._check_sovits_status(api_url):
                        try:
                            resp2 = requests.post(synth_url, json=params, timeout=120)
                            if resp2.status_code == 200 and resp2.content:
                                if has_ref and ref_audio_path:
                                    name_tag = os.path.splitext(os.path.basename(ref_audio_path))[0]
                                else:
                                    name_tag = character
                                fname = self._tts_audio_name(i, name_tag, text)
                                out_path = os.path.join(out_dir, fname)
                                with open(out_path, "wb") as f:
                                    f.write(resp2.content)
                                self._tts_log_msg(f"[{i}/{len(lines)}] 重试成功")
                                success += 1; continue
                        except Exception:
                            pass
                self._tts_log_msg(f"[{i}/{len(lines)}] 重试失败")
                fail += 1
            except Exception as e:
                self._tts_log_msg(f"[{i}/{len(lines)}] 失败: {e}")
                fail += 1
            _time.sleep(0.3)

        self._tts_log_msg("=" * 40)
        self._tts_log_msg(f"完成: 成功 {success}，失败 {fail}")
        self._tts_log_msg(f"音频保存至: {out_dir}")
        self.safe_after( lambda: self.tts_gen_btn.configure(state="normal", text="一键批量生成音频"))
        if success > 0:
            messagebox.showinfo("完成", f"音频生成完成！\n成功: {success}\n保存至: {out_dir}")

    def _tts_generate_mimo(self, lines):
        """小米 MiMo TTS 生成 - 兼容 OpenAI 接口"""
        api_key = self.config.get("mimo_api_key", "").strip()
        if not api_key:
            self._tts_log_msg("错误: 请先配置小米 MiMo API Key！")
            self.safe_after( lambda: self.tts_gen_btn.configure(state="normal", text="一键批量生成音频"))
            return
        
        # 解析模型名称（API 要求全小写）
        mimo_model_display = self.mimo_model_var.get().strip()
        if " (" in mimo_model_display:
            model = mimo_model_display.split(" (")[0]
        else:
            model = mimo_model_display
        model = model.lower()  # API 要求全小写 model ID

        # 使用配置中的Base URL
        base_url = self.config.get("api_base_url", "https://token-plan-cn.xiaomimimo.com/anthropic").strip()
        if "/anthropic" in base_url:
            base_url = base_url.replace("/anthropic", "/v1")
        elif not base_url.endswith("/v1"):
            base_url = base_url.rstrip("/") + "/v1"

        out_dir = self._get_tts_audio_dir()
        os.makedirs(out_dir, exist_ok=True)
        self._tts_log_msg(f"音频保存至: {out_dir}")

        # 模式隔离
        adv_mode = self.tts_adv_mode_var.get()
        prompt_text = ""
        ref_audio_path = ""
        
        if adv_mode == "clone":
            ref_audio_path = self.tts_ref_audio_var.get().strip()
            if ref_audio_path and os.path.isfile(ref_audio_path):
                self._tts_log_msg(f"[声音复刻] 参考音频: {os.path.basename(ref_audio_path)}")
            else:
                self._tts_log_msg(f"[声音复刻] 未选择参考音频或文件不存在，使用标准模式")
                ref_audio_path = ""
        else:
            prompt_text = self.tts_prompt_text_var.get().strip()
            if prompt_text:
                self._tts_log_msg(f"[情感指令] {prompt_text}")
        
        mode_desc = "声音复刻" if ref_audio_path else "标准模式+情感指令"
        self._tts_log_msg(f"MiMo 模型: {model} | 模式: {mode_desc}")
        # 提前检查：复刻模式需要 VoiceClone 模型
        if ref_audio_path and "voiceclone" not in model and "voicedesign" not in model:
            self._tts_log_msg(f"[警告] 声音复刻需要选择 VoiceClone 或 VoiceDesign 模型！当前模型 '{model}' 不支持复刻。")
        self._tts_log_msg(f"开始批量生成，共 {len(lines)} 条台词")
        
        success, fail = 0, 0
        
        for i, line in enumerate(lines, 1):
            text = line
            # 清理 "Shot X:" 前缀
            for pp in ["Shot ", "SHOT ", "shot "]:
                if text.startswith(pp):
                    sep = text.find("：")
                    if sep == -1: sep = text.find(":")
                    if sep != -1: text = text[sep + 1:].strip()
                    break
            
            if not text:
                self._tts_log_msg(f"[{i}/{len(lines)}] 跳过空行")
                continue

            self._tts_log_msg(f"[{i}/{len(lines)}] 生成中: {text[:30]}...")

            try:
                # 构建请求头
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json; charset=utf-8",
                }

                # 解析预设音色 ID - 使用映射表获取正确的API音色ID（修复"出来的是男生"问题）
                voice_display = self.mimo_voice_var.get().strip()
                voice_id = self.mimo_voice_id_map.get(voice_display, "bingtang")

                # 构建 messages：VoiceDesign 模式需要特殊处理（修复"HTTP 400: Param Incorrect"和音色生成错误）
                messages = []
                
                if "voicedesign" in model:
                    # VoiceDesign 模式：音色信息嵌入到 user 消息中（解决音色显示错误和HTTP 400问题）
                    voice_desc_map = {
                        "bingtang": "冰糖的清甜女声",
                        "mohuali": "茉莉的温柔女声",
                        "sudahuoli": "苏打的活力女声",
                        "baihuashenzhu": "白桦的沉稳女声",
                        "mia": "Mia的英文女声",
                        "chloe": "Chloe的英文女声",
                        "milo": "Milo的英文男声",
                        "dean": "Dean的英文男声",
                        "mimo_default": "默认音色",
                    }
                    voice_desc = voice_desc_map.get(voice_id, voice_id)
                    user_content = f"使用{voice_desc}读这段话："
                    if prompt_text:
                        user_content += f"\n\n语气：{prompt_text}\n\n"
                    else:
                        user_content += "\n\n"
                    user_content += text
                    messages.append({"role": "user", "content": user_content})
                else:
                    # 标准TTS模式：情感指令放user，台词放assistant
                    messages.append({"role": "user", "content": prompt_text if prompt_text else ""})
                    messages.append({"role": "assistant", "content": text})

                payload = {
                    "model": model,
                    "messages": messages,
                    "response_format": "audio",
                    "stream": False,
                }

                # 声音复刻：将参考音频转为 DataURL 放入 audio.voice（仅限标准模型）
                if ref_audio_path and os.path.isfile(ref_audio_path):
                    if "voiceclone" in model:
                        with open(ref_audio_path, "rb") as f:
                            ref_audio_b64 = base64.b64encode(f.read()).decode()
                        mime = mimetypes.guess_type(ref_audio_path)[0] or "audio/wav"
                        payload["audio"] = {"voice": f"data:{mime};base64,{ref_audio_b64}"}
                    else:
                        # 其他模型不支持复刻
                        self._tts_log_msg(f"[警告] 当前模型 '{model}' 不支持声音复刻！请切换到 VoiceClone 模型。")
                        if "voicedesign" not in model:
                            payload["audio"] = {"voice": voice_id}
                else:
                    # 无参考音频，使用预设音色（仅限标准TTS模型）
                    if "voicedesign" not in model:
                        payload["audio"] = {"voice": voice_id}

                # 发送请求到 MiMo API（手动 UTF-8 编码，确保中文音色名正确传递）
                resp = requests.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                    timeout=180
                )

                if resp.status_code == 200:
                    # 文件名：复刻模式用参考音频名，预设模式用音色名
                    if ref_audio_path and os.path.isfile(ref_audio_path):
                        name_tag = os.path.splitext(os.path.basename(ref_audio_path))[0]
                    else:
                        name_tag = voice_id
                    fname = self._tts_audio_name(i, name_tag, text)
                    out_path = os.path.join(out_dir, fname)

                    # 解析 JSON 响应，提取 base64 音频
                    result = resp.json()
                    audio_b64 = (result.get("choices", [{}])[0]
                                 .get("message", {}).get("audio", {}).get("data", ""))
                    if audio_b64:
                        audio_bytes = base64.b64decode(audio_b64)
                        with open(out_path, "wb") as f:
                            f.write(audio_bytes)
                        self._tts_log_msg(f"[{i}/{len(lines)}] 已保存: {fname} ({len(audio_bytes)} bytes)")
                        success += 1
                    else:
                        self._tts_log_msg(f"[{i}/{len(lines)}] 响应中无音频数据")
                        fail += 1
                else:
                    # 详细错误日志
                    try:
                        err = resp.json().get("error", {}).get("message", resp.text[:300])
                    except Exception:
                        err = resp.text[:300]
                    self._tts_log_msg(f"[{i}/{len(lines)}] HTTP {resp.status_code}: {err}")
                    fail += 1
                    
            except requests.exceptions.Timeout:
                self._tts_log_msg(f"[{i}/{len(lines)}] 超时: 请求未在120秒内完成")
                fail += 1
            except requests.exceptions.ConnectionError as e:
                self._tts_log_msg(f"[{i}/{len(lines)}] 连接错误: {e}")
                fail += 1
            except Exception as e:
                self._tts_log_msg(f"[{i}/{len(lines)}] 失败: {type(e).__name__}: {e}")
                fail += 1
            
            _time.sleep(0.3)
        
        self._tts_log_msg("=" * 40)
        self._tts_log_msg(f"完成: 成功 {success}，失败 {fail}")
        self._tts_log_msg(f"音频保存至: {out_dir}")
        self.safe_after( lambda: self.tts_gen_btn.configure(state="normal", text="一键批量生成音频"))
        if success > 0:
            messagebox.showinfo("完成", f"音频生成完成！\n成功: {success}\n保存至: {out_dir}")

    # ==================== Script 生成 ====================

    def start_generate_script(self):
        idea = self.story_input.get("1.0", "end").strip()
        if not idea or idea.startswith("例："):
            messagebox.showwarning("提示", "请先输入故事创意或剧情大纲！")
            return
        self.generate_btn.configure(state="disabled", text="生成中...")
        self.script_output.delete("1.0", "end")
        self.script_output.insert("end", "正在调用 AI 生成镜头脚本，请稍候...\n")
        threading.Thread(target=self.generate_script, args=(idea,), daemon=True).start()

    def generate_script(self, idea):
        # 使用 MiMo API Key（与视觉引擎、TTS 统一）
        api_key = self.config.get("mimo_api_key", "").strip()
        if not api_key:
            api_key = self.api_key_var.get().strip()
        base_url = self.config.get("api_base_url", "https://token-plan-cn.xiaomimimo.com/anthropic").strip().rstrip("/")
        model = self.config.get("api_model", "mimo-v2.5-pro").strip()
        if not base_url or not api_key:
            self._script_error("错误：请先在「全局设置」中配置 Base URL 和 API Key。")
            return
        # MiMo 网关使用 OpenAI 兼容格式
        if "/anthropic" in base_url:
            base_url = base_url.replace("/anthropic", "/v1")
        elif not base_url.endswith("/v1"):
            base_url = base_url.rstrip("/") + "/v1"
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json; charset=utf-8",
            }
            url = f"{base_url}/chat/completions"
            payload = {
                "model": model, "temperature": 0.8, "max_tokens": 1000000,
                "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                              {"role": "user", "content": idea}]
            }

            self._update_script_text("正在请求 API...\n")
            response = requests.post(url, headers=headers, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), timeout=120)
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                lines = content.split("\n")
                processed = []
                for line in lines:
                    processed.append(line)
                    stripped = line.strip()
                    if stripped.startswith("英文Prompt") or stripped.startswith("English Prompt"):
                        if VISUAL_SUFFIX.split(",")[0] not in stripped:
                            base = line.rstrip()
                            sep = ", " if base and not base.endswith(",") else " "
                            processed[-1] = base + sep + VISUAL_SUFFIX
                self._update_script_text("\n".join(processed))
            else:
                err = f"API 错误: HTTP {response.status_code}\n{response.text[:500]}"
                self._update_script_text(err)
        except requests.exceptions.Timeout:
            self._script_error("错误：请求超时（120秒）")
        except requests.exceptions.ConnectionError:
            self._script_error("错误：无法连接到 API 服务器")
        except Exception as e:
            self._script_error(f"错误：{e}")
        finally:
            self.safe_after( lambda: self.generate_btn.configure(state="normal", text="生成动态镜头脚本"))

    def _update_script_text(self, text):
        self.safe_after( lambda: (self.script_output.delete("1.0", "end"),
                                     self.script_output.insert("end", text)))

    def _script_error(self, msg):
        self._update_script_text(msg)

    def export_script(self):
        content = self.script_output.get("1.0", "end").strip()
        if not content:
            messagebox.showwarning("提示", "没有可导出的脚本内容！"); return
        path = filedialog.asksaveasfilename(title="导出脚本", defaultextension=".txt",
                                             filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
                                             initialfile="镜头脚本.txt")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("完成", f"脚本已保存至:\n{path}")

    def copy_script(self):
        content = self.script_output.get("1.0", "end").strip()
        if not content:
            messagebox.showwarning("提示", "没有可复制的脚本内容！"); return
        self.root.clipboard_clear()
        self.root.clipboard_append(content)

    # ==================== Tab 2: 图像处理 ====================

    def log(self, msg):
        ts = time.strftime("%H:%M:%S")
        # v6: log to console since we don't have a dedicated log box in the new layout
        print(f"[{ts}] {msg}")

    def select_images(self):
        files = filedialog.askopenfilenames(
            title="选择图片文件",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"), ("所有文件", "*.*")])
        if files:
            self.selected_files.extend(files)
            self.log(f"已添加 {len(files)} 个文件")
            self.file_count_label.configure(text=f"已选: {len(self.selected_files)} 张")
            # 九宫格模式下自动加载第一张图到预览
            if self.mode_var.get() == "nine_grid" and files:
                self._ng_load_preview_image(files[0])

    def clear_list(self):
        self.selected_files = []
        self.log("已清空文件列表")
        self.file_count_label.configure(text="已选: 0 张")

    def open_output_dir(self):
        if self.output_dir and os.path.exists(self.output_dir):
            os.startfile(self.output_dir)

    def start_processing(self):
        if not self.selected_files:
            messagebox.showwarning("警告", "请先选择要处理的图片！"); return
        self.output_dir = filedialog.askdirectory(title="选择输出目录")
        if not self.output_dir: return
        self.config["image_width"] = self.width_var.get()
        self.config["image_height"] = self.height_var.get()
        save_config(self.config)
        mode = self.mode_var.get()
        if mode == "resize":
            try:
                out_w, out_h = int(self.width_var.get()), int(self.height_var.get())
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数字！"); return
            self.log(f"开始调整尺寸，共 {len(self.selected_files)} 张，目标 {out_w}x{out_h}")
            threading.Thread(target=self.process_batch_resize, args=(out_w, out_h), daemon=True).start()
        else:
            self.log(f"开始九宫格切分，共 {len(self.selected_files)} 张")
            threading.Thread(target=self.split_to_nine_grid, daemon=True).start()

    def process_batch_resize(self, out_w, out_h):
        ok, fail = 0, 0
        for i, src in enumerate(self.selected_files, 1):
            try:
                fn = os.path.basename(src)
                name, ext = os.path.splitext(fn)
                dst = os.path.join(self.output_dir, f"{name}_{out_w}x{out_h}_processed{ext}")
                with Image.open(src) as img:
                    img.resize((out_w, out_h), Image.LANCZOS).save(dst)
                ok += 1
            except Exception as e:
                self.log(f"[{i}] FAIL {fn} - {e}"); fail += 1
        self.log(f"调整尺寸完成: 成功 {ok}，失败 {fail}")
        if ok:
            messagebox.showinfo("完成", f"处理完成!\n成功: {ok} 个\n失败: {fail} 个")

    def split_to_nine_grid(self):
        ok, fail = 0, 0
        # 使用可视化预览中调整的参考线位置
        col_lines = list(self.ng_col_lines)
        row_lines = list(self.ng_row_lines)
        self.log(f"使用参考线位置: 列=[{col_lines[0]:.3f}, {col_lines[1]:.3f}] 行=[{row_lines[0]:.3f}, {row_lines[1]:.3f}]")
        for idx, src in enumerate(self.selected_files, 1):
            try:
                fn = os.path.basename(src)
                name, _ = os.path.splitext(fn)
                out_folder = os.path.join(self.output_dir, name)
                os.makedirs(out_folder, exist_ok=True)
                with Image.open(src) as img:
                    w, h = img.size
                    c1 = int(w * col_lines[0])
                    c2 = int(w * col_lines[1])
                    r1 = int(h * row_lines[0])
                    r2 = int(h * row_lines[1])
                    coords = [
                        (0, 0, c1, r1), (c1, 0, c2, r1), (c2, 0, w, r1),
                        (0, r1, c1, r2), (c1, r1, c2, r2), (c2, r1, w, r2),
                        (0, r2, c1, h), (c1, r2, c2, h), (c2, r2, w, h),
                    ]
                    for n, (left, upper, right, lower) in enumerate(coords, 1):
                        crop = img.crop((left, upper, right, lower))
                        # RGBA/P/LA 模式不能直接存 JPEG，需先转 RGB
                        if crop.mode in ('RGBA', 'P', 'LA'):
                            crop = crop.convert('RGB')
                        crop.save(os.path.join(out_folder, f"{n}.jpg"), quality=95)
                ok += 1
            except Exception as e:
                self.log(f"[{idx}] FAIL - {e}"); fail += 1
        self.log(f"九宫格切分完成: 成功 {ok}，失败 {fail}")
        if ok:
            messagebox.showinfo("完成", f"九宫格切分完成!\n成功: {ok} 张\n失败: {fail} 张")

    # ==================== 九宫格可视化 ====================

    def _on_mode_switch(self, *args):
        mode = self.mode_var.get()
        if mode == "nine_grid":
            self.size_row.pack_forget()
            self.nine_grid_panel.pack(fill="both", expand=True, padx=0, pady=(0, 8))
            # 如果已有选中图片，加载第一张到预览
            if self.selected_files:
                self._ng_load_preview_image(self.selected_files[0])
        else:
            self.nine_grid_panel.pack_forget()
            self.size_row.pack(fill="x", padx=16, pady=(4, 4))

    def _ng_load_preview_image(self, path):
        try:
            self.ng_current_image = Image.open(path)
            self.ng_current_image_path = path
            w, h = self.ng_current_image.size
            self.ng_info_label.configure(text=f"{os.path.basename(path)} | {w}×{h}px")
            self._ng_redraw()
            self._ng_update_preview()
        except Exception as e:
            self.ng_info_label.configure(text=f"加载失败: {e}")

    def _ng_redraw(self):
        if not hasattr(self, "ng_current_image") or not self.ng_current_image:
            return
        self.ng_canvas.update_idletasks()
        canvas_w = self.ng_canvas.winfo_width()
        canvas_h = self.ng_canvas.winfo_height()
        if canvas_w < 10 or canvas_h < 10:
            return

        img_w, img_h = self.ng_current_image.size
        scale_w = canvas_w / img_w
        scale_h = canvas_h / img_h
        self.ng_image_scale = min(scale_w, scale_h, 1.0)

        display_w = int(img_w * self.ng_image_scale)
        display_h = int(img_h * self.ng_image_scale)

        resized = self.ng_current_image.resize((display_w, display_h), Image.LANCZOS)
        self.ng_photo = ImageTk.PhotoImage(resized)

        offset_x = (canvas_w - display_w) // 2
        offset_y = (canvas_h - display_h) // 2
        self.ng_img_offset = (offset_x, offset_y)
        self.ng_img_display_size = (display_w, display_h)

        self.ng_canvas.delete("all")
        self.ng_canvas.create_image(offset_x, offset_y, anchor=tk.NW, image=self.ng_photo)
        self._ng_draw_grid_lines()

    def _ng_draw_grid_lines(self):
        ox, oy = self.ng_img_offset
        dw, dh = self.ng_img_display_size

        c1 = ox + int(dw * self.ng_col_lines[0])
        c2 = ox + int(dw * self.ng_col_lines[1])
        r1 = oy + int(dh * self.ng_row_lines[0])
        r2 = oy + int(dh * self.ng_row_lines[1])

        # 竖线（红色虚线）
        for x in [c1, c2]:
            self.ng_canvas.create_line(x, oy, x, oy + dh, fill="#FF4444", width=2, dash=(6, 4), tags="grid")
        # 横线
        for y in [r1, r2]:
            self.ng_canvas.create_line(ox, y, ox + dw, y, fill="#FF4444", width=2, dash=(6, 4), tags="grid")

        # 更新像素坐标显示
        img_w, img_h = self.ng_current_image.size
        px_c1 = int(img_w * self.ng_col_lines[0])
        px_c2 = int(img_w * self.ng_col_lines[1])
        px_r1 = int(img_h * self.ng_row_lines[0])
        px_r2 = int(img_h * self.ng_row_lines[1])
        self.ng_pixel_label.configure(
            text=f"像素坐标 | 列: {px_c1}, {px_c2} | 行: {px_r1}, {px_r2} | 每格: {px_c1}×{px_r1} / {px_c2-px_c1}×{px_r2-px_r1} / {img_w-px_c2}×{img_h-px_r2}")

    def _ng_on_mouse_down(self, event):
        if not hasattr(self, "ng_current_image") or not self.ng_current_image:
            return
        ox, oy = self.ng_img_offset
        dw, dh = self.ng_img_display_size

        for i, line in enumerate(self.ng_col_lines):
            x = ox + int(dw * line)
            if abs(event.x - x) < 10:
                self.ng_dragging = f"col_{i}"
                return

        for i, line in enumerate(self.ng_row_lines):
            y = oy + int(dh * line)
            if abs(event.y - y) < 10:
                self.ng_dragging = f"row_{i}"
                return

    def _ng_on_mouse_drag(self, event):
        if not self.ng_dragging:
            return
        ox, oy = self.ng_img_offset
        dw, dh = self.ng_img_display_size

        if self.ng_dragging.startswith("col_"):
            idx = int(self.ng_dragging.split("_")[1])
            new_pos = (event.x - ox) / dw if dw > 0 else 0.333
            new_pos = max(0.05, min(0.95, new_pos))
            self.ng_col_lines[idx] = new_pos
        elif self.ng_dragging.startswith("row_"):
            idx = int(self.ng_dragging.split("_")[1])
            new_pos = (event.y - oy) / dh if dh > 0 else 0.333
            new_pos = max(0.05, min(0.95, new_pos))
            self.ng_row_lines[idx] = new_pos

        self._ng_update_line_vars()
        self._ng_redraw()

    def _ng_on_mouse_up(self, event):
        if self.ng_dragging:
            self.ng_dragging = None
            self._ng_update_preview()

    def _ng_on_mouse_move(self, event):
        """鼠标悬停时显示像素坐标"""
        if not hasattr(self, "ng_current_image") or not self.ng_current_image:
            return
        ox, oy = self.ng_img_offset
        dw, dh = self.ng_img_display_size
        img_w, img_h = self.ng_current_image.size
        scale = self.ng_image_scale

        rel_x = event.x - ox
        rel_y = event.y - oy
        if 0 <= rel_x <= dw and 0 <= rel_y <= dh:
            px = int(rel_x / scale)
            py = int(rel_y / scale)
            # 检查是否靠近参考线
            near_line = ""
            for i, line in enumerate(self.ng_col_lines):
                lx = int(dw * line)
                if abs(rel_x - lx) < 8:
                    near_line = f" [← 拖拽列线{i+1}]"
            for i, line in enumerate(self.ng_row_lines):
                ly = int(dh * line)
                if abs(rel_y - ly) < 8:
                    near_line = f" [← 拖拽行线{i+1}]"
            self.ng_pixel_label.configure(
                text=f"鼠标: ({px}, {py}) | 图片: {img_w}×{img_h}{near_line}")
        else:
            self._ng_draw_grid_lines()  # 恢复默认像素显示

    def _ng_apply_manual(self):
        try:
            self.ng_col_lines[0] = float(self.ng_col1_var.get().replace("%", "")) / 100
            self.ng_col_lines[1] = float(self.ng_col2_var.get().replace("%", "")) / 100
            self.ng_row_lines[0] = float(self.ng_row1_var.get().replace("%", "")) / 100
            self.ng_row_lines[1] = float(self.ng_row2_var.get().replace("%", "")) / 100
            self._ng_redraw()
            self._ng_update_preview()
        except ValueError:
            messagebox.showerror("错误", "请输入有效的百分比，如 33.3%")

    def _ng_reset_lines(self):
        self.ng_col_lines = [0.333, 0.667]
        self.ng_row_lines = [0.333, 0.667]
        self._ng_update_line_vars()
        self._ng_redraw()
        self._ng_update_preview()

    def _ng_update_line_vars(self):
        self.ng_col1_var.set(f"{self.ng_col_lines[0]*100:.1f}%")
        self.ng_col2_var.set(f"{self.ng_col_lines[1]*100:.1f}%")
        self.ng_row1_var.set(f"{self.ng_row_lines[0]*100:.1f}%")
        self.ng_row2_var.set(f"{self.ng_row_lines[1]*100:.1f}%")

    def _ng_update_preview(self):
        if not hasattr(self, "ng_current_image") or not self.ng_current_image:
            return
        w, h = self.ng_current_image.size
        c1 = int(w * self.ng_col_lines[0])
        c2 = int(w * self.ng_col_lines[1])
        r1 = int(h * self.ng_row_lines[0])
        r2 = int(h * self.ng_row_lines[1])

        coords = [
            (0, 0, c1, r1), (c1, 0, c2, r1), (c2, 0, w, r1),
            (0, r1, c1, r2), (c1, r1, c2, r2), (c2, r1, w, r2),
            (0, r2, c1, h), (c1, r2, c2, h), (c2, r2, w, h),
        ]

        for i, (left, upper, right, lower) in enumerate(coords):
            try:
                crop = self.ng_current_image.crop((left, upper, right, lower))
                crop.thumbnail((55, 55), Image.LANCZOS)
                photo = ImageTk.PhotoImage(crop)
                self.ng_preview_labels[i].configure(image=photo, text="")
                self.ng_preview_labels[i].image = photo
            except Exception:
                pass

    # ==================== Settings ====================

    def toggle_key_visibility(self):
        self.key_visible.set(not self.key_visible.get())
        self.key_entry.configure(show="" if self.key_visible.get() else "*")
        self.toggle_key_btn.configure(text="隐藏" if self.key_visible.get() else "显示")

    def save_settings(self):
        self.config["api_base_url"] = self.api_url_var.get().strip()
        self.config["api_key"] = self.api_key_var.get().strip()
        self.config["api_model"] = self.api_model_var.get().strip()
        self.config["bailian_api_key"] = self.bailian_key_var.get().strip()
        self.config["bailian_mode"] = self.bailian_mode_var.get()
        self.config["bailian_model"] = self.bailian_model_var.get()
        self.config["bailian_ratio"] = self.bailian_ratio_var.get()
        self.config["bailian_video_duration"] = self.video_duration_var.get()
        self.config["tts_engine"] = self.tts_engine_var.get()
        voice_display = self.tts_voice_var.get()
        self.config["tts_voice"] = self.tts_voice_map.get(voice_display, "sambert-zhichu-v1")
        self.config["tts_custom_model"] = self.tts_custom_model_var.get().strip()
        self.config["tts_adv_mode"] = self.tts_adv_mode_var.get()
        self.config["tts_ref_audio"] = self.tts_ref_audio_var.get().strip()
        self.config["tts_prompt_text"] = self.tts_prompt_text_var.get().strip()
        self.config["sovits_url"] = self.sovits_url_var.get().strip()
        self.config["sovits_bat_path"] = self.sovits_bat_var.get().strip()
        self.config["sovits_character"] = self.sovits_character_var.get().strip()
        self.config["sovits_emotion"] = self.sovits_emotion_var.get().strip()
        save_config(self.config)
        self.settings_status.configure(text="设置已保存到 config.json")
        self.root.after(3000, lambda: self.settings_status.configure(text=""))

    def reset_settings(self):
        self.api_url_var.set(DEFAULT_CONFIG["api_base_url"])
        self.api_key_var.set(DEFAULT_CONFIG["api_key"])
        self.api_model_var.set(DEFAULT_CONFIG["api_model"])
        self.settings_status.configure(text="已恢复为默认值（尚未保存）")
        self.root.after(3000, lambda: self.settings_status.configure(text=""))


def main():
    # 全局异常钩子 — 捕获所有未处理异常并写入 crash.log
    def _global_excepthook(exc_type, exc_value, exc_tb):
        msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logging.error("未捕获异常:\n%s", msg)
        print(f"\n[致命错误] 已写入 crash.log:\n{msg}", file=sys.stderr)
    sys.excepthook = _global_excepthook

    # 线程异常钩子
    def _thread_excepthook(args):
        msg = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_tb))
        logging.error("线程异常:\n%s", msg)
        print(f"\n[线程错误] 已写入 crash.log:\n{msg}", file=sys.stderr)
    threading.excepthook = _thread_excepthook

    try:
        app = BatchProcessor()
        app.root.mainloop()
    except Exception as e:
        logging.error("主循环异常:\n%s", traceback.format_exc())
        print(f"\n[致命错误] {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
