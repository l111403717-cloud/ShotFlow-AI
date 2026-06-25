"""Visuals page mixin — image processing + Bailian + batch i2v + MiMo agent"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import requests
import json
import os
import time
import base64
import re
from PIL import Image, ImageTk

from ..constants import (C, FONT_TITLE, FONT_H2, FONT_BODY, FONT_MONO, FONT_MONO_SM, FONT_SMALL,
                         PAD_MD, PAD_LG, PAD_SM, CORNER_RADIUS, CORNER_RADIUS_LG,
                         BAILIAN_BASE_URL, BAILIAN_MODEL_MAP, VIDEO_MODELS, IMAGE_MODELS,
                         EDIT_MODELS, I2V_MODELS, R2V_MODELS,
                         PipelineType, get_pipeline_type, MODEL_PIPELINE_CACHE,
                         _model_hint, _extract_model_id)
from ..ui import SectionCard


class VisualsMixin:

    def _build_page_visuals(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color=C["bg"],
            scrollbar_button_color=C["border"], scrollbar_button_hover_color=C["text3"])
        scroll.pack(fill="both", expand=True, padx=PAD_MD, pady=PAD_MD)

        # Image batch processing
        ctk.CTkLabel(scroll, text="图片批处理", font=FONT_H2, text_color=C["accent"]).pack(anchor="w", pady=(0, 12))

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

        # Nine grid panel
        self.nine_grid_panel = ctk.CTkFrame(scroll, fg_color=C["surface"], corner_radius=12,
                                             border_width=1, border_color=C["border"])
        self.ng_col_lines = [0.333, 0.667]
        self.ng_row_lines = [0.333, 0.667]
        self.ng_dragging = None; self.ng_image_scale = 1.0
        self.ng_img_offset = (0, 0); self.ng_img_display_size = (0, 0)

        ng_header = ctk.CTkFrame(self.nine_grid_panel, fg_color="transparent")
        ng_header.pack(fill="x", padx=12, pady=(8, 4))
        ctk.CTkLabel(ng_header, text="九宫格可视化切分", font=FONT_H2, text_color=C["accent"]).pack(side="left")
        self.ng_info_label = ctk.CTkLabel(ng_header, text="请先添加图片", font=FONT_SMALL, text_color=C["text3"])
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

        self.ng_pixel_label = ctk.CTkLabel(self.nine_grid_panel, text="像素坐标: --",
                                            font=FONT_MONO_SM, text_color=C["text3"])
        self.ng_pixel_label.pack(anchor="w", padx=12, pady=(0, 4))

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

        preview_row = ctk.CTkFrame(self.nine_grid_panel, fg_color="transparent")
        preview_row.pack(fill="x", padx=12, pady=(0, 8))
        ctk.CTkLabel(preview_row, text="切分预览:", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w", pady=(0, 4))
        preview_grid = ctk.CTkFrame(preview_row, fg_color="transparent")
        preview_grid.pack(anchor="w")
        self.ng_preview_labels = []
        for i in range(9):
            lbl = ctk.CTkLabel(preview_grid, text="", width=60, height=60, fg_color=C["surface2"], corner_radius=4)
            lbl.grid(row=i // 3, column=i % 3, padx=2, pady=2)
            self.ng_preview_labels.append(lbl)

        self.mode_var.trace_add("write", self._on_mode_switch)
        self._on_mode_switch()

        ctk.CTkButton(scroll, text="开始处理", font=FONT_H2, fg_color=C["accent"], text_color=C["bg"],
                       hover_color=C["accent2"], corner_radius=12, height=40,
                       command=self.start_processing).pack(fill="x", padx=20, pady=(0, 4))
        ctk.CTkButton(scroll, text="打开输出目录", font=FONT_SMALL, fg_color=C["surface2"],
                       hover_color=C["border"], text_color=C["text2"], corner_radius=8, height=28,
                       command=self.open_output_dir).pack(anchor="w", padx=20, pady=(0, 16))

        # Bailian visual engine
        ctk.CTkLabel(scroll, text="阿里云百炼视觉引擎", font=FONT_H2, text_color=C["accent"]).pack(anchor="w", pady=(0, 12))

        card = SectionCard(scroll, title="百炼 API Key")
        card.pack(fill="x", pady=(0, 8))
        self.bailian_key_var = tk.StringVar(value=self.config.get("bailian_api_key", ""))
        self.bailian_key_entry = ctk.CTkEntry(card, textvariable=self.bailian_key_var, show="*",
                                               font=FONT_MONO, fg_color=C["surface2"], border_color=C["border"], corner_radius=8)
        self.bailian_key_entry.pack(fill="x", padx=16, pady=(4, 4))
        key_row = ctk.CTkFrame(card, fg_color="transparent")
        key_row.pack(fill="x", padx=16, pady=(0, 10))
        self.bailian_key_visible = tk.BooleanVar(value=False)
        ctk.CTkButton(key_row, text="显示/隐藏", width=80, font=FONT_SMALL,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text2"], corner_radius=6, height=28,
                       command=self.toggle_bailian_key_vis).pack(side="left")
        ctk.CTkLabel(key_row, text="在阿里云百炼控制台获取", font=FONT_SMALL, text_color=C["text3"]).pack(side="left", padx=8)

        card = SectionCard(scroll, title="生成模式")
        card.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(card, text="第一步：选择模式类别", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w", padx=16, pady=(4, 0))
        self.bailian_mode_var = tk.StringVar(value=self.config.get("bailian_mode", list(BAILIAN_MODEL_MAP.keys())[0]))
        self.bailian_mode_combo = ctk.CTkComboBox(card, variable=self.bailian_mode_var,
            values=list(BAILIAN_MODEL_MAP.keys()), font=FONT_BODY, dropdown_font=FONT_BODY,
            fg_color=C["surface2"], border_color=C["border"], button_color=C["border"],
            button_hover_color=C["text3"], corner_radius=8, command=self._on_mode_changed)
        self.bailian_mode_combo.pack(fill="x", padx=16, pady=(2, 8))
        ctk.CTkLabel(card, text="第二步：选择具体模型", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w", padx=16)
        self.bailian_model_var = tk.StringVar(value=self.config.get("bailian_model", ""))
        self.bailian_model_combo = ctk.CTkComboBox(card, variable=self.bailian_model_var,
            values=[], font=FONT_MONO, fg_color=C["surface2"], border_color=C["border"],
            button_color=C["border"], button_hover_color=C["text3"], corner_radius=8, command=self._on_model_changed)
        self.bailian_model_combo.pack(fill="x", padx=16, pady=(2, 12))
        self.bailian_info_label = ctk.CTkLabel(card, text="", font=FONT_MONO_SM, text_color=C["text3"])
        self.bailian_info_label.pack(anchor="w", padx=16, pady=(0, 4))
        self._update_model_combo()

        # Ratio
        card = SectionCard(scroll, title="画面比例")
        card.pack(fill="x", pady=(0, 8))
        self.ratio_map = {
            "1:1 (正方形)": {"size": "1024*1024", "w": 1024, "h": 1024},
            "16:9 (横屏宽屏)": {"size": "1280*720", "w": 1280, "h": 720},
            "9:16 (竖屏短视频)": {"size": "720*1280", "w": 720, "h": 1280},
            "4:3 (传统横屏)": {"size": "1024*768", "w": 1024, "h": 768},
            "3:4 (传统竖屏)": {"size": "768*1024", "w": 768, "h": 1024},
            "3:2 (摄影横屏)": {"size": "1152*768", "w": 1152, "h": 768},
            "2:3 (摄影竖屏)": {"size": "768*1152", "w": 768, "h": 1152},
        }
        ratio_names = list(self.ratio_map.keys())
        saved_ratio = self.config.get("bailian_ratio", ratio_names[0])
        if saved_ratio not in self.ratio_map: saved_ratio = ratio_names[0]
        self.bailian_ratio_var = tk.StringVar(value=saved_ratio)
        self.bailian_ratio_combo = ctk.CTkComboBox(card, variable=self.bailian_ratio_var,
            values=ratio_names, font=FONT_BODY, dropdown_font=FONT_BODY,
            fg_color=C["surface2"], border_color=C["border"], button_color=C["border"],
            button_hover_color=C["text3"], corner_radius=8, command=self._on_ratio_changed)
        self.bailian_ratio_combo.pack(fill="x", padx=16, pady=(4, 4))
        self.ratio_hint = ctk.CTkLabel(card, text=f"输出尺寸: {self.ratio_map[saved_ratio]['size']}",
                                        font=FONT_MONO_SM, text_color=C["text3"])
        self.ratio_hint.pack(anchor="w", padx=16, pady=(0, 12))

        # Video settings
        self.video_settings_frame = SectionCard(scroll, title="视频设置")
        ctk.CTkLabel(self.video_settings_frame, text="视频时长 (秒):", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w", padx=16, pady=(4, 0))
        dur_row = ctk.CTkFrame(self.video_settings_frame, fg_color="transparent")
        dur_row.pack(fill="x", padx=16, pady=(2, 8))
        self.video_duration_var = tk.StringVar(value=self.config.get("bailian_video_duration", "5"))
        ctk.CTkEntry(dur_row, textvariable=self.video_duration_var, width=80, font=FONT_MONO,
                      fg_color=C["surface2"], border_color=C["border"], corner_radius=8).pack(side="left")
        ctk.CTkLabel(dur_row, text="秒  (建议 3~10)", font=FONT_SMALL, text_color=C["text3"]).pack(side="left", padx=8)

        self.pipeline_type_banner = ctk.CTkFrame(self.video_settings_frame, fg_color=C["green"],
                                                   corner_radius=8, height=36)
        self.pipeline_type_banner.pack(fill="x", padx=16, pady=(8, 4))
        self.pipeline_type_banner.pack_propagate(False)
        self.pipeline_type_label = ctk.CTkLabel(self.pipeline_type_banner,
            text="📝 Text-to-Video — 无需参考图，纯文本驱动", font=FONT_H2, text_color=C["bg"])
        self.pipeline_type_label.pack(expand=True)

        self.ref_image_frame = ctk.CTkFrame(self.video_settings_frame, fg_color="transparent")
        self.ref_image_frame.pack(fill="x", padx=0, pady=0)
        ctk.CTkLabel(self.ref_image_frame, text="参考图 (i2v/r2v/videoedit 必填):",
                     font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w", padx=16, pady=(4, 0))
        ref_row = ctk.CTkFrame(self.ref_image_frame, fg_color="transparent")
        ref_row.pack(fill="x", padx=16, pady=(2, 12))
        self.ref_image_path_var = tk.StringVar(value="")
        ctk.CTkEntry(ref_row, textvariable=self.ref_image_path_var, font=FONT_MONO_SM,
                      fg_color=C["surface2"], border_color=C["border"], corner_radius=8).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(ref_row, text="浏览", width=60, font=FONT_SMALL,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text"], corner_radius=6, height=30,
                       command=self._browse_ref_image).pack(side="left", padx=(6, 0))
        self._toggle_video_settings()

        # Prompt
        card = SectionCard(scroll, title="Prompt / 描述")
        card.pack(fill="x", pady=(0, 8))
        shot_row = ctk.CTkFrame(card, fg_color="transparent")
        shot_row.pack(fill="x", padx=16, pady=(4, 4))
        ctk.CTkButton(shot_row, text="从 Script 提取 Prompt", font=FONT_SMALL,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["blue"], corner_radius=6, height=28,
                       command=self._fill_prompt_from_tab1).pack(side="left")
        self._parsed_shots = []
        self.bailian_shot_combo = ctk.CTkComboBox(shot_row, values=["请先提取"], font=FONT_SMALL, width=140,
            dropdown_font=FONT_SMALL, fg_color=C["surface2"], border_color=C["border"],
            button_color=C["border"], button_hover_color=C["text3"], corner_radius=8, command=self._on_shot_selected)
        self.bailian_shot_combo.pack(side="left", padx=(8, 0))
        self.bailian_shot_combo.set("请先提取")
        self.bailian_prompt_input = ctk.CTkTextbox(card, height=80, font=FONT_BODY,
            fg_color=C["surface2"], text_color=C["text"], corner_radius=8,
            border_width=1, border_color=C["border"])
        self.bailian_prompt_input.pack(fill="x", padx=16, pady=(4, 8))

        gen_row = ctk.CTkFrame(scroll, fg_color="transparent")
        gen_row.pack(fill="x", padx=20, pady=(0, 8))
        self.bailian_gen_btn = ctk.CTkButton(gen_row, text="生成当前镜头", font=FONT_H2,
            fg_color=C["accent"], text_color=C["bg"], hover_color=C["accent2"],
            corner_radius=12, height=44, command=self.start_bailian_generate)
        self.bailian_gen_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.bailian_batch_btn = ctk.CTkButton(gen_row, text="批量生成所有镜头", font=FONT_BODY,
            fg_color=C["surface2"], text_color=C["accent"], hover_color=C["border"],
            corner_radius=12, height=44, command=self._batch_generate_all_shots)
        self.bailian_batch_btn.pack(side="left")
        ctk.CTkButton(scroll, text="打开输出目录", font=FONT_SMALL, fg_color=C["surface2"],
                       hover_color=C["border"], text_color=C["text2"], corner_radius=8, height=30,
                       command=self._open_bailian_output).pack(anchor="w", padx=20, pady=(0, 16))

        # Batch i2v module
        self.i2v_batch_card = SectionCard(scroll, title="批量图生视频 (Image-to-Video)")
        self.i2v_batch_card.pack(fill="x", padx=20, pady=(0, 16))

        top_action_row = ctk.CTkFrame(self.i2v_batch_card, fg_color="transparent")
        top_action_row.pack(fill="x", padx=16, pady=(8, 4))
        ctk.CTkButton(top_action_row, text="+ 添加图片", font=FONT_SMALL, width=80,
                       fg_color=C["accent"], hover_color=C["accent2"],
                       text_color=C["bg"], corner_radius=6, height=28,
                       command=self._i2v_batch_add_images).pack(side="left")
        ctk.CTkButton(top_action_row, text="清空", font=FONT_SMALL, width=50,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text2"], corner_radius=6, height=28,
                       command=self._i2v_batch_clear).pack(side="left", padx=4)
        ctk.CTkButton(top_action_row, text="从 Script 提取", font=FONT_SMALL, width=100,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["blue"], corner_radius=6, height=28,
                       command=self._i2v_extract_prompts_from_script).pack(side="left", padx=4)
        self.i2v_batch_count_label = ctk.CTkLabel(top_action_row, text="0 图 / 0 提示词",
                                                    font=FONT_SMALL, text_color=C["text3"])
        self.i2v_batch_count_label.pack(side="right")

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

        ctk.CTkLabel(self.i2v_batch_card, text="图片 ↔ 提示词对应关系:",
                     font=FONT_SMALL, text_color=C["text"]).pack(anchor="w", padx=16, pady=(8, 2))

        self.i2v_mapping_frame = ctk.CTkScrollableFrame(self.i2v_batch_card, fg_color=C["surface2"],
            corner_radius=8, border_width=1, border_color=C["border"], height=200)
        self.i2v_mapping_frame.pack(fill="x", padx=16, pady=(0, 8))

        header_row = ctk.CTkFrame(self.i2v_mapping_frame, fg_color="transparent")
        header_row.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(header_row, text="#", font=FONT_SMALL, text_color=C["text3"], width=30).pack(side="left")
        ctk.CTkLabel(header_row, text="预览", font=FONT_SMALL, text_color=C["text3"], width=60).pack(side="left", padx=2)
        ctk.CTkLabel(header_row, text="提示词", font=FONT_SMALL, text_color=C["text3"]).pack(side="left", padx=2, fill="x", expand=True)
        ctk.CTkLabel(header_row, text="时长", font=FONT_SMALL, text_color=C["text3"], width=40).pack(side="left", padx=2)
        ctk.CTkLabel(header_row, text="操作", font=FONT_SMALL, text_color=C["text3"], width=60).pack(side="left", padx=2)

        self.i2v_empty_label = ctk.CTkLabel(self.i2v_mapping_frame, text="请先添加图片",
                                              font=FONT_SMALL, text_color=C["text3"])
        self.i2v_empty_label.pack(pady=20)

        bottom_action_row = ctk.CTkFrame(self.i2v_batch_card, fg_color="transparent")
        bottom_action_row.pack(fill="x", padx=16, pady=(4, 12))
        ctk.CTkButton(bottom_action_row, text="MiMo 智能优化全部", font=FONT_SMALL, width=120,
                       fg_color=C["blue"], hover_color="#3AA5E0",
                       text_color="#FFF", corner_radius=6, height=32,
                       command=self._i2v_mimo_analyze_all).pack(side="left")
        ctk.CTkButton(bottom_action_row, text="开始批量生成", font=FONT_H2,
                       fg_color=C["accent"], text_color=C["bg"],
                       hover_color=C["accent2"], corner_radius=10, height=36,
                       command=self._start_i2v_batch_generate).pack(side="right")

        self._i2v_batch_images = []
        self._i2v_mapping_rows = []
        self.bailian_log = self.global_log

    # ---- Image processing ----
    def log(self, msg):
        print(f"[{time.strftime('%H:%M:%S')}] {msg}")

    def select_images(self):
        files = filedialog.askopenfilenames(title="选择图片文件",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"), ("所有文件", "*.*")])
        if files:
            self.selected_files.extend(files)
            self.log(f"已添加 {len(files)} 个文件")
            self.file_count_label.configure(text=f"已选: {len(self.selected_files)} 张")
            if self.mode_var.get() == "nine_grid" and files:
                self._ng_load_preview_image(files[0])

    def clear_list(self):
        self.selected_files = []
        self.log("已清空文件列表")
        self.file_count_label.configure(text="已选: 0 张")

    def open_output_dir(self):
        if self.output_dir and os.path.exists(self.output_dir): os.startfile(self.output_dir)

    def start_processing(self):
        if not self.selected_files:
            messagebox.showwarning("警告", "请先选择要处理的图片！"); return
        self.output_dir = filedialog.askdirectory(title="选择输出目录")
        if not self.output_dir: return
        self.config["image_width"] = self.width_var.get()
        self.config["image_height"] = self.height_var.get()
        from ..config import save_config
        save_config(self.config)
        mode = self.mode_var.get()
        if mode == "resize":
            try: out_w, out_h = int(self.width_var.get()), int(self.height_var.get())
            except ValueError: messagebox.showerror("错误", "请输入有效的数字！"); return
            self.log(f"开始调整尺寸，共 {len(self.selected_files)} 张，目标 {out_w}x{out_h}")
            threading.Thread(target=self.process_batch_resize, args=(out_w, out_h), daemon=True).start()
        else:
            self.log(f"开始九宫格切分，共 {len(self.selected_files)} 张")
            threading.Thread(target=self.split_to_nine_grid, daemon=True).start()

    def process_batch_resize(self, out_w, out_h):
        ok, fail = 0, 0
        for i, src in enumerate(self.selected_files, 1):
            try:
                fn = os.path.basename(src); name, ext = os.path.splitext(fn)
                dst = os.path.join(self.output_dir, f"{name}_{out_w}x{out_h}_processed{ext}")
                with Image.open(src) as img: img.resize((out_w, out_h), Image.LANCZOS).save(dst)
                ok += 1
            except Exception as e: self.log(f"[{i}] FAIL {fn} - {e}"); fail += 1
        self.log(f"调整尺寸完成: 成功 {ok}，失败 {fail}")
        if ok: messagebox.showinfo("完成", f"处理完成!\n成功: {ok} 个\n失败: {fail} 个")

    def split_to_nine_grid(self):
        ok, fail = 0, 0
        col_lines = list(self.ng_col_lines); row_lines = list(self.ng_row_lines)
        for idx, src in enumerate(self.selected_files, 1):
            try:
                fn = os.path.basename(src); name, _ = os.path.splitext(fn)
                out_folder = os.path.join(self.output_dir, name)
                os.makedirs(out_folder, exist_ok=True)
                with Image.open(src) as img:
                    w, h = img.size
                    c1, c2 = int(w * col_lines[0]), int(w * col_lines[1])
                    r1, r2 = int(h * row_lines[0]), int(h * row_lines[1])
                    coords = [(0,0,c1,r1),(c1,0,c2,r1),(c2,0,w,r1),(0,r1,c1,r2),(c1,r1,c2,r2),(c2,r1,w,r2),(0,r2,c1,h),(c1,r2,c2,h),(c2,r2,w,h)]
                    for n, (left, upper, right, lower) in enumerate(coords, 1):
                        crop = img.crop((left, upper, right, lower))
                        if crop.mode in ('RGBA', 'P', 'LA'): crop = crop.convert('RGB')
                        crop.save(os.path.join(out_folder, f"{n}.jpg"), quality=95)
                ok += 1
            except Exception as e: self.log(f"[{idx}] FAIL - {e}"); fail += 1
        self.log(f"九宫格切分完成: 成功 {ok}，失败 {fail}")
        if ok: messagebox.showinfo("完成", f"九宫格切分完成!\n成功: {ok} 张\n失败: {fail} 张")

    # ---- Nine grid visualization ----
    def _on_mode_switch(self, *args):
        mode = self.mode_var.get()
        if mode == "nine_grid":
            self.size_row.pack_forget()
            self.nine_grid_panel.pack(fill="both", expand=True, padx=0, pady=(0, 8))
            if self.selected_files: self._ng_load_preview_image(self.selected_files[0])
        else:
            self.nine_grid_panel.pack_forget()
            self.size_row.pack(fill="x", padx=16, pady=(4, 4))

    def _ng_load_preview_image(self, path):
        try:
            self.ng_current_image = Image.open(path); self.ng_current_image_path = path
            w, h = self.ng_current_image.size
            self.ng_info_label.configure(text=f"{os.path.basename(path)} | {w}×{h}px")
            self._ng_redraw(); self._ng_update_preview()
        except Exception as e: self.ng_info_label.configure(text=f"加载失败: {e}")

    def _ng_redraw(self):
        if not hasattr(self, "ng_current_image") or not self.ng_current_image: return
        self.ng_canvas.update_idletasks()
        canvas_w, canvas_h = self.ng_canvas.winfo_width(), self.ng_canvas.winfo_height()
        if canvas_w < 10 or canvas_h < 10: return
        img_w, img_h = self.ng_current_image.size
        self.ng_image_scale = min(canvas_w / img_w, canvas_h / img_h, 1.0)
        display_w, display_h = int(img_w * self.ng_image_scale), int(img_h * self.ng_image_scale)
        resized = self.ng_current_image.resize((display_w, display_h), Image.LANCZOS)
        self.ng_photo = ImageTk.PhotoImage(resized)
        offset_x, offset_y = (canvas_w - display_w) // 2, (canvas_h - display_h) // 2
        self.ng_img_offset = (offset_x, offset_y); self.ng_img_display_size = (display_w, display_h)
        self.ng_canvas.delete("all")
        self.ng_canvas.create_image(offset_x, offset_y, anchor=tk.NW, image=self.ng_photo)
        self._ng_draw_grid_lines()

    def _ng_draw_grid_lines(self):
        ox, oy = self.ng_img_offset; dw, dh = self.ng_img_display_size
        c1, c2 = ox + int(dw * self.ng_col_lines[0]), ox + int(dw * self.ng_col_lines[1])
        r1, r2 = oy + int(dh * self.ng_row_lines[0]), oy + int(dh * self.ng_row_lines[1])
        for x in [c1, c2]: self.ng_canvas.create_line(x, oy, x, oy + dh, fill="#FF4444", width=2, dash=(6, 4), tags="grid")
        for y in [r1, r2]: self.ng_canvas.create_line(ox, y, ox + dw, y, fill="#FF4444", width=2, dash=(6, 4), tags="grid")
        img_w, img_h = self.ng_current_image.size
        px_c1, px_c2 = int(img_w * self.ng_col_lines[0]), int(img_w * self.ng_col_lines[1])
        px_r1, px_r2 = int(img_h * self.ng_row_lines[0]), int(img_h * self.ng_row_lines[1])
        self.ng_pixel_label.configure(text=f"像素坐标 | 列: {px_c1}, {px_c2} | 行: {px_r1}, {px_r2} | 每格: {px_c1}×{px_r1} / {px_c2-px_c1}×{px_r2-px_r1} / {img_w-px_c2}×{img_h-px_r2}")

    def _ng_on_mouse_down(self, event):
        if not hasattr(self, "ng_current_image") or not self.ng_current_image: return
        ox, oy = self.ng_img_offset; dw, dh = self.ng_img_display_size
        for i, line in enumerate(self.ng_col_lines):
            if abs(event.x - (ox + int(dw * line))) < 10: self.ng_dragging = f"col_{i}"; return
        for i, line in enumerate(self.ng_row_lines):
            if abs(event.y - (oy + int(dh * line))) < 10: self.ng_dragging = f"row_{i}"; return

    def _ng_on_mouse_drag(self, event):
        if not self.ng_dragging: return
        ox, oy = self.ng_img_offset; dw, dh = self.ng_img_display_size
        if self.ng_dragging.startswith("col_"):
            idx = int(self.ng_dragging.split("_")[1])
            self.ng_col_lines[idx] = max(0.05, min(0.95, (event.x - ox) / dw if dw > 0 else 0.333))
        elif self.ng_dragging.startswith("row_"):
            idx = int(self.ng_dragging.split("_")[1])
            self.ng_row_lines[idx] = max(0.05, min(0.95, (event.y - oy) / dh if dh > 0 else 0.333))
        self._ng_update_line_vars(); self._ng_redraw()

    def _ng_on_mouse_up(self, event):
        if self.ng_dragging: self.ng_dragging = None; self._ng_update_preview()

    def _ng_on_mouse_move(self, event):
        if not hasattr(self, "ng_current_image") or not self.ng_current_image: return
        ox, oy = self.ng_img_offset; dw, dh = self.ng_img_display_size
        img_w, img_h = self.ng_current_image.size; scale = self.ng_image_scale
        rel_x, rel_y = event.x - ox, event.y - oy
        if 0 <= rel_x <= dw and 0 <= rel_y <= dh:
            px, py = int(rel_x / scale), int(rel_y / scale)
            near_line = ""
            for i, line in enumerate(self.ng_col_lines):
                if abs(rel_x - int(dw * line)) < 8: near_line = f" [← 拖拽列线{i+1}]"
            for i, line in enumerate(self.ng_row_lines):
                if abs(rel_y - int(dh * line)) < 8: near_line = f" [← 拖拽行线{i+1}]"
            self.ng_pixel_label.configure(text=f"鼠标: ({px}, {py}) | 图片: {img_w}×{img_h}{near_line}")
        else: self._ng_draw_grid_lines()

    def _ng_apply_manual(self):
        try:
            self.ng_col_lines[0] = float(self.ng_col1_var.get().replace("%", "")) / 100
            self.ng_col_lines[1] = float(self.ng_col2_var.get().replace("%", "")) / 100
            self.ng_row_lines[0] = float(self.ng_row1_var.get().replace("%", "")) / 100
            self.ng_row_lines[1] = float(self.ng_row2_var.get().replace("%", "")) / 100
            self._ng_redraw(); self._ng_update_preview()
        except ValueError: messagebox.showerror("错误", "请输入有效的百分比，如 33.3%")

    def _ng_reset_lines(self):
        self.ng_col_lines = [0.333, 0.667]; self.ng_row_lines = [0.333, 0.667]
        self._ng_update_line_vars(); self._ng_redraw(); self._ng_update_preview()

    def _ng_update_line_vars(self):
        self.ng_col1_var.set(f"{self.ng_col_lines[0]*100:.1f}%")
        self.ng_col2_var.set(f"{self.ng_col_lines[1]*100:.1f}%")
        self.ng_row1_var.set(f"{self.ng_row_lines[0]*100:.1f}%")
        self.ng_row2_var.set(f"{self.ng_row_lines[1]*100:.1f}%")

    def _ng_update_preview(self):
        if not hasattr(self, "ng_current_image") or not self.ng_current_image: return
        w, h = self.ng_current_image.size
        c1, c2 = int(w * self.ng_col_lines[0]), int(w * self.ng_col_lines[1])
        r1, r2 = int(h * self.ng_row_lines[0]), int(h * self.ng_row_lines[1])
        coords = [(0,0,c1,r1),(c1,0,c2,r1),(c2,0,w,r1),(0,r1,c1,r2),(c1,r1,c2,r2),(c2,r1,w,r2),(0,r2,c1,h),(c1,r2,c2,h),(c2,r2,w,h)]
        for i, (left, upper, right, lower) in enumerate(coords):
            try:
                crop = self.ng_current_image.crop((left, upper, right, lower))
                crop.thumbnail((55, 55), Image.LANCZOS)
                photo = ImageTk.PhotoImage(crop)
                self.ng_preview_labels[i].configure(image=photo, text="")
                self.ng_preview_labels[i].image = photo
            except Exception: pass

    # ---- Bailian visual engine ----
    def _on_mode_changed(self, value=None):
        self._update_model_combo(); self._toggle_video_settings(); self._save_bailian_config()

    def _on_model_changed(self, value=None):
        display = self.bailian_model_var.get()
        model_id = _extract_model_id(display)
        self.bailian_model_var.set(model_id)
        self.bailian_info_label.configure(text=model_id)
        self._toggle_video_settings(); self._save_bailian_config()

    def _on_ratio_changed(self, value=None):
        ratio = self.bailian_ratio_var.get()
        info = self.ratio_map.get(ratio, {})
        self.ratio_hint.configure(text=f"输出尺寸: {info.get('size', '')}")
        self._save_bailian_config()

    def _update_model_combo(self):
        mode = self.bailian_mode_var.get()
        models = BAILIAN_MODEL_MAP.get(mode, [])
        display_names = [_model_hint(m) for m in models]
        self._bailian_display_names = display_names; self._bailian_model_ids = models
        self.bailian_model_combo.configure(values=display_names)
        current_id = self.bailian_model_var.get()
        if current_id in models:
            idx = models.index(current_id); self.bailian_model_combo.set(display_names[idx])
        elif models:
            self.bailian_model_var.set(models[0]); self.bailian_model_combo.set(display_names[0])
        if hasattr(self, "bailian_info_label"):
            self.bailian_info_label.configure(text=self.bailian_model_var.get())

    def _toggle_video_settings(self):
        model = self.bailian_model_var.get()
        if model in VIDEO_MODELS:
            self.video_settings_frame.pack(fill="x", pady=(0, 8))
            pipeline_type = MODEL_PIPELINE_CACHE.get(model, PipelineType.IMAGE_GEN)
            type_labels = {
                PipelineType.TEXT_TO_VIDEO: ("📝 Text-to-Video", "无需参考图，纯文本驱动", C["green"]),
                PipelineType.IMAGE_TO_VIDEO: ("🖼️ Image-to-Video", "⚠️ 必须提供参考图！", C["warn"]),
                PipelineType.REF_TO_VIDEO: ("🎬 Reference-to-Video", "⚠️ 必须提供参考视频！", C["accent3"]),
                PipelineType.VIDEO_EDIT: ("✂️ Video Edit", "⚠️ 必须提供素材！", C["accent3"]),
            }
            label, hint, bg_color = type_labels.get(pipeline_type, ("❓ 未知", "", C["text3"]))
            self.pipeline_type_banner.configure(fg_color=bg_color)
            self.pipeline_type_label.configure(text=f"{label} — {hint}", text_color=C["bg"])
            if pipeline_type in (PipelineType.IMAGE_TO_VIDEO, PipelineType.REF_TO_VIDEO, PipelineType.VIDEO_EDIT):
                self.ref_image_frame.pack(fill="x", padx=0, pady=0)
            else: self.ref_image_frame.pack_forget()
        else: self.video_settings_frame.pack_forget()

    def _browse_ref_image(self):
        path = filedialog.askopenfilename(title="选择参考图片",
            filetypes=[("图片", "*.png *.jpg *.jpeg *.webp"), ("所有文件", "*.*")])
        if path: self.ref_image_path_var.set(path)

    def _fill_prompt_from_tab1(self):
        content = self.script_output.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo("提示", "Script 页面中没有脚本内容，请先生成镜头脚本。"); return
        shots = self._parse_script_shots(content)
        if not shots:
            messagebox.showinfo("提示", "未从脚本中找到 **英文 Prompt**: 关键词，请检查脚本格式。"); return
        self._parsed_shots = shots
        shot_labels = [s["label"] for s in shots]
        self.bailian_shot_combo.configure(values=shot_labels)
        self.bailian_shot_combo.set(shot_labels[0])
        self._apply_shot(0)
        self._bailian_log_msg(f"已解析 {len(shots)} 个镜头，可用下拉菜单切换")

    def _parse_script_shots(self, content):
        prompt_pattern = re.compile(r"(?:英文|English)\s*\*{0,2}\s*Prompt\s*\*{0,2}\s*[:：]\s*(.+)", re.IGNORECASE)
        duration_pattern = re.compile(r"(?:时长|時長|Duration)\s*\*{0,2}\s*[:：]\s*(\d+(?:\.\d+)?)\s*(?:s|秒|sec)?", re.IGNORECASE)
        raw_prompts, raw_durations = [], []
        for line in content.split("\n"):
            stripped = line.strip()
            if not stripped: continue
            pm = prompt_pattern.search(stripped)
            if pm:
                text = self._clean_prompt(pm.group(1))
                if text: raw_prompts.append(text)
                continue
            dm = duration_pattern.search(stripped)
            if dm: raw_durations.append(float(dm.group(1)))
        if not raw_prompts: return []
        shots = []
        for i, prompt in enumerate(raw_prompts):
            num = i + 1
            duration = raw_durations[i] if i < len(raw_durations) else None
            if duration is None: duration = self._estimate_duration(prompt)
            shots.append({"num": num, "label": f"镜头 {num}", "prompt": prompt, "duration": duration})
        return shots

    def _clean_prompt(self, raw_text):
        text = re.sub(r"\*+", "", raw_text).strip()
        literary = [r"\b(?:breathtaking|stunning|gorgeous|magnificent|exquisite)\b",
                    r"\b(?:masterpiece|award-winning|cinematic masterpiece)\b",
                    r"\b(?:unparalleled|extraordinary|sublime|ethereal)\b",
                    r"\b(?:captivating|mesmerizing|enchanting|awe-inspiring)\b"]
        for pat in literary: text = re.sub(pat, "", text, flags=re.IGNORECASE)
        text = re.sub(r"[,，]\s*[,，]+", ",", text)
        text = re.sub(r"\s{2,}", " ", text).strip().strip(",").strip("，")
        return text

    def _estimate_duration(self, prompt):
        if not prompt: return 5.0
        word_count = len(prompt.split())
        if word_count < 15: return 3.0
        elif word_count < 25: return 5.0
        elif word_count < 40: return 6.0
        else: return 8.0

    def _apply_shot(self, index):
        if not hasattr(self, "_parsed_shots") or index >= len(self._parsed_shots): return
        shot = self._parsed_shots[index]
        self.bailian_prompt_input.delete("1.0", "end")
        if shot["prompt"]: self.bailian_prompt_input.insert("end", shot["prompt"])
        self.video_duration_var.set(str(int(shot["duration"])))
        self._bailian_log_msg(f"已加载镜头 {shot['num']}: {shot['prompt'][:50]}... | 时长 {shot['duration']}s")

    def _on_shot_selected(self, choice):
        labels = [s["label"] for s in self._parsed_shots] if hasattr(self, "_parsed_shots") else []
        idx = labels.index(choice) if choice in labels else 0
        self._apply_shot(idx)

    def _batch_generate_all_shots(self):
        if not hasattr(self, "_parsed_shots") or not self._parsed_shots:
            messagebox.showinfo("提示", "请先点击「从 Script 提取 Prompt」解析镜头。"); return
        api_key = self.bailian_key_var.get().strip()
        if not api_key: messagebox.showwarning("提示", "请先填写百炼 API Key！"); return
        archived = self._archive_old_files(("output_video", "output_audio"))
        if archived: self._bailian_log_msg(f"[归档] 已将 {archived} 个旧文件移入 archive_history")
        model = self.bailian_model_var.get(); mode = self.bailian_mode_var.get()
        is_video = model in VIDEO_MODELS
        self.bailian_gen_btn.configure(state="disabled", text="批量生成中...")
        self._bailian_log_msg(f"开始批量生成 {len(self._parsed_shots)} 个镜头 (模式: {mode})")
        threading.Thread(target=self._batch_gen_worker, args=(api_key, model, is_video), daemon=True).start()

    def _batch_gen_worker(self, api_key, model, is_video):
        ok, fail = 0, 0
        if is_video and model in (EDIT_MODELS + I2V_MODELS + R2V_MODELS):
            ref_path = self.ref_image_path_var.get().strip()
            if not ref_path or not os.path.exists(ref_path):
                self._bailian_log_msg(f"错误: 模型 {model} 需要参考素材！")
                self.safe_after(lambda: self.bailian_gen_btn.configure(state="normal", text="生成当前镜头"))
                return
        for i, shot in enumerate(self._parsed_shots):
            if _bailian_circuit_open:
                self._bailian_log_msg(f"⚠️ 熔断已触发，中止剩余 {len(self._parsed_shots) - i} 个镜头"); break
            prompt = shot["prompt"]
            if not prompt: self._bailian_log_msg(f"[镜头 {shot['num']}] 跳过：无 Prompt"); fail += 1; continue
            self._bailian_log_msg(f"[镜头 {shot['num']}] 生成中: {prompt[:40]}... (时长 {shot['duration']}s)")
            try:
                if is_video:
                    ref_path = self.ref_image_path_var.get().strip()
                    self._bailian_generate_video(api_key, model, prompt, ref_path, str(int(shot["duration"])))
                else: self._bailian_generate_image(api_key, model, prompt)
                ok += 1
            except Exception as e:
                self._bailian_log_msg(f"[镜头 {shot['num']}] 失败: {e}"); fail += 1
        self._bailian_log_msg(f"{'='*30} 批量完成: 成功 {ok}，失败 {fail}")
        self.safe_after(lambda: self.bailian_gen_btn.configure(state="normal", text="生成当前镜头"))

    def _save_bailian_config(self):
        self.config["bailian_api_key"] = self.bailian_key_var.get().strip()
        self.config["bailian_mode"] = self.bailian_mode_var.get()
        self.config["bailian_model"] = self.bailian_model_var.get()
        self.config["bailian_ratio"] = self.bailian_ratio_var.get()
        self.config["bailian_video_duration"] = self.video_duration_var.get()
        from ..config import save_config
        save_config(self.config)

    def toggle_bailian_key_vis(self):
        self.bailian_key_visible.set(not self.bailian_key_visible.get())
        self.bailian_key_entry.configure(show="" if self.bailian_key_visible.get() else "*")

    def _bailian_log_msg(self, msg):
        ts = time.strftime("%H:%M:%S")
        self.safe_after(lambda: self.global_log.append(f"[{ts}] {msg}"))

    def _open_bailian_output(self):
        out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bailian_output")
        if os.path.exists(out_dir): os.startfile(out_dir)
        else: self._bailian_log_msg("输出目录尚未创建，生成后会自动创建。")

    pass  # _bailian_circuit_open defined below at module level

    def _bailian_check_response(self, resp):
        code = resp.status_code; body = resp.text.lower()
        if code == 429: return True, "API 触发限流 (HTTP 429)，请稍后再试或更换 Key。"
        quota_keywords = ["exceeded your current quota", "quota exceeded", "insufficient balance",
                          "insufficient_quota", "balance is not enough", "余额不足", "配额不足", "throttling", "rate limit"]
        if any(kw in body for kw in quota_keywords):
            return True, "百炼 API 免费算力已耗尽 / 余额不足，请更换 Key 或充值。"
        if code in (401, 403): return True, f"API Key 无效或已过期 (HTTP {code})，请检查百炼 Key。"
        return False, ""

    def _bailian_block(self, msg):
        _bailian_circuit_open = True
        import logging
        logging.error("百炼熔断: %s", msg)
        self._bailian_log_msg(f"⚠️ 熔断: {msg}")
        self.safe_after(lambda: messagebox.showerror("算力熔断", msg))
        self.safe_after(lambda: self.bailian_gen_btn.configure(state="disabled", text="⛔ 算力已耗尽"))

    def start_bailian_generate(self):
        if _bailian_circuit_open:
            messagebox.showwarning("熔断中", "百炼算力已耗尽，请更换 Key 或重启应用后重试。"); return
        api_key = self.bailian_key_var.get().strip()
        model = self.bailian_model_var.get().strip()
        prompt = self.bailian_prompt_input.get("1.0", "end").strip()
        if not api_key: messagebox.showwarning("提示", "请先填写百炼 API Key！"); return
        if not prompt: messagebox.showwarning("提示", "请输入 Prompt！"); return
        self._save_bailian_config()
        self.bailian_gen_btn.configure(state="disabled", text="生成中...")
        if model in IMAGE_MODELS:
            threading.Thread(target=self._bailian_generate_image, args=(api_key, model, prompt), daemon=True).start()
        else:
            ref_path = self.ref_image_path_var.get().strip()
            duration = self.video_duration_var.get().strip() or "5"
            threading.Thread(target=self._bailian_generate_video, args=(api_key, model, prompt, ref_path, duration), daemon=True).start()

    def _bailian_generate_image(self, api_key, model, prompt):
        self._bailian_log_msg(f"调用图像生成，模型: {model}")
        try:
            ratio_info = self.ratio_map.get(self.bailian_ratio_var.get(), {})
            img_size = ratio_info.get("size", "1024*1024")
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            if "qwen-image-2.0" in model:
                payload = {"model": model, "input": {"messages": [{"role": "user", "content": [{"text": prompt}]}]},
                           "parameters": {"size": img_size}}
                resp = requests.post(f"{BAILIAN_BASE_URL}/services/aigc/multimodal-generation/generation",
                                     headers=headers, json=payload, timeout=120)
                blocked, msg = self._bailian_check_response(resp)
                if blocked: self._bailian_block(msg); return
                if resp.status_code == 200:
                    choices = resp.json().get("output", {}).get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", [])
                        for item in content:
                            if isinstance(item, dict):
                                for key in ("image", "image_url", "url"):
                                    if key in item: self._bailian_download_result(item[key], "image"); return
                else: raise RuntimeError(f"图像生成失败: HTTP {resp.status_code}")
            else:
                headers["X-DashScope-Async"] = "enable"
                payload = {"model": model, "input": {"prompt": prompt}, "parameters": {"n": 1, "size": img_size}}
                resp = requests.post(f"{BAILIAN_BASE_URL}/services/aigc/text2image/image-synthesis",
                                     headers=headers, json=payload, timeout=120)
                blocked, msg = self._bailian_check_response(resp)
                if blocked: self._bailian_block(msg); return
                if resp.status_code == 200:
                    task_id = resp.json().get("output", {}).get("task_id", "")
                    if task_id: self._bailian_poll_task(api_key, task_id, "image")
                else: raise RuntimeError(f"图像生成失败: HTTP {resp.status_code}")
        except Exception as e: self._bailian_log_msg(f"错误: {e}"); raise
        finally: self.safe_after(lambda: self.bailian_gen_btn.configure(state="normal", text="生成当前镜头"))

    def _bailian_generate_video(self, api_key, model, prompt, ref_path, duration):
        self._bailian_log_msg(f"调用视频生成，模型: {model}")
        try: self._submit_video_via_requests(api_key, model, prompt, ref_path, duration)
        except Exception as e: self._bailian_log_msg(f"错误: {e}"); raise
        finally: self.safe_after(lambda: self.bailian_gen_btn.configure(state="normal", text="生成当前镜头"))

    def _submit_video_via_requests(self, api_key, model, prompt, ref_path, duration):
        ratio_info = self.ratio_map.get(self.bailian_ratio_var.get(), {})
        vid_w, vid_h = ratio_info.get("w", 1280), ratio_info.get("h", 720)
        dur = int(duration) if isinstance(duration, str) and duration.isdigit() else int(duration) if isinstance(duration, (int, float)) else 5
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "X-DashScope-Async": "enable"}
        payload = {"model": model, "input": {"prompt": prompt}, "parameters": {"size": f"{vid_w}*{vid_h}", "duration": dur}}
        if model in (EDIT_MODELS + I2V_MODELS + R2V_MODELS):
            if not ref_path or not os.path.exists(ref_path): raise ValueError(f"模型 {model} 需要参考素材")
            oss_url = self._upload_to_bailian_oss(api_key, os.path.abspath(ref_path))
            if oss_url:
                media_type = "first_frame" if model in I2V_MODELS else ("first_clip" if model in R2V_MODELS else "first_frame")
                payload["input"]["media"] = [{"type": media_type, "url": oss_url}]
            else: self._bailian_log_msg("错误: 媒体上传失败！"); return
        resp = requests.post(f"{BAILIAN_BASE_URL}/services/aigc/video-generation/video-synthesis",
                             headers=headers, json=payload, timeout=120)
        blocked, msg = self._bailian_check_response(resp)
        if blocked: self._bailian_block(msg); return
        if resp.status_code == 200:
            task_id = resp.json().get("output", {}).get("task_id", "")
            if task_id: self._bailian_log_msg(f"任务已提交: {task_id}"); self._bailian_poll_task(api_key, task_id, "video")
        else: raise RuntimeError(f"视频生成失败: HTTP {resp.status_code}")

    def _to_data_uri(self, local_path):
        ext = os.path.splitext(local_path)[1].lower()
        mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
        mime = mime_map.get(ext, "application/octet-stream")
        with open(local_path, "rb") as f: b64 = base64.b64encode(f.read()).decode()
        return f"data:{mime};base64,{b64}"

    def _upload_to_bailian_oss(self, api_key, local_path):
        self._bailian_log_msg(f"上传文件到 OSS: {os.path.basename(local_path)}")
        headers = {"Authorization": f"Bearer {api_key}"}
        for endpoint in [f"{BAILIAN_BASE_URL}/uploads", "https://dashscope.aliyuncs.com/api/v1/uploads"]:
            try:
                with open(local_path, "rb") as f:
                    resp = requests.post(endpoint, headers=headers,
                        files={"file": (os.path.basename(local_path), f)}, data={"target": "model-service"}, timeout=120)
                if resp.status_code in (200, 201):
                    result = resp.json()
                    url = result.get("data", {}).get("upload_url", "") or result.get("output", {}).get("upload_url", "") or result.get("upload_url", "")
                    if url: self._bailian_log_msg("OSS 上传成功"); return url
            except Exception: continue
        self._bailian_log_msg("OSS 上传失败，尝试 base64 内嵌")
        return self._to_data_uri(local_path)

    def _bailian_poll_task(self, api_key, task_id, task_type):
        headers = {"Authorization": f"Bearer {api_key}"}
        max_wait, elapsed = 600, 0
        while elapsed < max_wait:
            time.sleep(5); elapsed += 5
            try:
                resp = requests.get(f"{BAILIAN_BASE_URL}/tasks/{task_id}", headers=headers, timeout=30)
                blocked, msg = self._bailian_check_response(resp)
                if blocked: self._bailian_block(msg); return
                if resp.status_code != 200: continue
                result = resp.json()
                status = result.get("output", {}).get("task_status", "")
                self._bailian_log_msg(f"[{elapsed}s] 状态: {status}")
                if status == "SUCCEEDED":
                    url = self._extract_image_url(result.get("output", {}))
                    if url: self._bailian_download_result(url, task_type)
                    return
                elif status == "FAILED":
                    err = result.get("output", {}).get("message", "未知错误")
                    self._bailian_log_msg(f"任务失败: {err}")
                    if any(kw in err.lower() for kw in ["quota", "balance", "insufficient", "余额", "配额"]):
                        self._bailian_block(f"任务因算力不足失败: {err}"); return
                    raise RuntimeError(f"任务失败: {err}")
            except Exception: continue
        self._bailian_log_msg(f"超时: {max_wait} 秒")

    def _extract_image_url(self, output):
        for key in ("image_url", "output_video_url", "url", "video_url"):
            val = output.get(key, "")
            if val: return val
        if "results" in output:
            for r in output["results"]:
                if isinstance(r, dict) and "url" in r: return r["url"]
        if "choices" in output:
            for c in output["choices"]:
                if isinstance(c, dict):
                    for item in c.get("message", {}).get("content", []):
                        if isinstance(item, dict):
                            for k in ("video_url", "image_url", "url"):
                                if k in item: return item[k]
        return ""

    def _bailian_download_result(self, url, task_type):
        self._bailian_log_msg("下载中...")
        ext = ".mp4" if task_type == "video" else ".png"
        out_dir = self._get_output_dir("output_video") if task_type == "video" else self._get_output_dir("bailian_output")
        os.makedirs(out_dir, exist_ok=True)
        filename = f"bailian_{time.strftime('%Y%m%d_%H%M%S')}{ext}"
        out_path = os.path.join(out_dir, filename)
        try:
            dl = requests.get(url, timeout=120)
            if dl.status_code == 200:
                with open(out_path, "wb") as f: f.write(dl.content)
                self._bailian_log_msg(f"已保存: {out_path}")
            else: self._bailian_log_msg(f"下载失败: HTTP {dl.status_code}")
        except Exception as e: self._bailian_log_msg(f"下载错误: {e}")

    # ---- Batch i2v ----
    def _on_duration_mode_change(self):
        self.i2v_duration_entry.configure(state="normal" if self.i2v_duration_mode.get() == "manual" else "disabled")

    def _i2v_batch_update_count(self):
        img_count = len(self._i2v_batch_images); prompt_count = len(self._i2v_mapping_rows)
        color = C["green"] if img_count == prompt_count and img_count > 0 else C["warn"]
        self.i2v_batch_count_label.configure(text=f"{img_count} 图 / {prompt_count} 提示词", text_color=color)

    def _i2v_batch_add_images(self):
        files = filedialog.askopenfilenames(title="选择参考图片（可多选）",
            filetypes=[("图片", "*.png *.jpg *.jpeg *.webp"), ("所有文件", "*.*")])
        if files:
            self._i2v_batch_images.extend(files)
            for img_path in files: self._i2v_add_mapping_row(img_path, "")
            self._i2v_batch_update_count()

    def _i2v_add_mapping_row(self, img_path, prompt):
        self.i2v_empty_label.pack_forget()
        row_idx = len(self._i2v_mapping_rows) + 1
        row_frame = ctk.CTkFrame(self.i2v_mapping_frame, fg_color="transparent")
        row_frame.pack(fill="x", pady=1)
        num_label = ctk.CTkLabel(row_frame, text=str(row_idx), font=FONT_SMALL, text_color=C["text3"], width=30)
        num_label.pack(side="left")
        preview_label = ctk.CTkLabel(row_frame, text="", width=50, height=50, fg_color=C["surface"], corner_radius=4)
        preview_label.pack(side="left", padx=2)
        try:
            img = Image.open(img_path); img.thumbnail((45, 45), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            preview_label.configure(image=photo, text=""); preview_label.image = photo
        except Exception: preview_label.configure(text="❌")
        prompt_entry = ctk.CTkEntry(row_frame, font=FONT_SMALL, fg_color=C["surface"],
            border_color=C["border"], corner_radius=4, placeholder_text="输入提示词...")
        prompt_entry.pack(side="left", padx=2, fill="x", expand=True)
        if prompt: prompt_entry.insert(0, prompt)
        duration_entry = ctk.CTkEntry(row_frame, width=40, font=FONT_MONO_SM,
            fg_color=C["surface"], border_color=C["border"], corner_radius=4)
        duration_entry.pack(side="left", padx=2); duration_entry.insert(0, "5")
        btn_row = ctk.CTkFrame(row_frame, fg_color="transparent")
        btn_row.pack(side="left", padx=2)
        ctk.CTkButton(btn_row, text="💬", font=FONT_SMALL, width=24, fg_color=C["accent"],
                       hover_color=C["accent2"], text_color=C["bg"], corner_radius=4, height=24,
                       command=lambda idx=row_idx-1: self._i2v_open_chat(idx)).pack(side="left", padx=1)
        ctk.CTkButton(btn_row, text="AI", font=FONT_SMALL, width=30, fg_color=C["blue"],
                       hover_color="#3AA5E0", text_color="#FFF", corner_radius=4, height=24,
                       command=lambda idx=row_idx-1: self._i2v_mimo_analyze_single(idx)).pack(side="left", padx=1)
        ctk.CTkButton(btn_row, text="×", font=FONT_SMALL, width=24, fg_color=C["red"],
                       hover_color="#FF5555", text_color="#FFF", corner_radius=4, height=24,
                       command=lambda idx=row_idx-1: self._i2v_remove_mapping_row(idx)).pack(side="left", padx=1)
        self._i2v_mapping_rows.append({"frame": row_frame, "num_label": num_label,
            "preview_label": preview_label, "prompt_entry": prompt_entry,
            "duration_entry": duration_entry, "img_path": img_path})

    def _i2v_remove_mapping_row(self, idx):
        if idx >= len(self._i2v_mapping_rows): return
        row = self._i2v_mapping_rows[idx]; row["frame"].destroy()
        self._i2v_mapping_rows.pop(idx); self._i2v_batch_images.pop(idx)
        for i, row_data in enumerate(self._i2v_mapping_rows):
            row_data["num_label"].configure(text=str(i + 1))
        for i, row_data in enumerate(self._i2v_mapping_rows):
            btn_row = row_data["frame"].winfo_children()[-1]
            if isinstance(btn_row, ctk.CTkFrame):
                for btn in btn_row.winfo_children():
                    text = btn.cget("text")
                    if text == "💬": btn.configure(command=lambda idx=i: self._i2v_open_chat(idx))
                    elif text == "AI": btn.configure(command=lambda idx=i: self._i2v_mimo_analyze_single(idx))
                    elif text == "×": btn.configure(command=lambda idx=i: self._i2v_remove_mapping_row(idx))
        self._i2v_batch_update_count()
        if not self._i2v_mapping_rows: self.i2v_empty_label.pack(pady=20)

    def _i2v_extract_prompts_from_script(self):
        content = self.script_output.get("1.0", "end").strip()
        if not content: messagebox.showinfo("提示", "Script 页面中没有脚本内容。"); return
        shots = self._parse_script_shots(content)
        prompts = [s["prompt"] for s in shots if s["prompt"]] if shots else self._extract_prompts_loose(content)
        if not prompts:
            messagebox.showinfo("提示", "未从脚本中找到提示词。\n支持的格式：\n• 英文 Prompt: xxx\n• 画面描述: xxx"); return
        for row in self._i2v_mapping_rows: row["prompt_entry"].delete(0, "end")
        for i, prompt in enumerate(prompts):
            if i < len(self._i2v_mapping_rows): self._i2v_mapping_rows[i]["prompt_entry"].insert(0, prompt)
            else: self._i2v_add_mapping_row("", prompt)
        self._i2v_batch_update_count()

    def _extract_prompts_loose(self, content):
        prompts = []
        patterns = [r"(?:英文|English)\s*Prompt\s*[:：]\s*(.+)", r"Prompt\s*[:：]\s*(.+)",
                    r"描述\s*[:：]\s*(.+)", r"画面\s*[:：]\s*(.+)", r"Visual\s*[:：]\s*(.+)"]
        for line in content.split("\n"):
            line = line.strip()
            if not line: continue
            for pattern in patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    text = re.sub(r"\*+", "", match.group(1)).strip()
                    if text and len(text) > 10: prompts.append(text); break
        return prompts

    def _i2v_mimo_analyze_single(self, idx):
        if idx >= len(self._i2v_mapping_rows): return
        row = self._i2v_mapping_rows[idx]
        prompt = row["prompt_entry"].get().strip()
        img_name = os.path.basename(row["img_path"]) if row["img_path"] else "无图片"
        self._bailian_log_msg(f"MiMo 正在优化第 {idx+1} 条提示词...")
        threading.Thread(target=self._i2v_mimo_worker, args=([{"idx": idx, "prompt": prompt, "img_name": img_name}],), daemon=True).start()

    def _i2v_open_chat(self, idx):
        if idx >= len(self._i2v_mapping_rows): return
        row = self._i2v_mapping_rows[idx]
        current_prompt = row["prompt_entry"].get().strip()
        img_name = os.path.basename(row["img_path"]) if row["img_path"] else "无图片"

        chat_window = ctk.CTkToplevel(self.root)
        chat_window.title(f"MiMo AI 聊天 - 第 {idx+1} 行 (图片: {img_name})")
        chat_window.geometry("600x550"); chat_window.configure(fg_color=C["bg"])
        chat_window.transient(self.root); chat_window.grab_set()

        ctk.CTkLabel(chat_window, text=f"📷 当前图片: {img_name}", font=FONT_SMALL, text_color=C["text3"]).pack(anchor="w", padx=16, pady=(12, 2))
        ctk.CTkLabel(chat_window, text="📝 当前提示词 (实时更新):", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w", padx=16, pady=(0, 2))
        prompt_display = ctk.CTkTextbox(chat_window, height=70, font=FONT_MONO_SM,
            fg_color=C["surface2"], text_color=C["accent"], corner_radius=8, border_width=1, border_color=C["border"])
        prompt_display.pack(fill="x", padx=16, pady=(0, 8))
        prompt_display.insert("1.0", current_prompt); prompt_display.configure(state="disabled")

        ctk.CTkLabel(chat_window, text="对话:", font=FONT_SMALL, text_color=C["text"]).pack(anchor="w", padx=16, pady=(4, 2))
        chat_history = ctk.CTkTextbox(chat_window, height=200, font=FONT_BODY,
            fg_color=C["surface2"], text_color=C["text"], corner_radius=8, border_width=1, border_color=C["border"])
        chat_history.pack(fill="both", expand=True, padx=16, pady=(0, 8)); chat_history.configure(state="disabled")

        input_frame = ctk.CTkFrame(chat_window, fg_color="transparent")
        input_frame.pack(fill="x", padx=16, pady=(0, 8))
        chat_input = ctk.CTkEntry(input_frame, font=FONT_BODY, fg_color=C["surface2"],
            border_color=C["border"], corner_radius=8, placeholder_text="输入你想怎么修改提示词...")
        chat_input.pack(side="left", fill="x", expand=True, padx=(0, 8))

        def send_message():
            user_msg = chat_input.get().strip()
            if not user_msg: return
            chat_input.delete(0, "end")
            chat_history.configure(state="normal"); chat_history.insert("end", f"你: {user_msg}\n\n")
            chat_history.configure(state="disabled"); chat_history.see("end")
            threading.Thread(target=_chat_with_mimo, args=(user_msg,), daemon=True).start()

        def _chat_with_mimo(user_msg):
            api_key = self.config.get("mimo_api_key", "").strip() or self.config.get("api_key", "").strip()
            if not api_key:
                self.safe_after(lambda: _show_ai_response("错误: 请先配置 API Key！")); return
            base_url = self._get_base_url() if hasattr(self, '_get_base_url') else self.config.get("api_base_url", "").strip()
            system_prompt = f"""你是AI视频生成提示词优化助手。
