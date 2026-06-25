"""Voice/TTS page mixin"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import requests
import json
import os
import time as _time
import base64
import mimetypes
import re

from ..constants import (C, FONT_TITLE, FONT_H2, FONT_BODY, FONT_MONO, FONT_MONO_SM, FONT_SMALL,
                         PAD_MD, PAD_LG, PAD_SM, PAD_XS, CORNER_RADIUS,
                         BTN_HEIGHT_SM, BTN_HEIGHT_MD, BTN_HEIGHT_LG)
from ..ui import SectionCard, CyberButton


class VoiceMixin:

    def _build_page_voice(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color=C["bg"],
                                         scrollbar_button_hover_color=C["text3"])
        scroll.pack(fill="both", expand=True, padx=PAD_MD, pady=PAD_MD)

        ctk.CTkLabel(scroll, text="AI 智能配音", font=FONT_TITLE,
                     text_color=C["accent"]).pack(anchor="w", pady=(0, PAD_LG))

        # Engine selection
        self._tts_engine_card = SectionCard(scroll, title="TTS 引擎")
        self._tts_engine_card.pack(fill="x", pady=(0, 8))
        self.tts_engine_var = tk.StringVar(value=self.config.get("tts_engine", "bailian"))
        ctk.CTkRadioButton(self._tts_engine_card, text="阿里云 DashScope TTS (云端商业)",
                            variable=self.tts_engine_var, value="bailian",
                            font=FONT_BODY, fg_color=C["accent"], text_color=C["text"],
                            hover_color=C["accent2"], command=self._on_tts_engine_change).pack(anchor="w", padx=16, pady=4)
        ctk.CTkRadioButton(self._tts_engine_card, text="GPT-SoVITS (本地免费)",
                            variable=self.tts_engine_var, value="sovits",
                            font=FONT_BODY, fg_color=C["accent"], text_color=C["text"],
                            hover_color=C["accent2"], command=self._on_tts_engine_change).pack(anchor="w", padx=16, pady=4)
        ctk.CTkRadioButton(self._tts_engine_card, text="小米 MiMo (百亿额度)",
                            variable=self.tts_engine_var, value="mimo",
                            font=FONT_BODY, fg_color=C["accent"], text_color=C["text"],
                            hover_color=C["accent2"], command=self._on_tts_engine_change).pack(anchor="w", padx=16, pady=(0, 10))

        # Bailian TTS
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
        ctk.CTkLabel(self.bailian_tts_frame, text="预设音色:", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w", padx=16, pady=(8, 0))
        self.tts_voice_var = tk.StringVar(value=voice_default)
        ctk.CTkComboBox(self.bailian_tts_frame, variable=self.tts_voice_var,
                         values=list(self.tts_voice_map.keys()), font=FONT_BODY,
                         dropdown_font=FONT_BODY, fg_color=C["surface2"],
                         border_color=C["border"], button_color=C["border"],
                         button_hover_color=C["text3"], corner_radius=8).pack(fill="x", padx=16, pady=(2, 8))
        ctk.CTkLabel(self.bailian_tts_frame, text="自定义模型 ID (可选):", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w", padx=16)
        self.tts_custom_model_var = tk.StringVar(value=self.config.get("tts_custom_model", ""))
        ctk.CTkEntry(self.bailian_tts_frame, textvariable=self.tts_custom_model_var,
                      font=FONT_MONO, fg_color=C["surface2"], border_color=C["border"],
                      corner_radius=8).pack(fill="x", padx=16, pady=(2, 12))

        # SoVITS
        self.sovits_frame = SectionCard(scroll, title="GPT-SoVITS (本地免费) 配置")
        ctk.CTkLabel(self.sovits_frame, text="VibeVoice API 地址:", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w", padx=16, pady=(8, 0))
        self.sovits_url_var = tk.StringVar(value=self.config.get("sovits_url", "http://127.0.0.1:8080"))
        ctk.CTkEntry(self.sovits_frame, textvariable=self.sovits_url_var, font=FONT_MONO,
                      fg_color=C["surface2"], border_color=C["border"],
                      corner_radius=8).pack(fill="x", padx=16, pady=(2, 8))
        ctk.CTkLabel(self.sovits_frame, text="一键启动脚本 (.bat):", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w", padx=16)
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
        ctk.CTkLabel(self.sovits_frame, text="角色名称:", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w", padx=16, pady=(4, 0))
        char_row = ctk.CTkFrame(self.sovits_frame, fg_color="transparent")
        char_row.pack(fill="x", padx=16, pady=(2, 8))
        self.sovits_character_var = tk.StringVar(value=self.config.get("sovits_character", ""))
        self.sovits_character_combo = ctk.CTkComboBox(char_row, variable=self.sovits_character_var, values=[""],
            font=FONT_BODY, dropdown_font=FONT_BODY, fg_color=C["surface2"], border_color=C["border"],
            button_color=C["border"], button_hover_color=C["text3"], corner_radius=8, state="readonly")
        self.sovits_character_combo.pack(side="left", fill="x", expand=True)
        self.sovits_refresh_btn = ctk.CTkButton(char_row, text="刷新列表", width=80, font=FONT_SMALL,
            fg_color=C["accent"], text_color=C["bg"], hover_color=C["accent2"],
            corner_radius=6, height=30, command=self._refresh_vibevoice_characters)
        self.sovits_refresh_btn.pack(side="left", padx=(6, 0))
        ctk.CTkLabel(self.sovits_frame, text="情绪基调:", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w", padx=16)
        self.sovits_emotion_var = tk.StringVar(value=self.config.get("sovits_emotion", "平静"))
        self.sovits_emotion_combo = ctk.CTkComboBox(self.sovits_frame, variable=self.sovits_emotion_var, values=["平静"],
            font=FONT_BODY, dropdown_font=FONT_BODY, fg_color=C["surface2"], border_color=C["border"],
            button_color=C["border"], button_hover_color=C["text3"], corner_radius=8)
        self.sovits_emotion_combo.pack(fill="x", padx=16, pady=(2, 12))

        # MiMo TTS
        self.mimo_tts_frame = SectionCard(scroll, title="小米 MiMo TTS 配置")
        ctk.CTkLabel(self.mimo_tts_frame, text="API Key:", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w", padx=16, pady=(8, 0))
        self.mimo_api_key_var = tk.StringVar(value=self.config.get("mimo_api_key", ""))
        self.mimo_key_entry = ctk.CTkEntry(self.mimo_tts_frame, textvariable=self.mimo_api_key_var,
                                            show="*", font=FONT_MONO, fg_color=C["surface2"],
                                            border_color=C["border"], corner_radius=8)
        self.mimo_key_entry.pack(fill="x", padx=16, pady=(2, 8))
        mimo_key_row = ctk.CTkFrame(self.mimo_tts_frame, fg_color="transparent")
        mimo_key_row.pack(fill="x", padx=16, pady=(0, 8))
        self.mimo_key_visible = tk.BooleanVar(value=False)
        ctk.CTkButton(mimo_key_row, text="显示/隐藏", width=100, font=FONT_SMALL,
                      fg_color=C["surface2"], hover_color=C["border"],
                      text_color=C["text"], corner_radius=6, height=28,
                      command=self._toggle_mimo_key_vis).pack(side="left")
        ctk.CTkLabel(mimo_key_row, text="填入 MiMo API Key", font=FONT_SMALL, text_color=C["text3"]).pack(side="left", padx=8)
        ctk.CTkLabel(self.mimo_tts_frame, text="模型选择:", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w", padx=16)
        self.mimo_model_var = tk.StringVar(value=self.config.get("mimo_model", "MiMo-V2.5-TTS"))
        mimo_models = ["MiMo-V2.5-TTS (标准)", "MiMo-V2.5-TTS-VoiceClone (声音复刻)", "MiMo-V2.5-TTS-VoiceDesign (声音设计)"]
        ctk.CTkComboBox(self.mimo_tts_frame, variable=self.mimo_model_var, values=mimo_models,
                        font=FONT_BODY, dropdown_font=FONT_BODY, fg_color=C["surface2"],
                        border_color=C["border"], button_color=C["border"],
                        button_hover_color=C["text3"], corner_radius=8).pack(fill="x", padx=16, pady=(2, 8))
        ctk.CTkLabel(self.mimo_tts_frame, text="预设音色:", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w", padx=16)
        self.mimo_voice_var = tk.StringVar(value=self.config.get("mimo_voice", "冰糖"))
        mimo_voices = ["冰糖 (清甜女声)", "茉莉 (温柔女声)", "苏打 (活力女声)", "白桦 (沉稳女声)",
                       "Mia (英文女声)", "Chloe (英文女声)", "Milo (英文男声)", "Dean (英文男声)", "mimo_default (默认)"]
        self.mimo_voice_id_map = {
            "冰糖 (清甜女声)": "bingtang", "茉莉 (温柔女声)": "mohuali",
            "苏打 (活力女声)": "sudahuoli", "白桦 (沉稳女声)": "baihuashenzhu",
            "Mia (英文女声)": "mia", "Chloe (英文女声)": "chloe",
            "Milo (英文男声)": "milo", "Dean (英文男声)": "dean",
            "mimo_default (默认)": "mimo_default",
        }
        ctk.CTkComboBox(self.mimo_tts_frame, variable=self.mimo_voice_var, values=mimo_voices,
                        font=FONT_BODY, dropdown_font=FONT_BODY, fg_color=C["surface2"],
                        border_color=C["border"], button_color=C["border"],
                        button_hover_color=C["text3"], corner_radius=8).pack(fill="x", padx=16, pady=(2, 12))

        self._on_tts_engine_change()

        # Mode switch
        self.tts_adv_mode_var = tk.StringVar(value=self.config.get("tts_adv_mode", "preset"))
        mode_switch_frame = ctk.CTkFrame(scroll, fg_color=C["surface"], corner_radius=12, border_width=1, border_color=C["border"])
        mode_switch_frame.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(mode_switch_frame, text="配音模式", font=FONT_H2, text_color=C["accent"]).pack(anchor="w", padx=16, pady=(12, 8))
        self._mode_btn_row = ctk.CTkFrame(mode_switch_frame, fg_color="transparent")
        self._mode_btn_row.pack(fill="x", padx=16, pady=(0, 12))
        self._btn_preset = ctk.CTkButton(self._mode_btn_row, text="预设音色", font=FONT_H2,
            fg_color=C["accent"], text_color=C["bg"], hover_color=C["accent2"],
            corner_radius=10, height=44, command=lambda: self._switch_mode("preset"))
        self._btn_preset.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self._btn_clone = ctk.CTkButton(self._mode_btn_row, text="声音复刻", font=FONT_H2,
            fg_color=C["surface2"], text_color=C["text"], hover_color=C["border"],
            corner_radius=10, height=44, command=lambda: self._switch_mode("clone"))
        self._btn_clone.pack(side="left", fill="x", expand=True, padx=(4, 0))
        self._mode_hint = ctk.CTkLabel(mode_switch_frame, text="当前：预设音色 + 情感指令驱动",
                                        font=FONT_SMALL, text_color=C["text3"])
        self._mode_hint.pack(anchor="w", padx=16, pady=(0, 12))

        # Advanced controls
        self._tts_advanced_card = SectionCard(scroll, title="高级控制")
        self._tts_advanced_card.pack(fill="x", pady=(0, 8))
        self.tts_prompt_label = ctk.CTkLabel(self._tts_advanced_card, text="情感/语气指令:", font=FONT_SMALL, text_color=C["text2"])
        self.tts_prompt_label.pack(anchor="w", padx=16, pady=(4, 0))
        ctk.CTkLabel(self._tts_advanced_card, text="快速模板:", font=FONT_SMALL, text_color=C["text3"]).pack(anchor="w", padx=16, pady=(2, 0))
        self.tts_emotion_template_var = tk.StringVar(value="自定义")
        self._emotion_templates = {
            "自定义": "", "悬疑低沉": "故作神秘，压低声音，语速缓慢，带有紧张感",
            "活泼欢快": "声音明亮，语速偏快，充满活力和喜悦",
            "悲伤低落": "声音低沉，语速缓慢，带有哽咽和伤感",
            "愤怒大吼": "声音洪亮，语气强烈，充满愤怒和压迫感",
            "温柔轻语": "声音轻柔，语速缓慢，温柔体贴",
            "严肃庄重": "声音沉稳，语气正式，充满权威感",
            "俏皮可爱": "声音活泼，语调上扬，带有调皮和可爱感",
        }
        ctk.CTkComboBox(self._tts_advanced_card, variable=self.tts_emotion_template_var,
            values=list(self._emotion_templates.keys()), font=FONT_BODY, dropdown_font=FONT_BODY,
            fg_color=C["surface2"], border_color=C["border"], button_color=C["border"],
            button_hover_color=C["text3"], corner_radius=8,
            command=self._on_emotion_template_change).pack(fill="x", padx=16, pady=(2, 4))
        self.tts_prompt_text_var = tk.StringVar(value=self.config.get("tts_prompt_text", ""))
        self.tts_prompt_entry = ctk.CTkEntry(self._tts_advanced_card, textvariable=self.tts_prompt_text_var,
            font=FONT_BODY, placeholder_text="如：用悲伤且颤抖的声音缓缓道来",
            fg_color=C["surface2"], border_color=C["border"], corner_radius=8)
        self.tts_prompt_entry.pack(fill="x", padx=16, pady=(2, 8))

        self.tts_ref_label = ctk.CTkLabel(self._tts_advanced_card, text="参考音频 (用于声音复刻):", font=FONT_SMALL, text_color=C["text2"])
        self.tts_ref_label.pack(anchor="w", padx=16)
        ref_row = ctk.CTkFrame(self._tts_advanced_card, fg_color="transparent")
        ref_row.pack(fill="x", padx=16, pady=(2, 12))
        self.tts_ref_audio_var = tk.StringVar(value=self.config.get("tts_ref_audio", ""))
        self.tts_ref_entry = ctk.CTkEntry(ref_row, textvariable=self.tts_ref_audio_var, font=FONT_MONO_SM,
            placeholder_text="选择 .wav 参考音频文件", fg_color=C["surface2"], border_color=C["border"], corner_radius=8)
        self.tts_ref_entry.pack(side="left", fill="x", expand=True)
        self.tts_ref_btn = ctk.CTkButton(ref_row, text="浏览", width=60, font=FONT_SMALL,
            fg_color=C["surface2"], hover_color=C["border"], text_color=C["text"],
            corner_radius=6, height=30, command=self._browse_tts_ref_audio)
        self.tts_ref_btn.pack(side="left", padx=(6, 0))
        self._switch_mode(self.config.get("tts_adv_mode", "preset"))

        # Dialogue input
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
                       command=lambda: self.tts_text.delete("1.0", "end")).pack(side="left", padx=6)
        self.tts_text = ctk.CTkTextbox(card, font=FONT_BODY, fg_color=C["surface2"],
                                        text_color=C["text"], corner_radius=8,
                                        border_width=1, border_color=C["border"])
        self.tts_text.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        # Audio output dir
        ctk.CTkLabel(card, text="音频保存目录:", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w", padx=16, pady=(4, 0))
        audio_dir_row = ctk.CTkFrame(card, fg_color="transparent")
        audio_dir_row.pack(fill="x", padx=16, pady=(2, 8))
        self.tts_audio_dir_var = tk.StringVar(value="")
        self.tts_audio_dir_entry = ctk.CTkEntry(audio_dir_row, textvariable=self.tts_audio_dir_var,
            font=FONT_MONO_SM, placeholder_text="留空则使用默认 output_audio 目录",
            fg_color=C["surface2"], border_color=C["border"], corner_radius=8)
        self.tts_audio_dir_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(audio_dir_row, text="选择目录", width=80, font=FONT_SMALL,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text"], corner_radius=6, height=30,
                       command=self._browse_tts_audio_dir).pack(side="left", padx=(6, 0))

        self.tts_gen_btn = CyberButton(scroll, text="⚡ 一键批量生成音频",
                                        variant="primary", height=BTN_HEIGHT_LG,
                                        command=self.start_tts_generate)
        self.tts_gen_btn.pack(fill="x", padx=PAD_LG, pady=(PAD_SM, PAD_MD))
        self.tts_log = self.global_log

    def _on_tts_engine_change(self):
        engine = self.tts_engine_var.get()
        if engine == "bailian":
            self.sovits_frame.pack_forget(); self.mimo_tts_frame.pack_forget()
            self.bailian_tts_frame.pack(fill="x", pady=(0, 8), after=self._tts_engine_card)
        elif engine == "mimo":
            self.bailian_tts_frame.pack_forget(); self.sovits_frame.pack_forget()
            self.mimo_tts_frame.pack(fill="x", pady=(0, 8), after=self._tts_engine_card)
        else:
            self.bailian_tts_frame.pack_forget(); self.mimo_tts_frame.pack_forget()
            self.sovits_frame.pack(fill="x", pady=(0, 8), after=self._tts_engine_card)

    def _switch_mode(self, mode):
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
            self.tts_ref_entry.configure(state="normal"); self.tts_ref_entry.delete(0, "end"); self.tts_ref_entry.configure(state="disabled")
            self.tts_ref_btn.configure(state="disabled"); self.tts_ref_label.configure(text_color=C["text3"])
        else:
            self.tts_ref_entry.configure(state="normal"); self.tts_ref_label.configure(text_color=C["text2"])
            self.tts_ref_btn.configure(state="normal")
            self.tts_prompt_entry.configure(state="normal"); self.tts_prompt_entry.delete(0, "end"); self.tts_prompt_entry.configure(state="disabled")
            self.tts_prompt_label.configure(text_color=C["text3"])

    def _on_emotion_template_change(self, choice):
        template_text = self._emotion_templates.get(choice, "")
        if template_text:
            self.tts_prompt_text_var.set(template_text)
        if choice == "自定义":
            self.tts_prompt_text_var.set("")

    def _toggle_mimo_key_vis(self):
        if self.mimo_key_visible.get():
            self.mimo_key_entry.configure(show=""); self.mimo_key_visible.set(False)
        else:
            self.mimo_key_entry.configure(show="*"); self.mimo_key_visible.set(True)

    def _extract_dialogue(self):
        content = self.script_output.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo("提示", "Script 页面中没有脚本内容。")
            return
        dialogue_pattern = re.compile(r"(?:台词|旁白|中文台词|对白|独白|配音文本)\s*\*{0,2}\s*[:：]\s*(.+)", re.IGNORECASE)
        visual_pattern = re.compile(r"(?:画面描述|Visual Description)\s*[:：]\s*(.+)", re.IGNORECASE)
        dialogue_lines = []
        for line in content.split("\n"):
            stripped = line.strip()
            if not stripped: continue
            dm = dialogue_pattern.search(stripped)
            if dm:
                text = re.sub(r"\*+", "", dm.group(1)).strip()
                if text: dialogue_lines.append(text)
                continue
            vm = visual_pattern.search(stripped)
            if vm:
                text = re.sub(r"\*+", "", vm.group(1)).strip()
                if text: dialogue_lines.append(text)
        if dialogue_lines:
            self.tts_text.delete("1.0", "end")
            self.tts_text.insert("end", "\n".join(dialogue_lines))
            self._tts_log_msg(f"提取到 {len(dialogue_lines)} 条台词/旁白")
        else:
            messagebox.showinfo("提示", "未从脚本中提取到台词/旁白。\n请确保脚本中有「台词：」或「旁白：」关键词。")

    def _tts_log_msg(self, msg):
        ts = time.strftime("%H:%M:%S") if 'time' in dir() else _time.strftime("%H:%M:%S")
        self.safe_after(lambda: self.global_log.append(f"[{ts}] {msg}"))

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
        if " (" in mimo_model_display: mimo_model_display = mimo_model_display.split(" (")[0]
        self.config["mimo_model"] = mimo_model_display
        self.config["mimo_voice"] = self.mimo_voice_var.get().strip()
        from ..config import save_config
        save_config(self.config)

    def _browse_tts_audio_dir(self):
        path = filedialog.askdirectory(title="选择音频保存目录")
        if path: self.tts_audio_dir_var.set(path)

    def _browse_sovits_bat(self):
        path = filedialog.askopenfilename(title="选择启动脚本",
                                           filetypes=[("批处理", "*.bat"), ("所有文件", "*.*")])
        if path: self.sovits_bat_var.set(path)

    def _browse_tts_ref_audio(self):
        path = filedialog.askopenfilename(title="选择参考音频 (用于声音复刻)",
                                           filetypes=[("音频文件", "*.wav *.mp3 *.flac *.m4a"), ("所有文件", "*.*")])
        if path: self.tts_ref_audio_var.set(path)

    def _get_tts_audio_dir(self):
        custom = self.tts_audio_dir_var.get().strip()
        if custom and os.path.isdir(custom): return custom
        return self._get_output_dir("output_audio")

    def _check_sovits_status(self, api_url):
        try:
            resp = requests.get(api_url, timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    def _refresh_vibevoice_characters(self):
        api_url = self.sovits_url_var.get().strip().rstrip("/")
        if not api_url:
            self._tts_log_msg("错误: 请填写 VibeVoice API 地址！")
            return
        self.sovits_refresh_btn.configure(state="disabled", text="拉取中...")

        def _worker():
            if not self._check_sovits_status(api_url):
                self._tts_log_msg("[自动化] VibeVoice 未运行，正在拉起...")
                bat_path = self.sovits_bat_var.get().strip()
                if bat_path and os.path.exists(bat_path):
                    import subprocess
                    try:
                        subprocess.Popen(["cmd", "/c", bat_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
                        self._tts_log_msg(f"[自动化] 已执行: {bat_path}")
                    except Exception as e:
                        self._tts_log_msg(f"[自动化] 启动失败: {e}")
                        self.safe_after(lambda: self.sovits_refresh_btn.configure(state="normal", text="刷新列表"))
                        return
                else:
                    self._tts_log_msg(f"[自动化] 未找到启动脚本: {bat_path}")
                    self.safe_after(lambda: self.sovits_refresh_btn.configure(state="normal", text="刷新列表"))
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
                    self.safe_after(lambda: self.sovits_refresh_btn.configure(state="normal", text="刷新列表"))
                    return
            else:
                self._tts_log_msg("[自动化] VibeVoice 已在线")

            try:
                resp = requests.get(f"{api_url}/api/characters", timeout=5)
                if resp.status_code != 200:
                    self._tts_log_msg(f"获取角色列表失败: HTTP {resp.status_code}")
                    self.safe_after(lambda: self.sovits_refresh_btn.configure(state="normal", text="刷新列表"))
                    return
                chars = resp.json()
                if not chars:
                    self._tts_log_msg("角色列表为空，请先在 VibeVoice 中创建角色")
                    self.safe_after(lambda: self.sovits_refresh_btn.configure(state="normal", text="刷新列表"))
                    return
                names = [c.get("name", "?") for c in chars]
                self._char_name_to_id = {c.get("name", ""): c.get("id", "") for c in chars}
                current = self.sovits_character_var.get().strip()
                target = chars[0]
                for c in chars:
                    if c.get("name") == current:
                        target = c; break
                emotions = list(target.get("emotions", {}).keys())
                self.safe_after(lambda: self._apply_character(target, emotions, names))
            except Exception as e:
                self._tts_log_msg(f"连接 VibeVoice 失败: {e}")
            self.safe_after(lambda: self.sovits_refresh_btn.configure(state="normal", text="刷新列表"))

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_character(self, char_info, emotions, all_names=None):
        if all_names: self.sovits_character_combo.configure(values=all_names)
        self.sovits_character_var.set(char_info.get("name", ""))
        if emotions:
            self.sovits_emotion_combo.configure(values=emotions)
            default_emo = char_info.get("default_emotion", emotions[0])
            self.sovits_emotion_var.set(default_emo if default_emo in emotions else emotions[0])
        self._tts_log_msg(f"已加载角色: {char_info.get('name', '?')}，情绪: {', '.join(emotions)}")

    def _open_audio_output(self):
        out_dir = self._get_tts_audio_dir()
        os.makedirs(out_dir, exist_ok=True)
        os.startfile(out_dir)

    def _extract_audio_data(self, response):
        AUDIO_KEYS = ("audio", "audio_url", "url", "speech", "audio_data")

        def _pick_audio_from_dict(d):
            for key in AUDIO_KEYS:
                val = d.get(key)
                if val: return val
            return None

        def _resolve(val):
            if isinstance(val, str) and val.startswith("http"):
                return requests.get(val, timeout=30).content
            if isinstance(val, (bytes, bytearray)): return val
            if isinstance(val, str):
                try:
                    decoded = base64.b64decode(val)
                    if len(decoded) > 100: return decoded
                except Exception: pass
            return val if isinstance(val, (bytes, bytearray)) else None

        try:
            output = getattr(response, "output", None)
            if output and isinstance(output, dict):
                val = _pick_audio_from_dict(output)
                if val: return _resolve(val)
                for key in ("results", "choices"):
                    items = output.get(key)
                    if items and isinstance(items, list):
                        for item in items:
                            if isinstance(item, dict):
                                val = _pick_audio_from_dict(item)
                                if val: return _resolve(val)
        except Exception: pass
        try:
            if isinstance(response, dict):
                output = response.get("output", {})
                if isinstance(output, dict):
                    val = _pick_audio_from_dict(output)
                    if val: return _resolve(val)
                val = _pick_audio_from_dict(response)
                if val: return _resolve(val)
                data = response.get("data")
                if isinstance(data, (bytes, bytearray)): return data
        except Exception: pass
        return None

    def _pcm_to_wav(self, pcm_data, out_path, sample_rate=24000, channels=1, sample_width=2):
        import wave
        with wave.open(out_path, "wb") as wf:
            wf.setnchannels(channels); wf.setsampwidth(sample_width)
            wf.setframerate(sample_rate); wf.writeframes(pcm_data)

    def _tts_audio_name(self, idx, voice_name, text, ext=".wav"):
        voice = voice_name.strip() if voice_name else "默认"
        clean = text[:4] if text else ""
        clean = re.sub(r'[\\/:*?"<>|，。！？、；：\s\.\!\?\,\;\:]', '', clean)
        return f"{voice}_{clean}_{idx}{ext}"

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

    def _tts_generate_bailian(self, lines):
        try:
            from dashscope.audio.tts import SpeechSynthesizer
        except ImportError:
            self._tts_log_msg("错误: dashscope 未安装！请 pip install dashscope")
            self.safe_after(lambda: self.tts_gen_btn.configure(state="normal", text="一键批量生成音频"))
            return
        import dashscope
        dashscope.api_key = self.config.get("bailian_api_key", "")
        if not dashscope.api_key:
            self._tts_log_msg("错误: 请先配置百炼 API Key！")
            self.safe_after(lambda: self.tts_gen_btn.configure(state="normal", text="一键批量生成音频"))
            return
        voice_display = self.tts_voice_var.get()
        voice_id = self.tts_voice_map.get(voice_display, "longcheng")
        custom_model = self.tts_custom_model_var.get().strip()
        adv_mode = self.tts_adv_mode_var.get()
        model = custom_model if custom_model else ("cosyvoice-v2" if adv_mode == "clone" else "cosyvoice-v1")
        voice = None if custom_model else voice_id

        prompt_audio_url = None; use_clone = False
        if adv_mode == "clone":
            ref_audio_path = self.tts_ref_audio_var.get().strip()
            prompt_text = ""
            if ref_audio_path and os.path.isfile(ref_audio_path):
                self._tts_log_msg(f"[声音复刻] 上传参考音频: {os.path.basename(ref_audio_path)}")
                try:
                    upload_resp = dashscope.Files.upload(file_path=os.path.abspath(ref_audio_path))
                    uploaded = upload_resp.output.get("uploaded_files", [])
                    if uploaded:
                        prompt_audio_url = uploaded[0].get("file_id", ""); use_clone = True
                        self._tts_log_msg(f"[声音复刻] 上传成功，file_id={prompt_audio_url}")
                    else:
                        self._tts_log_msg(f"[声音复刻] 上传失败: {upload_resp.output.get('failed_uploads', [])}")
                except Exception as e:
                    self._tts_log_msg(f"[声音复刻] 上传异常: {type(e).__name__}: {e}")
            else:
                self._tts_log_msg("[声音复刻] 未选择参考音频或文件不存在，回退到预设音色")
        else:
            prompt_text = self.tts_prompt_text_var.get().strip()
            if prompt_text: self._tts_log_msg(f"[情感指令] {prompt_text}")

        out_dir = self._get_tts_audio_dir()
        os.makedirs(out_dir, exist_ok=True)
        self._tts_log_msg(f"TTS 模型: {model} | 音色: {voice or '自定义'} | 模式: {'零样本复刻' if use_clone else '预设音色+情感指令'}")
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
            if not text: self._tts_log_msg(f"[{i}/{len(lines)}] 跳过空行"); continue
            final_text = f"{prompt_text}：{text}" if prompt_text else text
            self._tts_log_msg(f"[{i}/{len(lines)}] 生成中: {text[:30]}...")
            audio_data = None; used_sample_rate = 24000; last_error = None
            for sample_rate in [24000, 48000, 16000]:
                try:
                    kwargs = {"model": model, "text": final_text, "sample_rate": sample_rate}
                    if use_clone and prompt_audio_url: kwargs["prompt_audio"] = prompt_audio_url
                    elif voice: kwargs["voice"] = voice
                    kwargs = {k: v for k, v in kwargs.items() if v not in (None, "", 0)}
                    response = SpeechSynthesizer.call(**kwargs)
                    audio_data = self._extract_audio_data(response)
                    if audio_data: used_sample_rate = sample_rate; break
                    last_error = f"DashScope返回无音频 (rate={sample_rate})"
                except Exception as e:
                    last_error = f"{type(e).__name__}: {e}"
                    err_lower = last_error.lower()
                    if any(kw in err_lower for kw in ["quota", "balance", "insufficient", "429", "rate limit", "余额", "配额"]):
                        self._bailian_block(f"TTS 算力不足: {last_error[:200]}")
                        return
                    continue
            if audio_data:
                name_tag = os.path.splitext(os.path.basename(ref_audio_path))[0] if (use_clone and self.tts_ref_audio_var.get().strip()) else (voice_display.split(" ")[0] if voice_display else "自定义")
                fname = self._tts_audio_name(i, name_tag, text)
                out_path = os.path.join(out_dir, fname)
                raw_bytes = base64.b64decode(audio_data) if isinstance(audio_data, str) else audio_data
                if raw_bytes[:4] == b'RIFF':
                    with open(out_path, "wb") as f: f.write(raw_bytes)
                else:
                    self._pcm_to_wav(raw_bytes, out_path, sample_rate=used_sample_rate)
                self._tts_log_msg(f"[{i}/{len(lines)}] 已保存: {fname}")
                success += 1
            else:
                self._tts_log_msg(f"[{i}/{len(lines)}] 生成失败: {last_error}"); fail += 1
            _time.sleep(0.3)
        self._tts_log_msg("=" * 40)
        self._tts_log_msg(f"完成: 成功 {success}，失败 {fail}")
        self.safe_after(lambda: self.tts_gen_btn.configure(state="normal", text="一键批量生成音频"))
        if success > 0:
            messagebox.showinfo("完成", f"音频生成完成！\n成功: {success}\n保存至: {out_dir}")

    def _tts_generate_sovits(self, lines):
        import subprocess
        api_url = self.sovits_url_var.get().strip().rstrip("/")
        if not api_url:
            self._tts_log_msg("错误: 请填写 VibeVoice API 地址！")
            self.safe_after(lambda: self.tts_gen_btn.configure(state="normal", text="一键批量生成音频"))
            return
        character = self.sovits_character_var.get().strip()
        emotion = self.sovits_emotion_var.get().strip()
        if not character:
            self._tts_log_msg("错误: 请填写角色名称！")
            self.safe_after(lambda: self.tts_gen_btn.configure(state="normal", text="一键批量生成音频"))
            return
        out_dir = self._get_tts_audio_dir()
        os.makedirs(out_dir, exist_ok=True)
        synth_url = f"{api_url}/api/synthesize"

        if not self._check_sovits_status(api_url):
            self._tts_log_msg("[自动化] VibeVoice 未运行，正在拉起...")
            bat_path = self.sovits_bat_var.get().strip()
            if bat_path and os.path.exists(bat_path):
                try:
                    subprocess.Popen(["cmd", "/c", bat_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
                    self._tts_log_msg(f"[自动化] 已执行: {bat_path}")
                except Exception as e:
                    self._tts_log_msg(f"[自动化] 启动失败: {e}")
                    self.safe_after(lambda: self.tts_gen_btn.configure(state="normal", text="一键批量生成音频"))
                    return
            else:
                self._tts_log_msg(f"[自动化] 未找到脚本: {bat_path}")
                self.safe_after(lambda: self.tts_gen_btn.configure(state="normal", text="一键批量生成音频"))
                return
            self._tts_log_msg("[自动化] 等待引擎启动...")
            for elapsed in range(2, 62, 2):
                _time.sleep(2)
                if self._check_sovits_status(api_url):
                    self._tts_log_msg(f"[自动化] 引擎唤醒成功！（耗时 {elapsed} 秒）"); break
                self._tts_log_msg(f"[自动化] 等待中... ({elapsed}/60s)")
            else:
                self._tts_log_msg("[自动化] 超时：60 秒内引擎未响应")
                self.safe_after(lambda: self.tts_gen_btn.configure(state="normal", text="一键批量生成音频"))
                return
        else:
            self._tts_log_msg("[自动化] VibeVoice 已在线")

        adv_mode = self.tts_adv_mode_var.get()
        if adv_mode == "clone":
            ref_audio_path = self.tts_ref_audio_var.get().strip()
            prompt_text = ""
            has_ref = ref_audio_path and os.path.isfile(ref_audio_path)
            if has_ref: self._tts_log_msg(f"[声音复刻] 参考音频: {os.path.basename(ref_audio_path)}")
        else:
            ref_audio_path = ""; prompt_text = self.tts_prompt_text_var.get().strip(); has_ref = False
            if prompt_text: self._tts_log_msg(f"[情感指令] {prompt_text}")

        char_id = self._char_name_to_id.get(character, character)
        self._tts_log_msg(f"角色: {character} | 情绪: {emotion or '默认'} | character_id: {char_id}")
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
            if not text: self._tts_log_msg(f"[{i}/{len(lines)}] 跳过空行"); continue
            final_text = f"{prompt_text}：{text}" if prompt_text else text
            self._tts_log_msg(f"[{i}/{len(lines)}] 生成中: {text[:30]}...")
            params = {"character_id": char_id, "text": final_text, "emotion": emotion or "平静",
                      "top_k": 5, "top_p": 0.9, "temperature": 0.75, "text_split_method": "cut5"}
            if has_ref: params["ref_audio_path"] = ref_audio_path
            try:
                resp = requests.post(synth_url, json=params, timeout=120)
                if resp.status_code == 200 and resp.content:
                    name_tag = os.path.splitext(os.path.basename(ref_audio_path))[0] if (has_ref and ref_audio_path) else character
                    fname = self._tts_audio_name(i, name_tag, text)
                    out_path = os.path.join(out_dir, fname)
                    with open(out_path, "wb") as f: f.write(resp.content)
                    self._tts_log_msg(f"[{i}/{len(lines)}] 已保存: {fname}"); success += 1
                else:
                    try: err = resp.json().get("detail", resp.text[:200])
                    except Exception: err = resp.text[:200]
                    self._tts_log_msg(f"[{i}/{len(lines)}] HTTP {resp.status_code}: {err}"); fail += 1
            except requests.exceptions.ConnectionError:
                self._tts_log_msg(f"[{i}/{len(lines)}] 连接中断，重新拉起...")
                bat_path = self.sovits_bat_var.get().strip()
                if bat_path and os.path.exists(bat_path):
                    subprocess.Popen(["cmd", "/c", bat_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
                    _time.sleep(10)
                    if self._check_sovits_status(api_url):
                        try:
                            resp2 = requests.post(synth_url, json=params, timeout=120)
                            if resp2.status_code == 200 and resp2.content:
                                name_tag = os.path.splitext(os.path.basename(ref_audio_path))[0] if (has_ref and ref_audio_path) else character
                                fname = self._tts_audio_name(i, name_tag, text)
                                out_path = os.path.join(out_dir, fname)
                                with open(out_path, "wb") as f: f.write(resp2.content)
                                self._tts_log_msg(f"[{i}/{len(lines)}] 重试成功"); success += 1; continue
                        except Exception: pass
                self._tts_log_msg(f"[{i}/{len(lines)}] 重试失败"); fail += 1
            except Exception as e:
                self._tts_log_msg(f"[{i}/{len(lines)}] 失败: {e}"); fail += 1
            _time.sleep(0.3)
        self._tts_log_msg("=" * 40)
        self._tts_log_msg(f"完成: 成功 {success}，失败 {fail}")
        self.safe_after(lambda: self.tts_gen_btn.configure(state="normal", text="一键批量生成音频"))
        if success > 0:
            messagebox.showinfo("完成", f"音频生成完成！\n成功: {success}\n保存至: {out_dir}")

    def _tts_generate_mimo(self, lines):
        api_key = self.config.get("mimo_api_key", "").strip()
        if not api_key: api_key = self.config.get("api_key", "").strip()
        if not api_key:
            self._tts_log_msg("错误: 请先在「全局设置」或「MiMo TTS 配置」中配置 API Key！")
            self.safe_after(lambda: self.tts_gen_btn.configure(state="normal", text="一键批量生成音频"))
            return
        mimo_model_display = self.mimo_model_var.get().strip()
        model = mimo_model_display.split(" (")[0] if " (" in mimo_model_display else mimo_model_display
        model = model.lower()
        base_url = self.config.get("api_base_url", "").strip()
        if "/anthropic" in base_url: base_url = base_url.replace("/anthropic", "/v1")
        elif not base_url.endswith("/v1"): base_url = base_url.rstrip("/") + "/v1"
        out_dir = self._get_tts_audio_dir()
        os.makedirs(out_dir, exist_ok=True)
        adv_mode = self.tts_adv_mode_var.get()
        prompt_text = ""; ref_audio_path = ""
        if adv_mode == "clone":
            ref_audio_path = self.tts_ref_audio_var.get().strip()
            if ref_audio_path and os.path.isfile(ref_audio_path):
                self._tts_log_msg(f"[声音复刻] 参考音频: {os.path.basename(ref_audio_path)}")
            else:
                self._tts_log_msg("[声音复刻] 未选择参考音频或文件不存在，使用标准模式"); ref_audio_path = ""
        else:
            prompt_text = self.tts_prompt_text_var.get().strip()
            if prompt_text: self._tts_log_msg(f"[情感指令] {prompt_text}")

        self._tts_log_msg(f"MiMo 模型: {model} | 模式: {'声音复刻' if ref_audio_path else '标准模式+情感指令'}")
        if ref_audio_path and "voiceclone" not in model and "voicedesign" not in model:
            self._tts_log_msg(f"[警告] 声音复刻需要选择 VoiceClone 或 VoiceDesign 模型！")
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
            if not text: self._tts_log_msg(f"[{i}/{len(lines)}] 跳过空行"); continue
            self._tts_log_msg(f"[{i}/{len(lines)}] 生成中: {text[:30]}...")
            try:
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json; charset=utf-8"}
                voice_display = self.mimo_voice_var.get().strip()
                voice_id = self.mimo_voice_id_map.get(voice_display, "bingtang")
                messages = []
                if "voicedesign" in model:
                    voice_desc_map = {"bingtang": "冰糖的清甜女声", "mohuali": "茉莉的温柔女声",
                        "sudahuoli": "苏打的活力女声", "baihuashenzhu": "白桦的沉稳女声",
                        "mia": "Mia的英文女声", "chloe": "Chloe的英文女声",
                        "milo": "Milo的英文男声", "dean": "Dean的英文男声", "mimo_default": "默认音色"}
                    user_content = f"使用{voice_desc_map.get(voice_id, voice_id)}读这段话："
                    if prompt_text: user_content += f"\n\n语气：{prompt_text}\n\n"
                    else: user_content += "\n\n"
                    user_content += text
                    messages.append({"role": "user", "content": user_content})
                else:
                    if prompt_text: messages.append({"role": "system", "content": f"请使用以下语气/情感进行配音：{prompt_text}"})
                    messages.append({"role": "user", "content": text})
                payload = {"model": model, "messages": messages, "response_format": "audio", "stream": False}
                if ref_audio_path and os.path.isfile(ref_audio_path):
                    if "voiceclone" in model:
                        with open(ref_audio_path, "rb") as f: ref_audio_b64 = base64.b64encode(f.read()).decode()
                        mime = mimetypes.guess_type(ref_audio_path)[0] or "audio/wav"
                        payload["audio"] = {"voice": f"data:{mime};base64,{ref_audio_b64}"}
                    else:
                        if "voicedesign" not in model: payload["audio"] = {"voice": voice_id}
                else:
                    if "voicedesign" not in model: payload["audio"] = {"voice": voice_id}

                resp = requests.post(f"{base_url}/chat/completions", headers=headers,
                    data=json.dumps(payload, ensure_ascii=False).encode('utf-8'), timeout=180)
                if resp.status_code == 200:
                    name_tag = os.path.splitext(os.path.basename(ref_audio_path))[0] if (ref_audio_path and os.path.isfile(ref_audio_path)) else voice_id
                    fname = self._tts_audio_name(i, name_tag, text)
                    out_path = os.path.join(out_dir, fname)
                    result = resp.json()
                    audio_b64 = (result.get("choices", [{}])[0].get("message", {}).get("audio", {}).get("data", ""))
                    if audio_b64:
                        audio_bytes = base64.b64decode(audio_b64)
                        with open(out_path, "wb") as f: f.write(audio_bytes)
                        self._tts_log_msg(f"[{i}/{len(lines)}] 已保存: {fname} ({len(audio_bytes)} bytes)"); success += 1
                    else:
                        self._tts_log_msg(f"[{i}/{len(lines)}] 响应中无音频数据"); fail += 1
                else:
                    try: err = resp.json().get("error", {}).get("message", resp.text[:300])
                    except Exception: err = resp.text[:300]
                    self._tts_log_msg(f"[{i}/{len(lines)}] HTTP {resp.status_code}: {err}"); fail += 1
            except requests.exceptions.Timeout:
                self._tts_log_msg(f"[{i}/{len(lines)}] 超时"); fail += 1
            except requests.exceptions.ConnectionError as e:
                self._tts_log_msg(f"[{i}/{len(lines)}] 连接错误: {e}"); fail += 1
            except Exception as e:
                self._tts_log_msg(f"[{i}/{len(lines)}] 失败: {type(e).__name__}: {e}"); fail += 1
            _time.sleep(0.3)
        self._tts_log_msg("=" * 40)
        self._tts_log_msg(f"完成: 成功 {success}，失败 {fail}")
        self.safe_after(lambda: self.tts_gen_btn.configure(state="normal", text="一键批量生成音频"))
        if success > 0:
            messagebox.showinfo("完成", f"音频生成完成！\n成功: {success}\n保存至: {out_dir}")
