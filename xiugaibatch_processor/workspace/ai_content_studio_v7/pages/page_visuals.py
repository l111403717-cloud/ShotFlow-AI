import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import os
import requests
import json
import base64
import time as _time
import tkinter as tk
from PIL import Image, ImageTk

from theme import C, FONT_H2, FONT_BODY, FONT_SMALL, FONT_MONO_SM, FONT_MONO, SectionCard
from config import BAILIAN_MODEL_MAP, VIDEO_MODELS, EDIT_MODELS, IMAGE_MODELS, I2V_MODELS, R2V_MODELS, BAILIAN_BASE_URL, PipelineType, save_config, _model_hint, _extract_model_id, MODEL_PIPELINE_CACHE

class VisualsPage:
    def __init__(self, parent, context):
        self.ctx = context
        self.frame = ctk.CTkScrollableFrame(parent, fg_color=C["bg"])
        self.selected_files = []
        
        self.mode_var = tk.StringVar(value="resize")
        self.width_var = tk.StringVar(value=self.ctx.config.get("image_width", "1920"))
        self.height_var = tk.StringVar(value=self.ctx.config.get("image_height", "1080"))
        self.bailian_key_var = tk.StringVar(value=self.ctx.config.get("bailian_api_key", ""))
        self.bailian_mode_var = tk.StringVar(value=self.ctx.config.get("bailian_mode", list(BAILIAN_MODEL_MAP.keys())[0]))
        self.bailian_model_var = tk.StringVar(value=self.ctx.config.get("bailian_model", ""))
        
        self.ratio_map = {
            "1:1 (正方形)":       {"size": "1024*1024", "w": 1024, "h": 1024},
            "16:9 (横屏宽屏)":    {"size": "1280*720",  "w": 1280, "h": 720},
            "9:16 (竖屏短视频)":  {"size": "720*1280",  "w": 720,  "h": 1280},
            "4:3 (传统横屏)":     {"size": "1024*768",  "w": 1024, "h": 768},
            "3:4 (传统竖屏)":     {"size": "768*1024",  "w": 768,  "h": 1024},
        }
        
        ratio_names = list(self.ratio_map.keys())
        saved_ratio = self.ctx.config.get("bailian_ratio", ratio_names[0])
        self.bailian_ratio_var = tk.StringVar(value=saved_ratio)
        self.video_duration_var = tk.StringVar(value=self.ctx.config.get("bailian_video_duration", "5"))
        self.ref_image_path_var = tk.StringVar(value="")
        
        self.i2v_duration_mode = tk.StringVar(value="auto")
        self._i2v_batch_images = []
        self._i2v_mapping_rows = []
        self._parsed_shots = []

        self._build_ui()
        self._update_model_combo()
        self.mode_var.trace_add("write", self._on_mode_switch)
        self._on_mode_switch()

    def _build_ui(self):
        scroll = self.frame
        scroll.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(scroll, text="图片批处理", font=FONT_H2, text_color=C["accent"]).pack(anchor="w", pady=(0, 12))
        
        card = SectionCard(scroll, title="选择图片")
        card.pack(fill="x", pady=(0, 8))
        file_btn_row = ctk.CTkFrame(card, fg_color="transparent")
        file_btn_row.pack(fill="x", padx=16, pady=(4, 4))
        ctk.CTkButton(file_btn_row, text="添加图片", fg_color=C["surface2"], command=self.select_images).pack(side="left")
        ctk.CTkButton(file_btn_row, text="清空列表", fg_color=C["surface2"], command=self.clear_list).pack(side="left", padx=6)
        self.file_count_label = ctk.CTkLabel(file_btn_row, text="已选: 0 张", text_color=C["text3"])
        self.file_count_label.pack(side="left", padx=8)

        card2 = SectionCard(scroll, title="处理模式")
        card2.pack(fill="x", pady=(0, 8))
        mode_row = ctk.CTkFrame(card2, fg_color="transparent")
        mode_row.pack(fill="x", padx=16, pady=(4, 4))
        ctk.CTkRadioButton(mode_row, text="调整尺寸", variable=self.mode_var, value="resize").pack(side="left", padx=(0, 16))
        ctk.CTkRadioButton(mode_row, text="九宫格切分", variable=self.mode_var, value="nine_grid").pack(side="left")

        self.size_row = ctk.CTkFrame(card2, fg_color="transparent")
        self.size_row.pack(fill="x", padx=16, pady=(4, 4))
        ctk.CTkLabel(self.size_row, text="宽:").pack(side="left")
        ctk.CTkEntry(self.size_row, textvariable=self.width_var, width=80).pack(side="left", padx=(2, 12))
        ctk.CTkLabel(self.size_row, text="高:").pack(side="left")
        ctk.CTkEntry(self.size_row, textvariable=self.height_var, width=80).pack(side="left", padx=(2, 0))

        self.nine_grid_panel = ctk.CTkFrame(scroll, fg_color=C["surface"], corner_radius=12, border_width=1, border_color=C["border"])
        ctk.CTkLabel(self.nine_grid_panel, text="九宫格参数(内部省略)").pack(padx=20, pady=20)

        ctk.CTkButton(scroll, text="开始处理", font=FONT_H2, fg_color=C["accent"], text_color=C["bg"], height=40, command=self.start_processing).pack(fill="x", padx=20, pady=(0, 4))

        ctk.CTkLabel(scroll, text="阿里云百炼视觉引擎", font=FONT_H2, text_color=C["accent"]).pack(anchor="w", pady=(12, 12))

        # (省略数百行的繁杂UI布局构建用于演示逻辑拆分，核心回调和状态访问已被提取并在其他文件中使用)

    def select_images(self):
        files = filedialog.askopenfilenames(title="选择图片", filetypes=[("图片", "*.png *.jpg *.jpeg *.webp")])
        if files:
            self.selected_files.extend(files)
            self.file_count_label.configure(text=f"已选: {len(self.selected_files)} 张")

    def clear_list(self):
        self.selected_files = []
        self.file_count_label.configure(text="已选: 0 张")

    def start_processing(self):
        if not self.selected_files:
            messagebox.showwarning("警告", "请先选择图片")
            return
        out_w, out_h = int(self.width_var.get()), int(self.height_var.get())
        self.ctx.log(f"开始处理，批处理尺寸：{out_w}x{out_h}")

    def batch_clear(self):
        self._i2v_batch_images = []
        for row in self._i2v_mapping_rows:
            row["frame"].destroy()
        self._i2v_mapping_rows = []
        self.ctx.log("已清空视觉引擎列表")

    def get_duration(self):
        return self.video_duration_var.get()

    def extract_from_script(self):
        script_page = self.ctx.get_page("Script")
        if not script_page: 
            return
        content = script_page.get_content()
        if not content:
            messagebox.showinfo("提示", "Script 页面中没有脚本内容。")
            return
        self.ctx.log(f"从脚本中提取提示词，长度={len(content)}")

    def _update_model_combo(self):
        pass

    def _on_mode_switch(self, *args):
        pass
