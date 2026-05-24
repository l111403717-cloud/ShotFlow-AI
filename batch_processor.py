"""AI 镜头脚本 + 视觉引擎 + 智能配音 一体化工具 v6.0
CustomTkinter 深色主题 | 侧边栏导航 | VibeVoice 自动唤醒
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import time
import json
import requests
from PIL import Image
import threading
import base64
import time as _time

# ============ CustomTkinter 全局主题 ============
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ============ 设计系统 ============
C = {
    "bg":        "#0A0A0A",
    "surface":   "#141414",
    "surface2":  "#1E1E1E",
    "border":    "#2A2A2A",
    "accent":    "#DEFF9A",
    "accent2":   "#B8E06E",
    "text":      "#EAEAEA",
    "text2":     "#999999",
    "text3":     "#666666",
    "red":       "#FF6B6B",
    "green":     "#6BCB77",
    "blue":      "#4FC3F7",
    "warn":      "#FFD93D",
}

FONT_TITLE  = ("Segoe UI Semibold", 20)
FONT_H2     = ("Segoe UI Semibold", 14)
FONT_BODY   = ("Segoe UI", 12)
FONT_SMALL  = ("Segoe UI", 10)
FONT_MONO   = ("Consolas", 11)
FONT_MONO_SM= ("Consolas", 10)

# ============ 阿里云百炼模型分类 ============
BAILIAN_MODEL_MAP = {
    "旗舰模式 (Flagship)": [
        "qwen-image-2.0-pro",
        "qwen-image-2.0-pro-2026-04-22",
        "qwen-image-2.0-pro-2026-03-03",
        "wan2.7-image-pro",
    ],
    "中等模式 (Standard)": [
        "qwen-image-2.0",
        "qwen-image-2.0-2026-03-03",
        "wan2.7-image",
    ],
    "视频生成 (Video Generation)": [
        "wan2.7-t2v", "wan2.7-t2v-2026-04-25",
        "wan2.7-i2v", "wan2.7-i2v-2026-04-25",
        "wan2.7-r2v",
        "happyhorse-1.0-t2v", "happyhorse-1.0-i2v", "happyhorse-1.0-r2v",
    ],
    "图像/视频编辑 (Edit)": [
        "wan2.7-videoedit", "happyhorse-1.0-video-edit",
    ],
}

VIDEO_MODELS = (BAILIAN_MODEL_MAP["视频生成 (Video Generation)"]
                + BAILIAN_MODEL_MAP["图像/视频编辑 (Edit)"])
T2V_MODELS   = [m for m in VIDEO_MODELS if m.endswith("-t2v") or "-t2v-" in m]
I2V_MODELS   = [m for m in VIDEO_MODELS if m.endswith("-i2v") or "-i2v-" in m]
R2V_MODELS   = [m for m in VIDEO_MODELS if m.endswith("-r2v") or "-r2v-" in m]
EDIT_MODELS  = BAILIAN_MODEL_MAP["图像/视频编辑 (Edit)"]
IMAGE_MODELS = BAILIAN_MODEL_MAP["旗舰模式 (Flagship)"] + BAILIAN_MODEL_MAP["中等模式 (Standard)"]

BAILIAN_BASE_URL = "https://dashscope.aliyuncs.com/api/v1"

# ============ 配置 ============
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "api_base_url": "https://token-plan-cn.xiaomimimo.com/anthropic",
    "api_key": "tp-clgfpo6b15ix395enlisuyd5eifnderql0r4215zyifj3v5t",
    "api_model": "mimo-v2.5-pro",
    "image_width": "1920", "image_height": "1080",
    "dark_mode": True,
    "bailian_api_key": "", "bailian_mode": "旗舰模式 (Flagship)",
    "bailian_model": "qwen-image-2.0-pro", "bailian_video_duration": "5",
    "bailian_ratio": "1:1 (正方形)",
    "tts_engine": "bailian", "tts_voice": "sambert-zhichu-v1", "tts_custom_model": "",
    "sovits_url": "http://127.0.0.1:8080",
    "sovits_bat_path": r"D:\剪映\声音克隆\一键启动.bat",
    "sovits_character": "", "sovits_emotion": "平静",
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
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        merged = {**DEFAULT_CONFIG, **cfg}
        return merged
    return dict(DEFAULT_CONFIG)


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# ============ 辅助组件 ============

class SectionCard(ctk.CTkFrame):
    """带标题的卡片容器"""
    def __init__(self, master, title="", **kwargs):
        super().__init__(master, fg_color=C["surface"], corner_radius=12,
                         border_width=1, border_color=C["border"], **kwargs)
        if title:
            ctk.CTkLabel(self, text=title, font=FONT_H2,
                         text_color=C["accent"]).pack(anchor="w", padx=16, pady=(12, 4))


class LogBox(ctk.CTkTextbox):
    """日志文本框"""
    def __init__(self, master, **kwargs):
        super().__init__(master, font=FONT_MONO_SM, fg_color=C["surface2"],
                         text_color=C["text2"], corner_radius=8,
                         border_width=1, border_color=C["border"],
                         state="disabled", **kwargs)

    def append(self, msg):
        self.configure(state="normal")
        self.insert("end", msg + "\n")
        self.see("end")
        self.configure(state="disabled")

    def clear_all(self):
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.configure(state="disabled")


# ============ 主应用 ============

class BatchProcessor:
    NAV_ITEMS = [
        ("Script",  "剧本生成"),
        ("Visuals", "视觉引擎"),
        ("Voice",   "智能配音"),
        ("API",     "全局设置"),
        ("Assembly", "一键总装"),
    ]

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("AI Content Studio v6.0")
        self.root.geometry("1400x900")
        self.root.minsize(1100, 700)
        self.root.configure(fg_color=C["bg"])

        self.config = load_config()
        self.selected_files = []
        self._char_name_to_id = {}
        self.output_dir = ""
        self._current_page = None

        self._build_sidebar()
        self._build_pages()
        self._show_page("Script")

    # ==================== 侧边栏 ====================

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self.root, width=200, fg_color=C["surface"],
                                     corner_radius=0, border_width=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Logo 区
        ctk.CTkLabel(self.sidebar, text="AI Studio", font=FONT_TITLE,
                     text_color=C["accent"]).pack(pady=(28, 24), padx=16, anchor="w")

        self.nav_buttons = {}
        for key, label in self.NAV_ITEMS:
            btn = ctk.CTkButton(
                self.sidebar, text=f"  {label}", font=FONT_BODY,
                fg_color="transparent", hover_color=C["surface2"],
                text_color=C["text"], anchor="w", height=44, corner_radius=8,
                command=lambda k=key: self._show_page(k))
            btn.pack(fill="x", padx=12, pady=2)
            self.nav_buttons[key] = btn

        # 底部版本
        ctk.CTkLabel(self.sidebar, text="v6.0 · CustomTkinter",
                     font=FONT_SMALL, text_color=C["text3"]).pack(
                         side="bottom", pady=12, padx=16, anchor="w")

    def _show_page(self, key):
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.configure(fg_color=C["accent"], text_color=C["bg"],
                              hover_color=C["accent2"])
            else:
                btn.configure(fg_color="transparent", text_color=C["text"],
                              hover_color=C["surface2"])
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

        self._build_page_script(self.page_frames["Script"])
        self._build_page_visuals(self.page_frames["Visuals"])
        self._build_page_voice(self.page_frames["Voice"])
        self._build_page_api(self.page_frames["API"])
        self._build_page_assembly(self.page_frames["Assembly"])

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
        top = ctk.CTkFrame(parent, fg_color=C["bg"])
        top.pack(fill="both", expand=True)

        # 左侧控制
        left = ctk.CTkFrame(top, fg_color=C["bg"], width=360)
        left.pack(side="left", fill="y", padx=(16, 8), pady=16)
        left.pack_propagate(False)

        scroll_l = ctk.CTkScrollableFrame(left, fg_color=C["bg"])
        scroll_l.pack(fill="both", expand=True)

        # ---- 图片批处理 ----
        ctk.CTkLabel(scroll_l, text="图片批处理", font=FONT_H2,
                     text_color=C["accent"]).pack(anchor="w", pady=(0, 12))

        card = SectionCard(scroll_l, title="选择图片")
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

        card = SectionCard(scroll_l, title="处理模式")
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

        size_row = ctk.CTkFrame(card, fg_color="transparent")
        size_row.pack(fill="x", padx=16, pady=(4, 4))
        ctk.CTkLabel(size_row, text="宽:", font=FONT_SMALL, text_color=C["text2"]).pack(side="left")
        self.width_var = tk.StringVar(value=self.config.get("image_width", "1920"))
        ctk.CTkEntry(size_row, textvariable=self.width_var, width=80, font=FONT_MONO,
                      fg_color=C["surface2"], border_color=C["border"],
                      corner_radius=8).pack(side="left", padx=(2, 12))
        ctk.CTkLabel(size_row, text="高:", font=FONT_SMALL, text_color=C["text2"]).pack(side="left")
        self.height_var = tk.StringVar(value=self.config.get("image_height", "1080"))
        ctk.CTkEntry(size_row, textvariable=self.height_var, width=80, font=FONT_MONO,
                      fg_color=C["surface2"], border_color=C["border"],
                      corner_radius=8).pack(side="left", padx=(2, 0))

        ctk.CTkButton(scroll_l, text="开始处理", font=FONT_H2,
                       fg_color=C["accent"], text_color=C["bg"],
                       hover_color=C["accent2"], corner_radius=12, height=40,
                       command=self.start_processing).pack(fill="x", padx=20, pady=(0, 4))
        ctk.CTkButton(scroll_l, text="打开输出目录", font=FONT_SMALL,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text2"], corner_radius=8, height=28,
                       command=self.open_output_dir).pack(anchor="w", padx=20, pady=(0, 16))

        # ---- 百炼视觉引擎 ----
        ctk.CTkLabel(scroll_l, text="阿里云百炼视觉引擎", font=FONT_H2,
                     text_color=C["accent"]).pack(anchor="w", pady=(0, 12))

        # API Key
        card = SectionCard(scroll_l, title="百炼 API Key")
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
        card = SectionCard(scroll_l, title="生成模式")
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
        card = SectionCard(scroll_l, title="画面比例")
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
        self.video_settings_frame = SectionCard(scroll_l, title="视频设置")
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

        ctk.CTkLabel(self.video_settings_frame, text="参考图 (可选，仅 i2v/r2v/videoedit):",
                     font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w", padx=16, pady=(4, 0))
        ref_row = ctk.CTkFrame(self.video_settings_frame, fg_color="transparent")
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
        card = SectionCard(scroll_l, title="Prompt / 描述")
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
        gen_row = ctk.CTkFrame(scroll_l, fg_color="transparent")
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
        ctk.CTkButton(scroll_l, text="打开输出目录", font=FONT_SMALL,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text2"], corner_radius=8, height=30,
                       command=self._open_bailian_output).pack(anchor="w", padx=20, pady=(0, 16))

        # 右侧日志
        right = ctk.CTkFrame(top, fg_color=C["bg"])
        right.pack(side="right", fill="both", expand=True, padx=(0, 16), pady=16)

        info_row = ctk.CTkFrame(right, fg_color="transparent")
        info_row.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(info_row, text="当前模型: ", font=FONT_BODY,
                     text_color=C["text2"]).pack(side="left")
        self.bailian_info_label = ctk.CTkLabel(info_row, text="qwen-image-2.0-pro",
                                                font=FONT_MONO, text_color=C["blue"])
        self.bailian_info_label.pack(side="left")

        ctk.CTkLabel(right, text="生成结果 / 日志", font=FONT_H2,
                     text_color=C["text"]).pack(anchor="w", pady=(0, 4))
        self.bailian_log = LogBox(right)
        self.bailian_log.pack(fill="both", expand=True)

        ctk.CTkButton(right, text="清空日志", font=FONT_SMALL, width=80,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text2"], corner_radius=6, height=28,
                       command=self._clear_bailian_log).pack(anchor="w", pady=(6, 0))

    # ---------- Voice 页面 ----------

    def _build_page_voice(self, parent):
        top = ctk.CTkFrame(parent, fg_color=C["bg"])
        top.pack(fill="both", expand=True)

        # 左侧
        left = ctk.CTkFrame(top, fg_color=C["bg"], width=400)
        left.pack(side="left", fill="y", padx=(16, 8), pady=16)
        left.pack_propagate(False)

        scroll_l = ctk.CTkScrollableFrame(left, fg_color=C["bg"])
        scroll_l.pack(fill="both", expand=True)

        ctk.CTkLabel(scroll_l, text="AI 智能配音", font=FONT_TITLE,
                     text_color=C["accent"]).pack(anchor="w", pady=(0, 12))

        # 引擎选择
        self._tts_engine_card = SectionCard(scroll_l, title="TTS 引擎")
        self._tts_engine_card.pack(fill="x", pady=(0, 8))
        self.tts_engine_var = tk.StringVar(value=self.config.get("tts_engine", "bailian"))
        self.tts_engine_bailian_rb = ctk.CTkRadioButton(
            self._tts_engine_card, text="阿里云百炼 TTS", variable=self.tts_engine_var, value="bailian",
            font=FONT_BODY, fg_color=C["accent"], text_color=C["text"],
            hover_color=C["accent2"], command=self._on_tts_engine_change)
        self.tts_engine_bailian_rb.pack(anchor="w", padx=16, pady=4)
        self.tts_engine_sovits_rb = ctk.CTkRadioButton(
            self._tts_engine_card, text="GPT-SoVITS (VibeVoice)", variable=self.tts_engine_var, value="sovits",
            font=FONT_BODY, fg_color=C["accent"], text_color=C["text"],
            hover_color=C["accent2"], command=self._on_tts_engine_change)
        self.tts_engine_sovits_rb.pack(anchor="w", padx=16, pady=(0, 10))

        # 百炼 TTS
        self.bailian_tts_frame = SectionCard(scroll_l, title="阿里云百炼 TTS 配置")
        self.bailian_tts_frame.pack(fill="x", pady=(0, 8))

        self.tts_voice_map = {
            "sambert-zhichu-v1 (成熟男声-推荐)": "sambert-zhichu-v1",
            "sambert-zhiyue-v1 (知性女声-推荐)": "sambert-zhiyue-v1",
            "sambert-zhide-v1 (浑厚男声)": "sambert-zhide-v1",
            "sambert-zhida-v1 (标准男声)": "sambert-zhida-v1",
        }
        saved_voice = self.config.get("tts_voice", "sambert-zhichu-v1")
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
        self.sovits_frame = SectionCard(scroll_l, title="GPT-SoVITS (VibeVoice) 配置")

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

        self._on_tts_engine_change()

        # 台词输入
        card = SectionCard(scroll_l, title="台词 / 旁白")
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

        self.tts_gen_btn = ctk.CTkButton(card, text="一键批量生成音频", font=FONT_H2,
                                          fg_color=C["accent"], text_color=C["bg"],
                                          hover_color=C["accent2"], corner_radius=12,
                                          height=44, command=self.start_tts_generate)
        self.tts_gen_btn.pack(fill="x", padx=16, pady=(0, 12))

        # 右侧日志
        right = ctk.CTkFrame(top, fg_color=C["bg"])
        right.pack(side="right", fill="both", expand=True, padx=(0, 16), pady=16)

        ctk.CTkLabel(right, text="状态日志", font=FONT_H2,
                     text_color=C["text"]).pack(anchor="w", pady=(0, 4))
        self.tts_log = LogBox(right)
        self.tts_log.pack(fill="both", expand=True)

        log_btn_row = ctk.CTkFrame(right, fg_color="transparent")
        log_btn_row.pack(fill="x", pady=(6, 0))
        ctk.CTkButton(log_btn_row, text="清空日志", font=FONT_SMALL, width=80,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text2"], corner_radius=6, height=28,
                       command=self._clear_tts_log).pack(side="left")
        ctk.CTkButton(log_btn_row, text="打开音频目录", font=FONT_SMALL, width=100,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text2"], corner_radius=6, height=28,
                       command=self._open_audio_output).pack(side="left", padx=8)

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

    def _get_output_dir(self, sub_dir):
        """根据用户保存路径配置，解析实际输出目录"""
        base = os.path.dirname(os.path.abspath(__file__))
        save = self.save_path_var.get().strip()
        if save and os.path.isdir(save):
            return os.path.join(save, sub_dir)
        return os.path.join(base, sub_dir)

    def _asm_log(self, msg):
        self.root.after(0, lambda: self.asm_log.append(f"[{time.strftime('%H:%M:%S')}] {msg}"))

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
        """在目录中查找匹配 shot_X.ext 或 {name}_shot_X.ext 的文件"""
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
        return exact

    def _refresh_assembly_status(self):
        import re, shutil
        prefix = self._get_project_prefix()
        video_dir = self.asm_video_dir_var.get().strip()
        audio_dir = self._get_output_dir("output_audio")

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

        # ---- 检测音频（匹配 {prefix}_shot_X 或 shot_X）----
        audio_shots = set()
        if os.path.isdir(audio_dir):
            for f in os.listdir(audio_dir):
                if f.lower().endswith(".wav"):
                    m = re.match(r"(?:.+_)?shot_(\d+)\.wav$", f, re.IGNORECASE)
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
        audio_dir = self._get_output_dir("output_audio")
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
        self.root.after(0, lambda: self.asm_start_btn.configure(
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
        # 转义路径中的特殊字符（Windows）
        srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")
        # 单引号包裹用于 subtitles 滤镜
        srt_ffmpeg = srt_escaped.replace("'", "\\'")

        # 构建滤镜链
        vf_parts = []
        if pad_len > 0.01:
            vf_parts.append(f"tpad=stop_mode=clone:stop_duration={pad_len:.3f}")

        # 字幕样式: 微软雅黑/纯白字/黑色描边/底部居中
        sub_style = (
            "FontName=Microsoft YaHei,"
            "FontSize=16,"
            "PrimaryColour=&HFFFFFF,"
            "OutlineColour=&H000000,"
            "Outline=2,"
            "Alignment=2,"
            "MarginV=25"
        )
        vf_parts.append(f"subtitles='{srt_ffmpeg}':force_style='{sub_style}'")

        vf = ",".join(vf_parts)

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-map", "0:v",
            "-map", "1:a",
            "-vf", vf,
            "-c:v", "libx264",
            "-c:a", "aac",
            "-b:a", "192k",
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

                self.root.after(0, lambda: self._apply_character(target, emotions, names))
            except Exception as e:
                self._tts_log_msg(f"连接 VibeVoice 失败: {e}")

            self._enable_refresh_btn()

        threading.Thread(target=_worker, daemon=True).start()

    def _enable_refresh_btn(self):
        self.root.after(0, lambda: self.sovits_refresh_btn.configure(
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
            self.bailian_tts_frame.pack(fill="x", pady=(0, 8), after=self._tts_engine_card)
        else:
            self.bailian_tts_frame.pack_forget()
            self.sovits_frame.pack(fill="x", pady=(0, 8), after=self._tts_engine_card)

    # ==================== 百炼视觉引擎 ====================

    def _on_mode_changed(self, value=None):
        self._update_model_combo()
        self._toggle_video_settings()
        self._save_bailian_config()

    def _on_model_changed(self, value=None):
        model = self.bailian_model_var.get()
        self.bailian_info_label.configure(text=model)
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
        self.bailian_model_combo.configure(values=models)
        if self.bailian_model_var.get() not in models:
            if models:
                self.bailian_model_var.set(models[0])
        if hasattr(self, "bailian_info_label"):
            self.bailian_info_label.configure(text=self.bailian_model_var.get())

    def _toggle_video_settings(self):
        model = self.bailian_model_var.get()
        if model in VIDEO_MODELS:
            self.video_settings_frame.pack(fill="x", pady=(0, 8))
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
        for i, shot in enumerate(self._parsed_shots):
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
        self.root.after(0, lambda: self.bailian_gen_btn.configure(state="normal", text="生成当前镜头"))

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
        self.root.after(0, lambda: self.bailian_log.append(f"[{ts}] {msg}"))

    def _clear_bailian_log(self):
        self.bailian_log.clear_all()

    def _open_bailian_output(self):
        out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bailian_output")
        if os.path.exists(out_dir):
            os.startfile(out_dir)
        else:
            self._bailian_log_msg("输出目录尚未创建，生成后会自动创建。")

    def start_bailian_generate(self):
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
            else:
                self._bailian_log_msg("使用 text2image 接口 (异步)")
                headers["X-DashScope-Async"] = "enable"
                payload = {"model": model, "input": {"prompt": prompt},
                           "parameters": {"n": 1, "size": img_size}}
                resp = requests.post(f"{BAILIAN_BASE_URL}/services/aigc/text2image/image-synthesis",
                                     headers=headers, json=payload, timeout=120)
                if resp.status_code == 200:
                    task_id = resp.json().get("output", {}).get("task_id", "")
                    if task_id:
                        self._bailian_log_msg(f"任务已提交: {task_id}")
                        self._bailian_poll_task(api_key, task_id, "image")
                else:
                    self._bailian_log_msg(f"HTTP {resp.status_code}: {resp.text[:300]}")
        except Exception as e:
            self._bailian_log_msg(f"错误: {e}")
        finally:
            self.root.after(0, lambda: self.bailian_gen_btn.configure(state="normal", text="生成当前镜头"))

    def _bailian_generate_video(self, api_key, model, prompt, ref_path, duration):
        self._bailian_log_msg(f"调用视频生成，模型: {model}")
        try:
            use_sdk = False
            try:
                import dashscope
                dashscope.api_key = api_key
                use_sdk = True
                self._bailian_log_msg("使用 dashscope SDK")
            except ImportError:
                self._bailian_log_msg("dashscope 未安装，使用 requests")
            if use_sdk:
                self._submit_video_via_sdk(api_key, model, prompt, ref_path, duration)
            else:
                self._submit_video_via_requests(api_key, model, prompt, ref_path, duration)
        except Exception as e:
            self._bailian_log_msg(f"错误: {e}")
        finally:
            self.root.after(0, lambda: self.bailian_gen_btn.configure(state="normal", text="生成当前镜头"))

    def _submit_video_via_sdk(self, api_key, model, prompt, ref_path, duration):
        import dashscope
        self._bailian_log_msg("通过 SDK 提交视频任务...")
        ratio_info = self.ratio_map.get(self.bailian_ratio_var.get(), {})
        vid_w, vid_h = ratio_info.get("w", 1280), ratio_info.get("h", 720)

        if model in EDIT_MODELS:
            if not ref_path or not os.path.exists(ref_path):
                self._bailian_log_msg("错误: video-edit 必须提供参考素材！"); return
            oss_url = self._upload_to_bailian_oss(api_key, os.path.abspath(ref_path))
            if not oss_url:
                self._bailian_log_msg("错误: OSS 上传失败！"); return
            response = dashscope.VideoSynthesis.async_call(
                model=model, input={"prompt": prompt, "media": oss_url},
                parameters={"size": f"{vid_w}*{vid_h}", "duration": int(duration) if duration.isdigit() else 5})
        elif model in I2V_MODELS:
            if not ref_path or not os.path.exists(ref_path):
                self._bailian_log_msg("错误: i2v 必须提供参考图！"); return
            response = dashscope.VideoSynthesis.async_call(
                model=model, prompt=prompt, ref_img_url=os.path.abspath(ref_path),
                parameters={"size": f"{vid_w}*{vid_h}", "duration": int(duration) if duration.isdigit() else 5})
        elif model in R2V_MODELS:
            if not ref_path or not os.path.exists(ref_path):
                self._bailian_log_msg("错误: r2v 必须提供参考素材！"); return
            response = dashscope.VideoSynthesis.async_call(
                model=model, prompt=prompt, ref_video_url=os.path.abspath(ref_path),
                parameters={"size": f"{vid_w}*{vid_h}", "duration": int(duration) if duration.isdigit() else 5})
        else:
            response = dashscope.VideoSynthesis.async_call(
                model=model, prompt=prompt,
                parameters={"size": f"{vid_w}*{vid_h}", "duration": int(duration) if duration.isdigit() else 5})

        task_id = None
        if hasattr(response, "output") and response.output:
            output = response.output
            task_id = output.get("task_id", "") if isinstance(output, dict) else getattr(output, "task_id", "")
        elif isinstance(response, dict):
            task_id = response.get("output", {}).get("task_id", "")
        if task_id:
            self._bailian_log_msg(f"任务已提交: {task_id}")
            self._bailian_poll_task(api_key, task_id, "video")
        else:
            self._bailian_log_msg(f"未获取到 task_id: {response}")

    def _submit_video_via_requests(self, api_key, model, prompt, ref_path, duration):
        self._bailian_log_msg("通过 requests 提交视频任务...")
        ratio_info = self.ratio_map.get(self.bailian_ratio_var.get(), {})
        vid_w, vid_h = ratio_info.get("w", 1280), ratio_info.get("h", 720)
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
                   "X-DashScope-Async": "enable"}
        payload = {"model": model, "input": {"prompt": prompt},
                   "parameters": {"size": f"{vid_w}*{vid_h}", "duration": int(duration) if duration.isdigit() else 5}}
        if model in EDIT_MODELS and ref_path and os.path.exists(ref_path):
            oss_url = self._upload_to_bailian_oss(api_key, os.path.abspath(ref_path))
            if oss_url:
                payload["input"]["media"] = oss_url
        resp = requests.post(f"{BAILIAN_BASE_URL}/services/aigc/video-generation/video-synthesis",
                             headers=headers, json=payload, timeout=120)
        if resp.status_code == 200:
            task_id = resp.json().get("output", {}).get("task_id", "")
            if task_id:
                self._bailian_log_msg(f"任务已提交: {task_id}")
                self._bailian_poll_task(api_key, task_id, "video")
        else:
            self._bailian_log_msg(f"HTTP {resp.status_code}: {resp.text[:300]}")

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
                    return
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
        out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bailian_output")
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

    def _browse_sovits_bat(self):
        path = filedialog.askopenfilename(
            title="选择启动脚本",
            filetypes=[("批处理", "*.bat"), ("所有文件", "*.*")])
        if path:
            self.sovits_bat_var.set(path)

    def _tts_log_msg(self, msg):
        ts = time.strftime("%H:%M:%S")
        self.root.after(0, lambda: self.tts_log.append(f"[{ts}] {msg}"))

    def _clear_tts_log(self):
        self.tts_log.clear_all()

    def _open_audio_output(self):
        out_dir = self._get_output_dir("output_audio")
        if os.path.exists(out_dir):
            os.startfile(out_dir)

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
        voice_display = self.tts_voice_var.get()
        self.config["tts_voice"] = self.tts_voice_map.get(voice_display, "sambert-zhichu-v1")
        self.config["tts_custom_model"] = self.tts_custom_model_var.get().strip()
        self.config["sovits_url"] = self.sovits_url_var.get().strip()
        self.config["sovits_bat_path"] = self.sovits_bat_var.get().strip()
        self.config["sovits_character"] = self.sovits_character_var.get().strip()
        self.config["sovits_emotion"] = self.sovits_emotion_var.get().strip()
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
        else:
            threading.Thread(target=self._tts_generate_sovits, args=(lines,), daemon=True).start()

    def _extract_audio_data(self, response):
        try:
            if hasattr(response, "get_audio_data"):
                ad = response.get_audio_data()
                if ad:
                    return ad if isinstance(ad, bytes) else ad.encode() if isinstance(ad, str) else ad
            if hasattr(response, "output") and response.output:
                output = response.output
                if isinstance(output, dict):
                    for key in ("audio", "audio_url", "url", "speech"):
                        if key in output and output[key]:
                            val = output[key]
                            if isinstance(val, str) and val.startswith("http"):
                                return requests.get(val, timeout=30).content
                            return val
                speech = getattr(output, "speech", None)
                if speech:
                    return speech
                audio_url = getattr(output, "audio_url", None) or getattr(output, "url", None)
                if audio_url:
                    return requests.get(audio_url, timeout=30).content
            if isinstance(response, dict):
                output = response.get("output", {})
                for key in ("audio", "audio_url", "url", "speech"):
                    if key in output and output[key]:
                        val = output[key]
                        if isinstance(val, str) and val.startswith("http"):
                            return requests.get(val, timeout=30).content
                        return val
                if "data" in response and isinstance(response["data"], (bytes, bytearray)):
                    return response["data"]
        except Exception as e:
            self._tts_log_msg(f"[DEBUG] 提取音频数据异常: {e}")
        return None

    def _tts_generate_bailian(self, lines):
        try:
            from dashscope.audio.tts import SpeechSynthesizer
        except ImportError:
            self._tts_log_msg("错误: dashscope 未安装！请 pip install dashscope")
            self.root.after(0, lambda: self.tts_gen_btn.configure(state="normal", text="一键批量生成音频"))
            return
        import dashscope
        dashscope.api_key = self.config.get("bailian_api_key", "")
        if not dashscope.api_key:
            self._tts_log_msg("错误: 请先配置百炼 API Key！")
            self.root.after(0, lambda: self.tts_gen_btn.configure(state="normal", text="一键批量生成音频"))
            return

        voice_display = self.tts_voice_var.get()
        voice = self.tts_voice_map.get(voice_display, "sambert-zhichu-v1")
        custom_model = self.tts_custom_model_var.get().strip()
        model = custom_model if custom_model else voice

        out_dir = self._get_output_dir("output_audio")
        os.makedirs(out_dir, exist_ok=True)
        prefix = self._get_project_prefix()
        self._tts_log_msg(f"百炼 TTS 引擎: {model}")
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
            self._tts_log_msg(f"[{i}/{len(lines)}] 生成中: {text[:30]}...")

            audio_data = None
            for sample_rate in [48000, 16000]:
                try:
                    response = SpeechSynthesizer.call(model=model, text=text, sample_rate=sample_rate)
                    audio_data = self._extract_audio_data(response)
                    if audio_data:
                        break
                except Exception:
                    continue
            if audio_data:
                fname = self._shot_name(i, ".wav")
                out_path = os.path.join(out_dir, fname)
                with open(out_path, "wb") as f:
                    if isinstance(audio_data, str):
                        f.write(base64.b64decode(audio_data))
                    else:
                        f.write(audio_data)
                self._tts_log_msg(f"[{i}/{len(lines)}] 已保存: {fname}")
                success += 1
            else:
                self._tts_log_msg(f"[{i}/{len(lines)}] 跳过: 当前音色无响应")
                fail += 1
            time.sleep(0.3)

        self._tts_log_msg("=" * 40)
        self._tts_log_msg(f"完成: 成功 {success}，失败 {fail}")
        self._tts_log_msg(f"音频保存至: {out_dir}")
        self.root.after(0, lambda: self.tts_gen_btn.configure(state="normal", text="一键批量生成音频"))
        if success > 0:
            messagebox.showinfo("完成", f"音频生成完成！\n成功: {success}\n保存至: {out_dir}")

    def _tts_generate_sovits(self, lines):
        import subprocess
        api_url = self.sovits_url_var.get().strip().rstrip("/")
        if not api_url:
            self._tts_log_msg("错误: 请填写 VibeVoice API 地址！")
            self.root.after(0, lambda: self.tts_gen_btn.configure(state="normal", text="一键批量生成音频"))
            return

        character = self.sovits_character_var.get().strip()
        emotion = self.sovits_emotion_var.get().strip()
        if not character:
            self._tts_log_msg("错误: 请填写角色名称！")
            self.root.after(0, lambda: self.tts_gen_btn.configure(state="normal", text="一键批量生成音频"))
            return

        out_dir = self._get_output_dir("output_audio")
        os.makedirs(out_dir, exist_ok=True)
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
                    self.root.after(0, lambda: self.tts_gen_btn.configure(state="normal", text="一键批量生成音频"))
                    return
            else:
                self._tts_log_msg(f"[自动化] 未找到脚本: {bat_path}")
                self.root.after(0, lambda: self.tts_gen_btn.configure(state="normal", text="一键批量生成音频"))
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
                self.root.after(0, lambda: self.tts_gen_btn.configure(state="normal", text="一键批量生成音频"))
                return
        else:
            self._tts_log_msg("[自动化] VibeVoice 已在线")

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
            self._tts_log_msg(f"[{i}/{len(lines)}] 生成中: {text[:30]}...")

            character_id = self._char_name_to_id.get(character, character)
            params = {"character_id": character_id, "text": text, "emotion": emotion or "平静",
                      "top_k": 5, "top_p": 0.9, "temperature": 0.75, "text_split_method": "cut5"}
            try:
                resp = requests.post(synth_url, json=params, timeout=120)
                if resp.status_code == 200 and resp.content:
                    fname = self._shot_name(i, ".wav")
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
                                out_path = os.path.join(out_dir, f"shot_{i}.wav")
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
        self.root.after(0, lambda: self.tts_gen_btn.configure(state="normal", text="一键批量生成音频"))
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
        base_url = self.api_url_var.get().strip().rstrip("/")
        api_key = self.api_key_var.get().strip()
        model = self.api_model_var.get().strip()
        if not base_url or not api_key:
            self._script_error("错误：请先在「全局设置」中配置 Base URL 和 API Key。")
            return
        is_anthropic = "/anthropic" in base_url or base_url.endswith("/anthropic")
        try:
            headers = {"Content-Type": "application/json"}
            if is_anthropic:
                headers["x-api-key"] = api_key
                headers["anthropic-version"] = "2023-06-01"
                url = f"{base_url}/v1/messages"
                payload = {"model": model, "max_tokens": 4096, "system": SYSTEM_PROMPT,
                           "messages": [{"role": "user", "content": idea}]}
            else:
                headers["Authorization"] = f"Bearer {api_key}"
                url = f"{base_url}/chat/completions"
                payload = {"model": model, "temperature": 0.8, "max_tokens": 4096,
                           "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                                        {"role": "user", "content": idea}]}

            self._update_script_text("正在请求 API...\n")
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            if response.status_code == 200:
                result = response.json()
                content = result["content"][0]["text"] if is_anthropic else result["choices"][0]["message"]["content"]
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
            self.root.after(0, lambda: self.generate_btn.configure(state="normal", text="生成动态镜头脚本"))

    def _update_script_text(self, text):
        self.root.after(0, lambda: (self.script_output.delete("1.0", "end"),
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
        for idx, src in enumerate(self.selected_files, 1):
            try:
                fn = os.path.basename(src)
                name, _ = os.path.splitext(fn)
                out_folder = os.path.join(self.output_dir, name)
                os.makedirs(out_folder, exist_ok=True)
                with Image.open(src) as img:
                    w, h = img.size
                    gw, gh = w // 3, h // 3
                    n = 1
                    for r in range(3):
                        for c in range(3):
                            crop = img.crop((c * gw, r * gh, (c + 1) * gw, (r + 1) * gh))
                            crop.save(os.path.join(out_folder, f"{n}.jpg"), quality=95)
                            n += 1
                ok += 1
            except Exception as e:
                self.log(f"[{idx}] FAIL - {e}"); fail += 1
        self.log(f"九宫格切分完成: 成功 {ok}，失败 {fail}")
        if ok:
            messagebox.showinfo("完成", f"九宫格切分完成!\n成功: {ok} 张\n失败: {fail} 张")

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
    app = BatchProcessor()
    app.root.mainloop()


if __name__ == "__main__":
    main()
