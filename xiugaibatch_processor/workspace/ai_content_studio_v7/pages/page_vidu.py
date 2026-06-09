import threading
import json
import base64
import os
import requests
import time as _time
from tkinter import filedialog, messagebox
import tkinter as tk
import customtkinter as ctk

from theme import C, FONT_H2, FONT_BODY, FONT_SMALL, FONT_MONO_SM, FONT_MONO, SectionCard
from config import VIDU_MODELS, VIDU_STYLES, VIDU_RESOLUTIONS, VIDU_ASPECT_RATIOS, VIDU_MOVEMENT_AMPLITUDES, VIDU_CREDIT_RATES, VIDU_MODEL_DURATION, VIDU_BASE_URL, save_config

class ViduPage:
    def __init__(self, parent, context):
        self.ctx = context
        self.frame = ctk.CTkScrollableFrame(
            parent, fg_color=C["bg"],
            scrollbar_button_color=C["border"],
            scrollbar_button_hover_color=C["text3"]
        )
        self._build_ui()

    def _build_ui(self):
        ctk.CTkLabel(self.frame, text="🎬 Vidu 视频生成引擎", font=FONT_H2,
                     text_color=C["accent"]).pack(anchor="w", pady=(0, 12))

        self._build_auth_card()
        self._build_settings_card()
        self._build_adv_settings_card()
        self._build_ref_card()
        self._build_shot_list_card()
        self._build_prompt_card()
        self._build_action_card()
        
        self._on_vidu_param_changed()

    def _build_auth_card(self):
        card = SectionCard(self.frame, title="🔑 API Key 认证")
        card.pack(fill="x", pady=(0, 8))
        key_row = ctk.CTkFrame(card, fg_color="transparent")
        key_row.pack(fill="x", padx=16, pady=(4, 4))
        self.vidu_key_var = tk.StringVar(value=self.ctx.config.get("vidu_api_key", ""))
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

        self.vidu_credits_label = ctk.CTkLabel(
            card, text="积分: --", font=FONT_SMALL, text_color=C["text3"]
        )
        self.vidu_credits_label.pack(anchor="w", padx=16, pady=(0, 4))
        ctk.CTkButton(card, text="查询积分", font=FONT_SMALL, width=70,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text2"], corner_radius=6, height=26,
                       command=self._vidu_query_credits).pack(anchor="w", padx=16, pady=(0, 8))

    def _build_settings_card(self):
        card = SectionCard(self.frame, title="⚙️ 渲染参数")
        card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(card, text="模型", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w", padx=16, pady=(4, 0))
        self.vidu_model_var = tk.StringVar(value=self.ctx.config.get("vidu_model", VIDU_MODELS[0]))
        ctk.CTkComboBox(card, variable=self.vidu_model_var, values=VIDU_MODELS,
                         font=FONT_MONO, fg_color=C["surface2"], border_color=C["border"],
                         button_color=C["accent"], button_hover_color=C["accent_dim"],
                         dropdown_fg_color=C["surface2"], dropdown_hover_color=C["surface3"],
                         corner_radius=8, command=lambda _: self._vidu_on_model_changed()
                         ).pack(fill="x", padx=16, pady=(0, 8))

        param_row = ctk.CTkFrame(card, fg_color="transparent")
        param_row.pack(fill="x", padx=16, pady=(0, 8))

        dur_frame = ctk.CTkFrame(param_row, fg_color="transparent")
        dur_frame.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkLabel(dur_frame, text="时长 (秒)", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w")
        self.vidu_duration_var = tk.StringVar(value=self.ctx.config.get("vidu_duration", "5"))
        self.vidu_duration_combo = ctk.CTkComboBox(
            dur_frame, variable=self.vidu_duration_var,
            values=self._vidu_get_duration_options(),
            font=FONT_MONO, fg_color=C["surface2"], border_color=C["border"],
            button_color=C["accent"], button_hover_color=C["accent_dim"],
            dropdown_fg_color=C["surface2"], corner_radius=8,
            command=lambda _: self._on_vidu_param_changed()
        )
        self.vidu_duration_combo.pack(fill="x", pady=(2, 0))

        res_frame = ctk.CTkFrame(param_row, fg_color="transparent")
        res_frame.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(res_frame, text="分辨率", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w")
        self.vidu_resolution_var = tk.StringVar(value=self.ctx.config.get("vidu_resolution", "720p"))
        ctk.CTkComboBox(res_frame, variable=self.vidu_resolution_var, values=VIDU_RESOLUTIONS,
                         font=FONT_MONO, fg_color=C["surface2"], border_color=C["border"],
                         button_color=C["accent"], button_hover_color=C["accent_dim"],
                         dropdown_fg_color=C["surface2"], corner_radius=8,
                         command=lambda _: self._on_vidu_param_changed()
                         ).pack(fill="x", pady=(2, 0))

        self.vidu_cost_label = ctk.CTkLabel(card, text="预估积分: --", font=FONT_MONO_SM, text_color=C["warn"])
        self.vidu_cost_label.pack(anchor="w", padx=16, pady=(0, 8))

    def _build_adv_settings_card(self):
        card = SectionCard(self.frame, title="🎛️ 高级参数")
        card.pack(fill="x", pady=(0, 8))

        adv_row1 = ctk.CTkFrame(card, fg_color="transparent")
        adv_row1.pack(fill="x", padx=16, pady=(4, 4))

        sty_f = ctk.CTkFrame(adv_row1, fg_color="transparent")
        sty_f.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkLabel(sty_f, text="风格 (q1/v1)", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w")
        self.vidu_style_var = tk.StringVar(value=self.ctx.config.get("vidu_style", "general"))
        ctk.CTkComboBox(sty_f, variable=self.vidu_style_var, values=VIDU_STYLES,
                         font=FONT_MONO, fg_color=C["surface2"], border_color=C["border"],
                         button_color=C["accent"], dropdown_fg_color=C["surface2"],
                         corner_radius=8, command=lambda _: self._save_vidu_config()
                         ).pack(fill="x", pady=(2, 0))

        ar_f = ctk.CTkFrame(adv_row1, fg_color="transparent")
        ar_f.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(ar_f, text="画面比例", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w")
        self.vidu_aspect_var = tk.StringVar(value=self.ctx.config.get("vidu_aspect_ratio", "16:9"))
        ctk.CTkComboBox(ar_f, variable=self.vidu_aspect_var, values=VIDU_ASPECT_RATIOS,
                         font=FONT_MONO, fg_color=C["surface2"], border_color=C["border"],
                         button_color=C["accent"], dropdown_fg_color=C["surface2"],
                         corner_radius=8, command=lambda _: self._save_vidu_config()
                         ).pack(fill="x", pady=(2, 0))

        adv_row2 = ctk.CTkFrame(card, fg_color="transparent")
        adv_row2.pack(fill="x", padx=16, pady=(4, 4))
        
        mv_f = ctk.CTkFrame(adv_row2, fg_color="transparent")
        mv_f.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkLabel(mv_f, text="运动幅度 (q1/v1)", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w")
        self.vidu_movement_var = tk.StringVar(value=self.ctx.config.get("vidu_movement_amplitude", "auto"))
        ctk.CTkComboBox(mv_f, variable=self.vidu_movement_var, values=VIDU_MOVEMENT_AMPLITUDES,
                         font=FONT_MONO, fg_color=C["surface2"], border_color=C["border"],
                         button_color=C["accent"], dropdown_fg_color=C["surface2"],
                         corner_radius=8, command=lambda _: self._save_vidu_config()
                         ).pack(fill="x", pady=(2, 0))

        sd_f = ctk.CTkFrame(adv_row2, fg_color="transparent")
        sd_f.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(sd_f, text="随机种子 (0=随机)", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w")
        self.vidu_seed_var = tk.StringVar(value=self.ctx.config.get("vidu_seed", "0"))
        ctk.CTkEntry(sd_f, textvariable=self.vidu_seed_var, font=FONT_MONO,
                      fg_color=C["surface2"], border_color=C["border"], corner_radius=8
                      ).pack(fill="x", pady=(2, 0))

        toggle_row = ctk.CTkFrame(card, fg_color="transparent")
        toggle_row.pack(fill="x", padx=16, pady=(8, 4))

        self.vidu_bgm_var = tk.BooleanVar(value=self.ctx.config.get("vidu_bgm", False))
        ctk.CTkCheckBox(toggle_row, text="背景音乐", variable=self.vidu_bgm_var,
                         font=FONT_SMALL, fg_color=C["accent"], text_color=C["text2"],
                         hover_color=C["accent_dim"], corner_radius=4,
                         command=self._save_vidu_config).pack(side="left", padx=(0, 16))

        self.vidu_audio_var = tk.BooleanVar(value=self.ctx.config.get("vidu_audio", True))
        ctk.CTkCheckBox(toggle_row, text="音画同步", variable=self.vidu_audio_var,
                         font=FONT_SMALL, fg_color=C["accent"], text_color=C["text2"],
                         hover_color=C["accent_dim"], corner_radius=4,
                         command=self._save_vidu_config).pack(side="left", padx=(0, 16))

        self.vidu_offpeak_var = tk.BooleanVar(value=self.ctx.config.get("vidu_off_peak", False))
        ctk.CTkCheckBox(toggle_row, text="错峰模式", variable=self.vidu_offpeak_var,
                         font=FONT_SMALL, fg_color=C["accent"], text_color=C["text2"],
                         hover_color=C["accent_dim"], corner_radius=4,
                         command=self._save_vidu_config).pack(side="left", padx=(0, 16))

        self.vidu_watermark_var = tk.BooleanVar(value=self.ctx.config.get("vidu_watermark", False))
        ctk.CTkCheckBox(toggle_row, text="添加水印", variable=self.vidu_watermark_var,
                         font=FONT_SMALL, fg_color=C["accent"], text_color=C["text2"],
                         hover_color=C["accent_dim"], corner_radius=4,
                         command=self._save_vidu_config).pack(side="left")

    def _build_ref_card(self):
        card = SectionCard(self.frame, title="🖼️ 图生视频 (可选)")
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

    def _build_shot_list_card(self):
        self.vidu_shot_card = SectionCard(self.frame, title="📋 Script 分镜列表 (一键导入)")
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

    def _build_prompt_card(self):
        card = SectionCard(self.frame, title="📝 创作提示词 (最多5000字符)")
        card.pack(fill="x", pady=(0, 8))
        self.vidu_prompt_text = ctk.CTkTextbox(
            card, height=100, font=FONT_BODY, fg_color=C["surface2"],
            border_color=C["border"], border_width=1, corner_radius=8,
            text_color=C["text"], wrap="word"
        )
        self.vidu_prompt_text.pack(fill="x", padx=16, pady=(4, 8))

    def _build_action_card(self):
        btn_row = ctk.CTkFrame(self.frame, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, 8))
        self.vidu_gen_btn = ctk.CTkButton(
            btn_row, text="🚀 生成视频", font=FONT_H2,
            fg_color=C["accent"], text_color=C["bg"],
            hover_color=C["accent_dim"], corner_radius=10, height=48,
            command=self.start_vidu_generate
        )
        self.vidu_gen_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.vidu_result_frame = SectionCard(self.frame, title="📺 输出结果")
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

    def _toggle_vidu_key_vis(self):
        self.vidu_key_visible.set(not self.vidu_key_visible.get())
        self.vidu_key_entry.configure(show="" if self.vidu_key_visible.get() else "•")

    def _vidu_get_duration_options(self):
        model = self.vidu_model_var.get()
        dur_range = VIDU_MODEL_DURATION.get(model, (1, 16))
        return [str(d) for d in range(dur_range[0], dur_range[1] + 1)]

    def _vidu_on_model_changed(self):
        options = self._vidu_get_duration_options()
        self.vidu_duration_combo.configure(values=options)
        if self.vidu_duration_var.get() not in options:
            self.vidu_duration_var.set(options[len(options) // 2] if len(options) > 1 else options[0])
        self._on_vidu_param_changed()
        self._save_vidu_config()

    def _on_vidu_param_changed(self):
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
        resolution = self.vidu_resolution_var.get()
        duration = int(self.vidu_duration_var.get())
        rate = VIDU_CREDIT_RATES.get(resolution, 20)
        return rate * duration

    def _save_vidu_config(self):
        self.ctx.config["vidu_api_key"] = self.vidu_key_var.get().strip()
        self.ctx.config["vidu_model"] = self.vidu_model_var.get()
        self.ctx.config["vidu_duration"] = self.vidu_duration_var.get()
        self.ctx.config["vidu_resolution"] = self.vidu_resolution_var.get()
        self.ctx.config["vidu_style"] = self.vidu_style_var.get()
        self.ctx.config["vidu_aspect_ratio"] = self.vidu_aspect_var.get()
        self.ctx.config["vidu_seed"] = self.vidu_seed_var.get()
        self.ctx.config["vidu_movement_amplitude"] = self.vidu_movement_var.get()
        self.ctx.config["vidu_bgm"] = self.vidu_bgm_var.get()
        self.ctx.config["vidu_audio"] = self.vidu_audio_var.get()
        self.ctx.config["vidu_off_peak"] = self.vidu_offpeak_var.get()
        self.ctx.config["vidu_watermark"] = self.vidu_watermark_var.get()
        save_config(self.ctx.config)

    def _browse_vidu_ref_image(self):
        path = filedialog.askopenfilename(
            title="选择参考图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.webp")]
        )
        if path:
            self.vidu_ref_path_var.set(path)

    def _open_output_dir(self, sub_dir):
        base = os.path.dirname(os.path.abspath(__file__))
        save = self.ctx.config.get("save_path", "").strip()
        out_dir = os.path.join(save if save and os.path.isdir(save) else base, sub_dir)
        os.makedirs(out_dir, exist_ok=True)
        os.startfile(out_dir)

    def _vidu_validate_key(self):
        api_key = self.vidu_key_var.get().strip()
        if not api_key:
            messagebox.showwarning("提示", "请先输入 API Key")
            return
        self._save_vidu_config()
        self.ctx.log("正在验证 API Key...")
        
        def _worker():
            try:
                headers = {"Authorization": f"Token {api_key}"}
                resp = requests.get(f"{VIDU_BASE_URL}/ent/v2/credits?show_detail=true", headers=headers, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    remains = data.get("remains", [])
                    if remains:
                        credit = remains[0].get("credit_remain", 0)
                        self.ctx.log(f"✅ API Key 有效！剩余积分: {credit}")
                        self.ctx.safe_after(lambda: self.vidu_credits_label.configure(text=f"积分: {credit}", text_color=C["green"]))
                        self.ctx.safe_after(lambda: messagebox.showinfo("验证成功", f"API Key 有效！\n剩余积分: {credit}"))
                    else:
                        self.ctx.log("✅ API Key 有效，但无积分数据")
                        self.ctx.safe_after(lambda: messagebox.showinfo("验证成功", "API Key 有效"))
                elif resp.status_code == 401:
                    self.ctx.log("❌ API Key 无效 (401)")
                    self.ctx.safe_after(lambda: messagebox.showerror("验证失败", "API Key 无效，请检查"))
                else:
                    self.ctx.log(f"❌ 验证失败: HTTP {resp.status_code}")
                    self.ctx.safe_after(lambda: messagebox.showerror("验证失败", f"HTTP {resp.status_code}: {resp.text[:200]}"))
            except Exception as e:
                self.ctx.log(f"❌ 验证异常: {e}")
                self.ctx.safe_after(lambda: messagebox.showerror("验证异常", str(e)))
        threading.Thread(target=_worker, daemon=True).start()

    def _vidu_query_credits(self):
        api_key = self.vidu_key_var.get().strip()
        if not api_key:
            messagebox.showwarning("提示", "请先输入 API Key")
            return
        self.ctx.log("正在查询积分...")
        def _worker():
            try:
                headers = {"Authorization": f"Token {api_key}"}
                resp = requests.get(f"{VIDU_BASE_URL}/ent/v2/credits?show_detail=true", headers=headers, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    remains = data.get("remains", [])
                    credit = remains[0].get("credit_remain", 0) if remains else 0
                    self.ctx.safe_after(lambda: messagebox.showinfo("积分查询", f"剩余积分: {credit}"))
                    self.ctx.safe_after(lambda: self.vidu_credits_label.configure(text=f"积分: {credit}"))
                else:
                    self.ctx.safe_after(lambda: messagebox.showerror("查询失败", f"HTTP {resp.status_code}"))
            except Exception as e:
                self.ctx.safe_after(lambda: messagebox.showerror("异常", str(e)))
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
            self.ctx.log("用户取消生成")
            return

        self._save_vidu_config()
        self.vidu_gen_btn.configure(state="disabled", text="⏳ 生成中...")
        self.ctx.safe_after(lambda: self.vidu_result_label.configure(text="正在生成，请查看终端日志...", text_color=C["accent2"]))

        threading.Thread(target=self._vidu_generate_worker, args=(api_key, model, prompt, ref_path, int(duration), resolution), daemon=True).start()

    def _vidu_generate_worker(self, api_key, model, prompt, ref_path, duration, resolution):
        try:
            headers = {"Authorization": f"Token {api_key}", "Content-Type": "application/json"}
            payload = {"model": model}
            is_i2v = bool(ref_path and os.path.exists(ref_path))
            if prompt: payload["prompt"] = prompt
            payload["duration"] = duration
            payload["resolution"] = resolution
            payload["style"] = self.vidu_style_var.get()
            payload["aspect_ratio"] = self.vidu_aspect_var.get()
            seed_val = self.vidu_seed_var.get().strip()
            if seed_val and seed_val != "0": payload["seed"] = int(seed_val)
            movement = self.vidu_movement_var.get()
            if movement != "auto": payload["movement_amplitude"] = movement
            if self.vidu_bgm_var.get(): payload["bgm"] = True
            if "q3" in model: payload["audio"] = self.vidu_audio_var.get()
            if self.vidu_offpeak_var.get(): payload["off_peak"] = True
            if self.vidu_watermark_var.get(): payload["watermark"] = True

            if is_i2v:
                endpoint = f"{VIDU_BASE_URL}/ent/v2/image-to-video"
                with open(ref_path, "rb") as f: img_b64 = base64.b64encode(f.read()).decode()
                ext = os.path.splitext(ref_path)[1].lower().lstrip(".")
                mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(ext, "image/png")
                payload["images"] = [f"data:{mime};base64,{img_b64}"]
            else:
                endpoint = f"{VIDU_BASE_URL}/ent/v2/text-to-video"

            self.ctx.log(f"🚀 提交生成任务 | {resolution} | {duration}s")
            resp = requests.post(endpoint, headers=headers, json=payload, timeout=60)
            if resp.status_code not in (200, 201):
                self.ctx.log(f"❌ 提交失败: HTTP {resp.status_code} - {resp.text[:300]}")
                return

            task_id = resp.json().get("id", "")
            if not task_id: return
            self.ctx.log(f"✅ 任务已提交 | ID: {task_id}")

            elapsed = 0
            max_wait = 600
            while elapsed < max_wait:
                _time.sleep(5)
                elapsed += 5
                pr = requests.get(f"{VIDU_BASE_URL}/ent/v2/tasks/{task_id}", headers=headers, timeout=30)
                if pr.status_code == 200:
                    result = pr.json()
                    status = result.get("status", "")
                    if status == "success":
                        video_url = result.get("video_url", "") or result.get("videos", [{}])[0].get("url", "")
                        self.ctx.log(f"🎉 生成成功！ ({elapsed}s)")
                        if video_url: self._vidu_download_video(video_url)
                        self.ctx.safe_after(lambda: self.vidu_result_label.configure(text=f"✅ 完成！", text_color=C["green"]))
                        return
                    elif status == "failed":
                        err = result.get("error_msg", "未知错误")
                        self.ctx.log(f"❌ 生成失败: {err}")
                        self.ctx.safe_after(lambda: self.vidu_result_label.configure(text=f"❌ 失败: {err}", text_color=C["red"]))
                        return
            self.ctx.log(f"⏰ 超时 ({max_wait}s)")
        except Exception as e:
            self.ctx.log(f"💥 异常: {e}")
        finally:
            self.ctx.safe_after(lambda: self.vidu_gen_btn.configure(state="normal", text="🚀 生成视频"))

    def _vidu_download_video(self, url):
        self.ctx.log("📥 下载视频中...")
        out_dir = os.path.join(self.ctx.config.get("save_path", "") or os.path.dirname(os.path.abspath(__file__)), "output_video")
        os.makedirs(out_dir, exist_ok=True)
        filename = f"vidu_{_time.strftime('%Y%m%d_%H%M%S')}.mp4"
        filepath = os.path.join(out_dir, filename)
        resp = requests.get(url, stream=True, timeout=120)
        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        self.ctx.log(f"✅ 已保存: {filepath}")

    def _vidu_sync_shots_from_script(self):
        script_page = self.ctx.get_page("Script")
        if not script_page: return
        content = script_page.get_content()
        if not content:
            messagebox.showinfo("提示", "Script 页面中没有脚本内容。")
            return
        
        import re
        prompt_pattern = re.compile(r"(?:英文|English)\s*\*{0,2}\s*Prompt\s*\*{0,2}\s*[:：]\s*(.+)", re.IGNORECASE)
        dur_pattern = re.compile(r"(?:时长|時長|Duration)\s*\*{0,2}\s*[:：]\s*(\d+(?:\.\d+)?)\s*(?:s|秒|sec)?", re.IGNORECASE)
        
        raw_prompts = []
        raw_durs = []
        for line in content.split("\n"):
            stripped = line.strip()
            pm = prompt_pattern.search(stripped)
            if pm: raw_prompts.append(re.sub(r"\*+", "", pm.group(1)).strip())
            dm = dur_pattern.search(stripped)
            if dm: raw_durs.append(float(dm.group(1)))
        
        if not raw_prompts: return
            
        shots = []
        for i, prompt in enumerate(raw_prompts):
            dur = raw_durs[i] if i < len(raw_durs) else 5.0
            shots.append({"num": i+1, "prompt": prompt, "duration": dur})

        for row in self._vidu_shot_rows:
            row["frame"].destroy()
        self._vidu_shot_rows = []
        self.vidu_shot_empty_label.pack_forget()

        for shot in shots:
            row_frame = ctk.CTkFrame(self.vidu_shot_list_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=2)
            ctk.CTkLabel(row_frame, text=f"#{shot['num']}", font=FONT_SMALL, text_color=C["accent"], width=30).pack(side="left")
            pt = ctk.CTkTextbox(row_frame, height=40, font=FONT_MONO_SM, fg_color=C["surface"], text_color=C["text"])
            pt.pack(side="left", padx=4, fill="x", expand=True)
            pt.insert("1.0", shot["prompt"])
            pt.configure(state="disabled")
            
            btn_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            btn_frame.pack(side="left", padx=2)
            ctk.CTkButton(btn_frame, text="▶", font=FONT_SMALL, width=28, fg_color=C["blue"], command=lambda p=shot["prompt"]: self._send_to_vidu(p)).pack(side="left", padx=1)
            ctk.CTkLabel(row_frame, text=f"{shot.get('duration', 5)}s", font=FONT_MONO_SM, text_color=C["warn"], width=30).pack(side="left", padx=2)
            self._vidu_shot_rows.append({"frame": row_frame, "prompt": shot["prompt"]})
        
        self.vidu_shot_count_label.configure(text=f"已同步 {len(shots)} 个镜头", text_color=C["green"])
        self.ctx.log(f"已从 Script 同步 {len(shots)} 个分镜")

    def _send_to_vidu(self, p):
        self.vidu_prompt_text.delete("1.0", "end")
        self.vidu_prompt_text.insert("1.0", p)
        self.ctx.log("Prompt 已填入提示词框")

    def _vidu_copy_all_shots(self):
        prompts = [r["prompt"] for r in self._vidu_shot_rows]
        self.ctx.root.clipboard_clear()
        self.ctx.root.clipboard_append("\n\n".join(prompts))
        self.ctx.log(f"已复制全部分镜提示词")