当前图片文件名: {img_name}
当前提示词: {current_prompt}
用户会告诉你如何修改提示词。请根据用户的要求，直接输出修改后的完整英文提示词。
注意：1. 只输出修改后的提示词 2. 保持英文 3. 控制在50-100词"""
            try:
                resp = requests.post(f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json; charset=utf-8"},
                    data=json.dumps({"model": "mimo-v2.5-pro",
                        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_msg}],
                        "temperature": 0.7, "max_tokens": 500}, ensure_ascii=False).encode('utf-8'), timeout=60)
                if resp.status_code == 200:
                    ai_response = resp.json()["choices"][0]["message"]["content"].strip()
                    self.safe_after(lambda: _show_ai_response(ai_response))
                else: self.safe_after(lambda: _show_ai_response(f"API错误: {resp.status_code}"))
            except Exception as e: self.safe_after(lambda: _show_ai_response(f"错误: {e}"))

        def _show_ai_response(response, chat_idx=None):
            chat_history.configure(state="normal"); chat_history.insert("end", f"MiMo: {response}\n\n")
            chat_history.configure(state="disabled"); chat_history.see("end")
            if chat_idx is not None and response and not response.startswith("错误") and not response.startswith("API错误"):
                self.root.after(100, lambda: _auto_apply_prompt(response, chat_idx))

        def _auto_apply_prompt(new_prompt, chat_idx):
            if chat_idx < len(self._i2v_mapping_rows):
                entry = self._i2v_mapping_rows[chat_idx]["prompt_entry"]
                entry.delete(0, "end"); entry.insert(0, new_prompt)
                prompt_display.configure(state="normal"); prompt_display.delete("1.0", "end")
                prompt_display.insert("1.0", new_prompt); prompt_display.configure(state="disabled")
                chat_history.configure(state="normal"); chat_history.insert("end", "✅ 提示词已自动更新！\n\n")
                chat_history.configure(state="disabled"); chat_history.see("end")

        ctk.CTkButton(input_frame, text="发送", font=FONT_BODY, width=60,
                       fg_color=C["accent"], text_color=C["bg"], hover_color=C["accent2"],
                       corner_radius=8, command=send_message).pack(side="left")
        chat_input.bind("<Return>", lambda e: send_message())

        btn_frame = ctk.CTkFrame(chat_window, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkLabel(btn_frame, text="💡 MiMo回复后会自动更新提示词", font=FONT_SMALL, text_color=C["accent"]).pack(side="left")
        ctk.CTkButton(btn_frame, text="关闭", font=FONT_BODY, width=80,
                       fg_color=C["surface2"], text_color=C["text"], hover_color=C["border"],
                       corner_radius=8, command=chat_window.destroy).pack(side="right", padx=4)

    def _i2v_mimo_analyze_all(self):
        if not self._i2v_mapping_rows:
            messagebox.showinfo("提示", "请先添加图片和提示词！"); return
        data_list = []
        for i, row in enumerate(self._i2v_mapping_rows):
            prompt = row["prompt_entry"].get().strip()
            img_name = os.path.basename(row["img_path"]) if row["img_path"] else "无图片"
            data_list.append({"idx": i, "prompt": prompt, "img_name": img_name})
        self._bailian_log_msg(f"MiMo 正在批量优化 {len(data_list)} 条提示词...")
        threading.Thread(target=self._i2v_mimo_worker, args=(data_list,), daemon=True).start()

    def _i2v_mimo_worker(self, data_list):
        api_key = self.config.get("mimo_api_key", "").strip() or self.config.get("api_key", "").strip()
        if not api_key: self._bailian_log_msg("错误: 请先配置 API Key！"); return
        base_url = self._get_base_url() if hasattr(self, '_get_base_url') else self.config.get("api_base_url", "").strip()
        system_prompt = """你是AI视频生成提示词优化专家。请根据图片文件名推测画面内容并优化提示词。
