"""Vidu video generation page mixin"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import requests
import json
import os
import time
import base64

from ..constants import (C, FONT_H2, FONT_BODY, FONT_MONO, FONT_MONO_SM, FONT_SMALL,
                         PAD_MD, PAD_LG, CORNER_RADIUS, CORNER_RADIUS_LG,
                         VIDU_BASE_URL, VIDU_MODELS, VIDU_STYLES, VIDU_RESOLUTIONS,
                         VIDU_ASPECT_RATIOS, VIDU_MOVEMENT_AMPLITUDES,
                         VIDU_CREDIT_RATES, VIDU_MODEL_DURATION)
from ..ui import SectionCard


class ViduMixin:

    def _build_page_vidu(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color=C["bg"],
                                         scrollbar_button_color=C["border"],
                                         scrollbar_button_hover_color=C["text3"])
        scroll.pack(fill="both", expand=True, padx=PAD_MD, pady=PAD_MD)

        ctk.CTkLabel(scroll, text="🎬 Vidu 视频生成引擎", font=FONT_H2,
                     text_color=C["accent"]).pack(anchor="w", pady=(0, 12))

        # API Key
        card = SectionCard(scroll, title="🔑 API Key 认证")
        card.pack(fill="x", pady=(0, 8))
        key_row = ctk.CTkFrame(card, fg_color="transparent")
        key_row.pack(fill="x", padx=16, pady=(4, 4))
        self.vidu_key_var = tk.StringVar(value=self.config.get("vidu_api_key", ""))
        self.vidu_key_entry = ctk.CTkEntry(key_row, textvariable=self.vidu_key_var, show="•",
                                            font=FONT_MONO, fg_color=C["surface2"],
                                            border_color=C["border"], corner_radius=8,
                                            placeholder_text="输入 Vidu API Key...")
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

        self.vidu_credits_label = ctk.CTkLabel(card, text="积分: --",
                                                font=FONT_SMALL, text_color=C["text3"])
        self.vidu_credits_label.pack(anchor="w", padx=16, pady=(0, 4))
        ctk.CTkButton(card, text="查询积分", font=FONT_SMALL, width=70,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text2"], corner_radius=6, height=26,
                       command=self._vidu_query_credits).pack(anchor="w", padx=16, pady=(0, 8))

        # Model & params
        card = SectionCard(scroll, title="⚙️ 渲染参数")
        card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(card, text="模型", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w", padx=16, pady=(4, 0))
        self.vidu_model_var = tk.StringVar(value=self.config.get("vidu_model", VIDU_MODELS[0]))
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
        self.vidu_duration_var = tk.StringVar(value=self.config.get("vidu_duration", "5"))
        self.vidu_duration_combo = ctk.CTkComboBox(dur_frame, variable=self.vidu_duration_var,
                                                     values=self._vidu_get_duration_options(),
                                                     font=FONT_MONO, fg_color=C["surface2"],
                                                     border_color=C["border"],
                                                     button_color=C["accent"], button_hover_color=C["accent_dim"],
                                                     dropdown_fg_color=C["surface2"], corner_radius=8,
                                                     command=lambda _: self._on_vidu_param_changed())
        self.vidu_duration_combo.pack(fill="x", pady=(2, 0))

        res_frame = ctk.CTkFrame(param_row, fg_color="transparent")
        res_frame.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(res_frame, text="分辨率", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w")
        self.vidu_resolution_var = tk.StringVar(value=self.config.get("vidu_resolution", "720p"))
        ctk.CTkComboBox(res_frame, variable=self.vidu_resolution_var, values=VIDU_RESOLUTIONS,
                         font=FONT_MONO, fg_color=C["surface2"], border_color=C["border"],
                         button_color=C["accent"], button_hover_color=C["accent_dim"],
                         dropdown_fg_color=C["surface2"], corner_radius=8,
                         command=lambda _: self._on_vidu_param_changed()
                         ).pack(fill="x", pady=(2, 0))

        self.vidu_cost_label = ctk.CTkLabel(card, text="预估积分: --",
                                             font=FONT_MONO_SM, text_color=C["warn"])
        self.vidu_cost_label.pack(anchor="w", padx=16, pady=(0, 8))

        # Advanced params
        card = SectionCard(scroll, title="🎛️ 高级参数")
        card.pack(fill="x", pady=(0, 8))

        adv_row1 = ctk.CTkFrame(card, fg_color="transparent")
        adv_row1.pack(fill="x", padx=16, pady=(4, 4))

        sty_f = ctk.CTkFrame(adv_row1, fg_color="transparent")
        sty_f.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkLabel(sty_f, text="风格 (q1/v1)", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w")
        self.vidu_style_var = tk.StringVar(value=self.config.get("vidu_style", "general"))
        ctk.CTkComboBox(sty_f, variable=self.vidu_style_var, values=VIDU_STYLES,
                         font=FONT_MONO, fg_color=C["surface2"], border_color=C["border"],
                         button_color=C["accent"], dropdown_fg_color=C["surface2"],
                         corner_radius=8, command=lambda _: self._save_vidu_config()
                         ).pack(fill="x", pady=(2, 0))

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

        mv_f = ctk.CTkFrame(adv_row2, fg_color="transparent")
        mv_f.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkLabel(mv_f, text="运动幅度 (q1/v1)", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w")
        self.vidu_movement_var = tk.StringVar(value=self.config.get("vidu_movement_amplitude", "auto"))
        ctk.CTkComboBox(mv_f, variable=self.vidu_movement_var, values=VIDU_MOVEMENT_AMPLITUDES,
                         font=FONT_MONO, fg_color=C["surface2"], border_color=C["border"],
                         button_color=C["accent"], dropdown_fg_color=C["surface2"],
                         corner_radius=8, command=lambda _: self._save_vidu_config()
                         ).pack(fill="x", pady=(2, 0))

        sd_f = ctk.CTkFrame(adv_row2, fg_color="transparent")
        sd_f.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(sd_f, text="随机种子 (0=随机)", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w")
        self.vidu_seed_var = tk.StringVar(value=self.config.get("vidu_seed", "0"))
        ctk.CTkEntry(sd_f, textvariable=self.vidu_seed_var, font=FONT_MONO,
                      fg_color=C["surface2"], border_color=C["border"], corner_radius=8
                      ).pack(fill="x", pady=(2, 0))

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

        # Reference image
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

        # Shot list panel
        self.vidu_shot_card = SectionCard(scroll, title="📋 Script 分镜列表 (一键导入)")
        self.vidu_shot_card.pack(fill="x", pady=(0, 8))

        shot_btn_row = ctk.CTkFrame(self.vidu_shot_card, fg_color="transparent")
        shot_btn_row.pack(fill="x", padx=16, pady=(4, 4))
        ctk.CTkButton(shot_btn_row, text="从 Script 导入分镜", font=FONT_SMALL,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["blue"], corner_radius=6, height=28,
                       command=self._vidu_import_from_script).pack(side="left")

        self.vidu_shot_list = ctk.CTkTextbox(self.vidu_shot_card, height=120, font=FONT_MONO_SM,
                                              fg_color=C["surface2"], text_color=C["text"],
                                              corner_radius=8, border_width=1, border_color=C["border"])
        self.vidu_shot_list.pack(fill="x", padx=16, pady=(4, 12))

        # Prompt input
        card = SectionCard(scroll, title="✏️ Prompt 提示词")
        card.pack(fill="x", pady=(0, 8))
        self.vidu_prompt_text = ctk.CTkTextbox(card, height=100, font=FONT_BODY,
                                                fg_color=C["surface2"], text_color=C["text"],
                                                corner_radius=8, border_width=1,
                                                border_color=C["border"])
        self.vidu_prompt_text.pack(fill="x", padx=16, pady=(4, 8))

        # Generate button
        self.vidu_gen_btn = ctk.CTkButton(scroll, text="🚀 生成视频", font=FONT_H2,
                                           fg_color=C["accent"], text_color=C["bg"],
                                           hover_color=C["accent2"], corner_radius=12,
                                           height=44, command=self.start_vidu_generate)
        self.vidu_gen_btn.pack(fill="x", padx=PAD_MD, pady=(0, 8))

        self.vidu_result_label = ctk.CTkLabel(scroll, text="", font=FONT_SMALL,
                                               text_color=C["text3"])
        self.vidu_result_label.pack(anchor="w", padx=PAD_MD, pady=(0, 16))

        self._on_vidu_param_changed()

    def _vidu_get_duration_options(self):
        model = self.vidu_model_var.get() if hasattr(self, "vidu_model_var") else VIDU_MODELS[0]
        lo, hi = VIDU_MODEL_DURATION.get(model, (1, 16))
        return [str(i) for i in range(lo, hi + 1)]

    def _vidu_on_model_changed(self):
        opts = self._vidu_get_duration_options()
        self.vidu_duration_combo.configure(values=opts)
        cur = self.vidu_duration_var.get()
        if cur not in opts:
            self.vidu_duration_var.set(opts[-1])
        self._on_vidu_param_changed()
        self._save_vidu_config()

    def _on_vidu_param_changed(self):
        try:
            dur = int(self.vidu_duration_var.get())
        except (ValueError, AttributeError):
            dur = 5
        res = self.vidu_resolution_var.get() if hasattr(self, "vidu_resolution_var") else "720p"
        rate = VIDU_CREDIT_RATES.get(res, 20)
        cost = rate * dur
        if hasattr(self, "vidu_cost_label"):
            self.vidu_cost_label.configure(text=f"预估积分: {cost}")
        self._save_vidu_config()

    def _save_vidu_config(self):
        self.config["vidu_api_key"] = self.vidu_key_var.get().strip()
        self.config["vidu_model"] = self.vidu_model_var.get()
        self.config["vidu_duration"] = self.vidu_duration_var.get()
        self.config["vidu_resolution"] = self.vidu_resolution_var.get()
        self.config["vidu_style"] = self.vidu_style_var.get()
        self.config["vidu_aspect_ratio"] = self.vidu_aspect_var.get()
        self.config["vidu_movement_amplitude"] = self.vidu_movement_var.get()
        self.config["vidu_seed"] = self.vidu_seed_var.get()
        self.config["vidu_bgm"] = self.vidu_bgm_var.get()
        self.config["vidu_audio"] = self.vidu_audio_var.get()
        self.config["vidu_off_peak"] = self.vidu_offpeak_var.get()
        self.config["vidu_watermark"] = self.vidu_watermark_var.get()
        from ..config import save_config
        save_config(self.config)

    def _toggle_vidu_key_vis(self):
        if self.vidu_key_visible.get():
            self.vidu_key_entry.configure(show="")
            self.vidu_key_visible.set(False)
        else:
            self.vidu_key_entry.configure(show="*")
            self.vidu_key_visible.set(True)

    def _browse_vidu_ref_image(self):
        path = filedialog.askopenfilename(title="选择参考图片",
                                           filetypes=[("图片", "*.png *.jpg *.jpeg *.webp"), ("所有文件", "*.*")])
        if path:
            self.vidu_ref_path_var.set(path)

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
                        self.safe_after(lambda: self.vidu_credits_label.configure(
                            text=f"积分: {credit}", text_color=C["green"]))
                        self.safe_after(lambda: messagebox.showinfo(
                            "验证成功", f"API Key 有效！\n剩余积分: {credit}"))
                    else:
                        self._vidu_log_msg("✅ API Key 有效，但无积分数据")
                        self.safe_after(lambda: messagebox.showinfo("验证成功", "API Key 有效"))
                elif resp.status_code == 401:
                    self._vidu_log_msg("❌ API Key 无效 (401)")
                    self.safe_after(lambda: messagebox.showerror("验证失败", "API Key 无效，请检查"))
                else:
                    self._vidu_log_msg(f"❌ 验证失败: HTTP {resp.status_code}")
                    self.safe_after(lambda: messagebox.showerror(
                        "验证失败", f"HTTP {resp.status_code}: {resp.text[:200]}"))
            except Exception as e:
                self._vidu_log_msg(f"❌ 验证异常: {e}")
                self.safe_after(lambda: messagebox.showerror("验证异常", str(e)))

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
                        self._vidu_log_msg(f"📊 积分: {credit} | 并发: {concur_now}/{concur_lim} | 排队: {queue}")
                        self.safe_after(lambda: self.vidu_credits_label.configure(
                            text=f"积分: {credit} | 并发: {concur_now}/{concur_lim}", text_color=C["green"]))
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

    def _vidu_log_msg(self, msg):
        ts = time.strftime("%H:%M:%S")
        self.safe_after(lambda: self.global_log.append(f"[{ts}] {msg}"))

    def _vidu_import_from_script(self):
        content = self.script_output.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo("提示", "Script 页面中没有脚本内容。")
            return
        self.vidu_shot_list.delete("1.0", "end")
        self.vidu_shot_list.insert("end", content)

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

        cost = self._vidu_calculate_cost()
        resolution = self.vidu_resolution_var.get()
        duration = self.vidu_duration_var.get()
        rate = VIDU_CREDIT_RATES.get(resolution, 20)
        model = self.vidu_model_var.get()

        confirm_msg = (
            f"📋 积分消耗核算\n{'─' * 32}\n"
            f"模型: {model}\n分辨率: {resolution}\n时长: {duration} 秒\n单价: {rate} 积分/秒\n"
            f"{'─' * 32}\n💰 预估消耗: {cost} 积分\n{'─' * 32}\n\n确认生成？"
        )
        if not messagebox.askyesno("积分核算确认", confirm_msg):
            self._vidu_log_msg("用户取消生成")
            return

        self._save_vidu_config()
        self.vidu_gen_btn.configure(state="disabled", text="⏳ 生成中...")
        self.safe_after(lambda: self.vidu_result_label.configure(
            text="正在生成，请查看终端日志...", text_color=C["accent2"]))

        threading.Thread(target=self._vidu_generate_worker,
                         args=(api_key, model, prompt, ref_path, int(duration), resolution),
                         daemon=True).start()

    def _vidu_generate_worker(self, api_key, model, prompt, ref_path, duration, resolution):
        try:
            headers = {"Authorization": f"Token {api_key}", "Content-Type": "application/json"}

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

            payload = {"model": model}
            is_i2v = bool(ref_path and os.path.exists(ref_path))
            if prompt:
                payload["prompt"] = prompt
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
            if "q3" in model:
                payload["audio"] = self.vidu_audio_var.get()
            if self.vidu_offpeak_var.get():
                payload["off_peak"] = True
            if self.vidu_watermark_var.get():
                payload["watermark"] = True

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
                self.safe_after(lambda: messagebox.showerror(
                    "提交失败", f"HTTP {resp.status_code}\n{resp.text[:300]}"))
                return

            task_id = resp.json().get("id", "")
            if not task_id:
                self._vidu_log_msg(f"❌ 未获取到任务 ID: {resp.text[:200]}")
                return
            self._vidu_log_msg(f"✅ 任务已提交 | ID: {task_id}")

            self._vidu_log_msg("⏱️ 开始轮询 (5秒间隔，10分钟超时)...")
            elapsed = 0
            max_wait = 600
            while elapsed < max_wait:
                time.sleep(5)
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
                        self.safe_after(lambda: self.vidu_result_label.configure(
                            text=f"✅ 完成！视频已保存到 output_video/", text_color=C["green"]))
                        return
                    elif status == "failed":
                        err = result.get("error_msg", result.get("message", "未知错误"))
                        self._vidu_log_msg(f"❌ 生成失败: {err}")
                        self.safe_after(lambda: self.vidu_result_label.configure(
                            text=f"❌ 失败: {err}", text_color=C["red"]))
                        return
                    else:
                        self._vidu_log_msg(f"[{elapsed}s] 状态: {status}")
                except Exception as e:
                    self._vidu_log_msg(f"⚠️ 轮询异常: {e}")

            self._vidu_log_msg(f"⏰ 超时 ({max_wait}s)，任务可能仍在处理")
            self.safe_after(lambda: self.vidu_result_label.configure(
                text="⏰ 轮询超时，请稍后手动查询", text_color=C["warn"]))

        except Exception as e:
            self._vidu_log_msg(f"💥 异常: {e}")
        finally:
            self.safe_after(lambda: self.vidu_gen_btn.configure(state="normal", text="🚀 生成视频"))

    def _vidu_calculate_cost(self):
        try:
            dur = int(self.vidu_duration_var.get())
        except (ValueError, AttributeError):
            dur = 5
        res = self.vidu_resolution_var.get() if hasattr(self, "vidu_resolution_var") else "720p"
        return VIDU_CREDIT_RATES.get(res, 20) * dur

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
            self.safe_after(lambda: self.vidu_result_label.configure(
                text=f"✅ 已保存: {filename}", text_color=C["green"]))
        except Exception as e:
            self._vidu_log_msg(f"❌ 下载失败: {e}")