1. 保持原始创意核心 2. 增加视觉细节（光影、构图、色彩、氛围）
3. 添加运镜方式 4. 添加电影级描述词 5. 英文表达准确 6. 50-100词
直接输出优化后的英文提示词。"""
        success_count = 0
        for data in data_list:
            idx, prompt, img_name = data["idx"], data["prompt"], data["img_name"]
            if not prompt: continue
            try:
                resp = requests.post(f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json; charset=utf-8"},
                    data=json.dumps({"model": "mimo-v2.5-pro",
                        "messages": [{"role": "system", "content": system_prompt},
                                     {"role": "user", "content": f"图片文件名: {img_name}\n初始提示词: {prompt}\n\n请优化这个视频生成提示词。"}],
                        "temperature": 0.7, "max_tokens": 500}, ensure_ascii=False).encode('utf-8'), timeout=60)
                if resp.status_code == 200:
                    optimized = resp.json()["choices"][0]["message"]["content"].strip()
                    self.safe_after(lambda i=idx, opt=optimized: self._i2v_apply_single(i, opt))
                    success_count += 1
                    self._bailian_log_msg(f"[{idx+1}/{len(data_list)}] ✓ 优化完成")
            except Exception as e: self._bailian_log_msg(f"[{idx+1}/{len(data_list)}] ✗ 失败: {e}")
        self._bailian_log_msg(f"优化完成: {success_count}/{len(data_list)}")
        if success_count > 0: messagebox.showinfo("完成", f"MiMo 已优化 {success_count} 条提示词！")

    def _i2v_apply_single(self, idx, optimized_prompt):
        if idx >= len(self._i2v_mapping_rows): return
        entry = self._i2v_mapping_rows[idx]["prompt_entry"]
        entry.delete(0, "end"); entry.insert(0, optimized_prompt)

    def _i2v_batch_clear(self):
        self._i2v_batch_images = []
        for row in self._i2v_mapping_rows: row["frame"].destroy()
        self._i2v_mapping_rows = []
        self.i2v_empty_label.pack(pady=20); self._i2v_batch_update_count()

    def _start_i2v_batch_generate(self):
        api_key = self.bailian_key_var.get().strip()
        if not api_key: messagebox.showwarning("提示", "请先填写百炼 API Key！"); return
        model = self.bailian_model_var.get()
        pipeline_type = MODEL_PIPELINE_CACHE.get(model, PipelineType.IMAGE_GEN)
        if pipeline_type != PipelineType.IMAGE_TO_VIDEO:
            messagebox.showwarning("提示", f"当前模型 {model} 不是 Image-to-Video 类型！"); return
        if not self._i2v_mapping_rows: messagebox.showwarning("提示", "请先添加图片和提示词！"); return
        data_pairs = []
        for i, row in enumerate(self._i2v_mapping_rows):
            img_path, prompt = row["img_path"], row["prompt_entry"].get().strip()
            if not img_path: messagebox.showerror("校验失败", f"第 {i+1} 行缺少图片！"); return
            if not prompt: messagebox.showerror("校验失败", f"第 {i+1} 行缺少提示词！"); return
            duration = int(self.i2v_duration_entry.get()) if self.i2v_duration_mode.get() == "manual" else self._estimate_duration_from_prompt(prompt)
            data_pairs.append((img_path, prompt, duration))
        self._save_bailian_config()
        archived = self._archive_old_files(("output_video",))
        if archived: self._bailian_log_msg(f"[归档] 已将 {archived} 个旧文件移入 archive_history")
        threading.Thread(target=self._i2v_batch_worker, args=(api_key, model, data_pairs), daemon=True).start()

    def _estimate_duration_from_prompt(self, prompt):
        word_count = len(prompt.split())
        if word_count < 15: return 3
        elif word_count < 30: return 5
        elif word_count < 50: return 7
        else: return 10

    def _i2v_batch_worker(self, api_key, model, data_pairs):
        ok, fail = 0, 0; total = len(data_pairs)
        for i, (img_path, prompt, duration) in enumerate(data_pairs, 1):
            if _bailian_circuit_open: break
            self._bailian_log_msg(f"[{i}/{total}] {os.path.basename(img_path)} | {duration}s")
            try:
                self._bailian_generate_video(api_key, model, prompt, img_path, str(duration))
                ok += 1
            except Exception as e: fail += 1; self._bailian_log_msg(f"[{i}/{total}] 失败: {e}")
        self._bailian_log_msg(f"{'='*40} 完成: 成功 {ok}, 失败 {fail}")
        out_dir = self._get_output_dir("output_video")
        if ok > 0:
            result = messagebox.askyesno("完成", f"批量图生视频完成！\n成功: {ok}\n失败: {fail}\n保存: {out_dir}\n\n是否打开输出目录？")
            if result: os.startfile(out_dir)

    # MiMo agent (global floating button)
    def _agent_log(self, msg):
        self.agent_chat_history.configure(state="normal")
        self.agent_chat_history.insert("end", msg + "\n")
        self.agent_chat_history.see("end")
        self.agent_chat_history.configure(state="disabled")

    def _agent_get_logs(self, lines=50):
        log_parts = []
        try:
            if os.path.exists(LOG_PATH):
                with open(LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
                    crash_lines = f.readlines()[-lines:]
                    if crash_lines: log_parts.append("=== crash.log ===\n" + "".join(crash_lines))
        except Exception: pass
        try:
            content = self.global_log.get(f"end-{lines}l", "end").strip()
            if content: log_parts.append(f"=== 应用日志 ===\n" + content)
        except Exception: pass
        return "\n\n".join(log_parts) if log_parts else "暂无日志记录"

    def _agent_send_command(self):
        cmd = self.agent_input.get().strip()
        if not cmd: return
        self.agent_input.delete(0, "end")
        self._agent_log(f"🧑: {cmd}")
        cmd_lower = cmd.lower()
        if any(k in cmd_lower for k in ["提取", "script", "导入提示词"]):
            self._agent_log("🤖: 正在从Script提取提示词..."); self._agent_extract_prompts()
        elif any(k in cmd_lower for k in ["清空", "清除"]):
            self._i2v_batch_clear(); self._agent_log("🤖: ✅ 已清空")
        elif any(k in cmd_lower for k in ["开始生成", "开始批量"]):
            self._start_i2v_batch_generate()
        elif any(k in cmd_lower for k in ["全部优化", "优化全部"]):
            self._i2v_mimo_analyze_all()
        elif "第" in cmd and ("改成" in cmd or "改为" in cmd):
            self._agent_modify_single(cmd)
        else: self._agent_mimo_understand(cmd)

    def _agent_extract_prompts(self):
        content = self.script_output.get("1.0", "end").strip()
        if not content: self._agent_log("🤖: ❌ Script页面没有脚本内容"); return
        shots = self._parse_script_shots(content)
        prompts = [s["prompt"] for s in shots if s["prompt"]] if shots else self._extract_prompts_loose(content)
        if not prompts: self._agent_log("🤖: ❌ 无法提取提示词"); return
        self._i2v_batch_clear()
        for prompt in prompts: self._i2v_add_mapping_row("", prompt)
        self._i2v_batch_update_count()
        self._agent_log(f"🤖: ✅ 已提取 {len(prompts)} 条提示词")

    def _agent_modify_single(self, cmd):
        match = re.search(r"第(\d+)(?:条|个|行).*(?:改成|修改为|改为)\s*(.+)", cmd)
        if match:
            idx = int(match.group(1)) - 1; new_text = match.group(2).strip()
            if idx < len(self._i2v_mapping_rows):
                entry = self._i2v_mapping_rows[idx]["prompt_entry"]
                entry.delete(0, "end"); entry.insert(0, new_text)
                self._agent_log(f"🤖: ✅ 已修改第 {idx+1} 条")
            else: self._agent_log(f"🤖: ❌ 第 {idx+1} 条不存在")
        else: self._agent_log("🤖: 格式不对，请用: 第X条改成xxx")

    def _agent_mimo_understand(self, cmd):
        api_key = self.config.get("mimo_api_key", "").strip() or self.config.get("api_key", "").strip()
        if not api_key: self._agent_log("🤖: ❌ 请先配置API Key"); return
        self._agent_log("🤖: 正在理解命令...")
        threading.Thread(target=self._agent_mimo_worker, args=(cmd,), daemon=True).start()

    def _agent_mimo_worker(self, cmd):
        api_key = self.config.get("mimo_api_key", "").strip() or self.config.get("api_key", "").strip()
        base_url = self._get_base_url() if hasattr(self, '_get_base_url') else self.config.get("api_base_url", "").strip()
        model = self.config.get("api_model", "mimo-v2.5-pro").strip()
        system_prompt = f"""你是AI视频生成助手的命令解析器。
用户给你命令，输出JSON: {{"action": "操作类型", "params": {{参数}}}}
支持: extract_prompts, clear_all, start_generate, optimize_all, modify_single({{idx, text}}), add_images, chat_reply({{reply}})
只输出JSON。"""
        try:
            resp = requests.post(f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json; charset=utf-8"},
                data=json.dumps({"model": model, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": cmd}],
                    "temperature": 0.3, "max_tokens": 1000}, ensure_ascii=False).encode('utf-8'), timeout=60)
            if resp.status_code == 200:
                ai_reply = resp.json()["choices"][0]["message"]["content"].strip()
                if ai_reply: self.safe_after(lambda: self._agent_process_ai_command(ai_reply))
        except Exception as e: self.safe_after(lambda: self._agent_log(f"🤖: ❌ 错误: {e}"))

    def _agent_process_ai_command(self, ai_reply):
        try:
            json_match = re.search(r'\{.*\}', ai_reply, re.DOTALL)
            if json_match:
                cmd_data = json.loads(json_match.group())
                action, params = cmd_data.get("action", ""), cmd_data.get("params", {})
                if action == "extract_prompts": self._agent_extract_prompts()
                elif action == "clear_all": self._i2v_batch_clear(); self._agent_log("🤖: ✅ 已清空")
                elif action == "start_generate": self._start_i2v_batch_generate()
                elif action == "optimize_all": self._i2v_mimo_analyze_all()
                elif action == "modify_single":
                    idx, text = params.get("idx", 0), params.get("text", "")
                    if idx < len(self._i2v_mapping_rows) and text:
                        entry = self._i2v_mapping_rows[idx]["prompt_entry"]
                        entry.delete(0, "end"); entry.insert(0, text)
                        self._agent_log(f"🤖: ✅ 已修改第 {idx+1} 条")
                elif action == "chat_reply": self._agent_log(f"🤖: {params.get('reply', '')}")
                else: self._agent_log(f"🤖: {ai_reply}")
            else: self._agent_log(f"🤖: {ai_reply}")
        except Exception as e: self._agent_log(f"🤖: ❌ 解析失败: {e}")


# Module-level circuit breaker flag (avoids circular import with app.py)
_bailian_circuit_open = False
