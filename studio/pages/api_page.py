"""API settings page mixin — 类似中转站风格"""

import customtkinter as ctk
import tkinter as tk

from ..constants import C, FONT_TITLE, FONT_H2, FONT_H2, FONT_BODY, FONT_MONO, FONT_SMALL, PAD_MD, PAD_LG, CORNER_RADIUS, DEFAULT_CONFIG
from ..ui import SectionCard
from ..config import save_config


# API 格式选项
API_FORMATS = [
    "Anthropic Messages (原生)",
    "OpenAI Compatible (兼容)",
]

# 认证字段选项
AUTH_FIELDS = [
    "ANTHROPIC_AUTH_TOKEN (默认)",
    "OPENAI_AUTH_TOKEN",
    "自定义 Header",
]


class ApiMixin:

    def _build_page_api(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color=C["bg"])
        scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(scroll, text="API 与全局设置", font=FONT_TITLE,
                     text_color=C["accent"]).pack(anchor="w", padx=20, pady=(16, 16))

        # 供应商名称
        card = SectionCard(scroll, title="供应商名称")
        card.pack(fill="x", padx=20, pady=(0, 12))
        self.api_provider_var = tk.StringVar(value=self.config.get("api_provider", "Xiaomi MiMo"))
        ctk.CTkEntry(card, textvariable=self.api_provider_var, font=FONT_BODY,
                      fg_color=C["surface2"], border_color=C["border"],
                      corner_radius=8, placeholder_text="例如：Xiaomi MiMo").pack(fill="x", padx=16, pady=(4, 4))
        ctk.CTkLabel(card, text="用于识别不同的 API 供应商",
                     font=FONT_SMALL, text_color=C["text3"]).pack(anchor="w", padx=16, pady=(0, 10))

        # 官网链接
        card = SectionCard(scroll, title="官网链接")
        card.pack(fill="x", padx=20, pady=(0, 12))
        self.api_website_var = tk.StringVar(value=self.config.get("api_website", "https://platform.xiaomimimo.com"))
        ctk.CTkEntry(card, textvariable=self.api_website_var, font=FONT_MONO,
                      fg_color=C["surface2"], border_color=C["border"],
                      corner_radius=8, placeholder_text="https://example.com").pack(fill="x", padx=16, pady=(4, 4))
        ctk.CTkLabel(card, text="供应商官网地址（可选）",
                     font=FONT_SMALL, text_color=C["text3"]).pack(anchor="w", padx=16, pady=(0, 10))

        # API Key
        card = SectionCard(scroll, title="API Key")
        card.pack(fill="x", padx=20, pady=(0, 12))
        key_row = ctk.CTkFrame(card, fg_color="transparent")
        key_row.pack(fill="x", padx=16, pady=(4, 4))
        self.api_key_var = tk.StringVar(value=self.config.get("api_key", DEFAULT_CONFIG["api_key"]))
        self.key_entry = ctk.CTkEntry(key_row, textvariable=self.api_key_var, show="•",
                                       font=FONT_MONO, fg_color=C["surface2"],
                                       border_color=C["border"], corner_radius=8,
                                       placeholder_text="输入 API Key...")
        self.key_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.key_visible = tk.BooleanVar(value=False)
        self.toggle_key_btn = ctk.CTkButton(key_row, text="👁", width=36, font=FONT_BODY,
                                             fg_color=C["surface2"], hover_color=C["border"],
                                             text_color=C["text2"], corner_radius=6, height=32,
                                             command=self.toggle_key_visibility)
        self.toggle_key_btn.pack(side="left")
        ctk.CTkLabel(card, text="密钥将以掩码显示",
                     font=FONT_SMALL, text_color=C["text3"]).pack(anchor="w", padx=16, pady=(0, 10))

        # 请求地址
        card = SectionCard(scroll, title="请求地址")
        card.pack(fill="x", padx=20, pady=(0, 12))
        
        # 完整 URL 开关行
        url_header = ctk.CTkFrame(card, fg_color="transparent")
        url_header.pack(fill="x", padx=16, pady=(4, 4))
        ctk.CTkLabel(url_header, text="请求地址", font=FONT_BODY, text_color=C["text"]).pack(side="left")
        self.api_full_url_var = tk.BooleanVar(value=self.config.get("api_full_url", False))
        ctk.CTkSwitch(url_header, text="完整 URL", variable=self.api_full_url_var,
                       font=FONT_SMALL, fg_color=C["border"], progress_color=C["accent"],
                       button_color=C["text"], button_hover_color=C["accent2"],
                       text_color=C["text2"], command=self._on_full_url_toggle).pack(side="left", padx=12)

        self.api_url_var = tk.StringVar(value=self.config.get("api_base_url", DEFAULT_CONFIG["api_base_url"]))
        self.url_entry = ctk.CTkEntry(card, textvariable=self.api_url_var, font=FONT_MONO,
                                       fg_color=C["surface2"], border_color=C["border"],
                                       corner_radius=8)
        self.url_entry.pack(fill="x", padx=16, pady=(0, 4))
        
        # 提示标签
        self.url_hint_label = ctk.CTkLabel(card, text="填写兼容 Claude API 的服务端点地址，不要以斜杠结尾",
                                            font=FONT_SMALL, text_color=C["warn"])
        self.url_hint_label.pack(anchor="w", padx=16, pady=(0, 10))
        
        self._on_full_url_toggle()

        # 模型名称
        card = SectionCard(scroll, title="模型名称")
        card.pack(fill="x", padx=20, pady=(0, 12))
        
        model_row = ctk.CTkFrame(card, fg_color="transparent")
        model_row.pack(fill="x", padx=16, pady=(4, 4))
        
        self.api_model_var = tk.StringVar(value=self.config.get("api_model", DEFAULT_CONFIG["api_model"]))
        self.api_model_combo = ctk.CTkComboBox(model_row, variable=self.api_model_var,
                                                 values=[DEFAULT_CONFIG["api_model"]],
                                                 font=FONT_MONO, fg_color=C["surface2"],
                                                 border_color=C["border"],
                                                 button_color=C["border"], button_hover_color=C["text3"],
                                                 corner_radius=8)
        self.api_model_combo.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        self._refresh_models_btn = ctk.CTkButton(model_row, text="🔄 刷新", font=FONT_SMALL, width=80,
                                                   fg_color=C["accent"], text_color=C["bg"],
                                                   hover_color=C["accent2"], corner_radius=6, height=32,
                                                   command=self._refresh_models)
        self._refresh_models_btn.pack(side="left")
        
        self._model_status_label = ctk.CTkLabel(card, text="点击「刷新」获取可用模型列表",
                                                  font=FONT_SMALL, text_color=C["text3"])
        self._model_status_label.pack(anchor="w", padx=16, pady=(0, 10))

        # 高级选项（可折叠）
        self._adv_expanded = tk.BooleanVar(value=self.config.get("api_adv_expanded", False))
        adv_header = ctk.CTkFrame(scroll, fg_color=C["surface"], corner_radius=CORNER_RADIUS,
                                   border_width=1, border_color=C["border"], cursor="hand2")
        adv_header.pack(fill="x", padx=20, pady=(0, 8))
        
        adv_toggle_row = ctk.CTkFrame(adv_header, fg_color="transparent", cursor="hand2")
        adv_toggle_row.pack(fill="x", padx=16, pady=(8, 8))
        
        self._adv_arrow = ctk.CTkLabel(adv_toggle_row, text="▶" if not self._adv_expanded.get() else "▼",
                                        font=FONT_BODY, text_color=C["accent"], width=20, cursor="hand2")
        self._adv_arrow.pack(side="left")
        ctk.CTkLabel(adv_toggle_row, text="高级选项", font=FONT_H2, text_color=C["text"],
                     cursor="hand2").pack(side="left", padx=4)
        
        # 整行可点击
        for widget in [adv_header, adv_toggle_row, self._adv_arrow]:
            widget.bind("<Button-1>", lambda e: self._toggle_advanced())

        self._adv_frame = ctk.CTkFrame(adv_header, fg_color="transparent")

        # API 格式
        ctk.CTkLabel(self._adv_frame, text="API 格式", font=FONT_BODY,
                     text_color=C["text"]).pack(anchor="w", padx=16, pady=(8, 2))
        self.api_format_var = tk.StringVar(value=self.config.get("api_format", API_FORMATS[0]))
        ctk.CTkComboBox(self._adv_frame, variable=self.api_format_var, values=API_FORMATS,
                         font=FONT_BODY, fg_color=C["surface2"], border_color=C["border"],
                         button_color=C["border"], button_hover_color=C["text3"],
                         corner_radius=8, command=self._on_format_changed).pack(fill="x", padx=16, pady=(0, 4))
        ctk.CTkLabel(self._adv_frame, text="选择供应商 API 的输入格式",
                     font=FONT_SMALL, text_color=C["text3"]).pack(anchor="w", padx=16, pady=(0, 8))

        # 认证字段
        ctk.CTkLabel(self._adv_frame, text="认证字段", font=FONT_BODY,
                     text_color=C["text"]).pack(anchor="w", padx=16, pady=(4, 2))
        self.api_auth_var = tk.StringVar(value=self.config.get("api_auth_field", AUTH_FIELDS[0]))
        ctk.CTkComboBox(self._adv_frame, variable=self.api_auth_var, values=AUTH_FIELDS,
                         font=FONT_BODY, fg_color=C["surface2"], border_color=C["border"],
                         button_color=C["border"], button_hover_color=C["text3"],
                         corner_radius=8).pack(fill="x", padx=16, pady=(0, 4))
        ctk.CTkLabel(self._adv_frame, text="选择写入配置的认证环境变量名",
                     font=FONT_SMALL, text_color=C["text3"]).pack(anchor="w", padx=16, pady=(0, 12))

        # 自定义 Header（仅当选择"自定义 Header"时显示）
        self._custom_header_frame = ctk.CTkFrame(self._adv_frame, fg_color="transparent")
        ctk.CTkLabel(self._custom_header_frame, text="自定义 Header 名称", font=FONT_BODY,
                     text_color=C["text"]).pack(anchor="w", padx=16, pady=(4, 2))
        self.api_custom_header_var = tk.StringVar(value=self.config.get("api_custom_header", "Authorization"))
        ctk.CTkEntry(self._custom_header_frame, textvariable=self.api_custom_header_var, font=FONT_MONO,
                      fg_color=C["surface2"], border_color=C["border"],
                      corner_radius=8, placeholder_text="Authorization").pack(fill="x", padx=16, pady=(0, 4))
        ctk.CTkLabel(self._custom_header_frame, text="HTTP 请求头名称",
                     font=FONT_SMALL, text_color=C["text3"]).pack(anchor="w", padx=16, pady=(0, 8))
        
        self._custom_header_frame.pack(fill="x") if self.api_auth_var.get() == "自定义 Header" else None

        # 展开/收起高级选项
        if self._adv_expanded.get():
            self._adv_frame.pack(fill="x", padx=0, pady=(0, 8))

        # 保存/恢复按钮
        btn_row = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(12, 4))
        ctk.CTkButton(btn_row, text="保存设置", font=FONT_BODY, fg_color=C["accent"],
                       text_color=C["bg"], hover_color=C["accent2"],
                       corner_radius=10, height=38, width=120,
                       command=self.save_settings).pack(side="left")
        ctk.CTkButton(btn_row, text="恢复默认", font=FONT_BODY, width=100,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text"], corner_radius=10, height=38,
                       command=self.reset_settings).pack(side="left", padx=10)

        self.settings_status = ctk.CTkLabel(scroll, text="", font=FONT_BODY,
                                             text_color=C["green"])
        self.settings_status.pack(anchor="w", padx=20, pady=(8, 16))

    def _on_full_url_toggle(self):
        """切换完整 URL 模式时更新提示"""
        if self.api_full_url_var.get():
            self.url_hint_label.configure(
                text="完整 URL 模式：直接填写完整的 API 端点地址",
                text_color=C["accent"])
        else:
            self.url_hint_label.configure(
                text="填写兼容 Claude API 的服务端点地址，不要以斜杠结尾",
                text_color=C["warn"])

    def _toggle_advanced(self):
        """展开/收起高级选项"""
        if self._adv_frame.winfo_viewable():
            self._adv_frame.pack_forget()
            self._adv_arrow.configure(text="▶")
            self._adv_expanded.set(False)
        else:
            self._adv_frame.pack(fill="x", padx=0, pady=(0, 8))
            self._adv_arrow.configure(text="▼")
            self._adv_expanded.set(True)

    def _on_format_changed(self, choice):
        """API 格式切换时更新认证字段选项"""
        if "Anthropic" in choice:
            auth_options = ["ANTHROPIC_AUTH_TOKEN (默认)", "自定义 Header"]
        else:
            auth_options = ["OPENAI_AUTH_TOKEN", "自定义 Header"]
        # 更新认证字段下拉框的选项
        if hasattr(self, '_auth_combo'):
            self._auth_combo.configure(values=auth_options)
            if self.api_auth_var.get() not in auth_options:
                self.api_auth_var.set(auth_options[0])

    def toggle_key_visibility(self):
        self.key_visible.set(not self.key_visible.get())
        self.key_entry.configure(show="" if self.key_visible.get() else "•")

    def _get_base_url(self):
        """根据配置获取实际的 base_url"""
        url = self.api_url_var.get().strip()
        # 无论是否完整 URL 模式，都需要处理 /anthropic → /v1 转换
        if "/anthropic" in url:
            return url.replace("/anthropic", "/v1")
        elif url.endswith("/anthropic"):
            return url[:-len("/anthropic")] + "/v1"
        # 如果已经是 /v1 格式或完整 URL，直接返回
        return url.rstrip("/")

    def _refresh_models(self):
        """刷新可用模型列表"""
        import threading
        import requests
        
        api_key = self.api_key_var.get().strip()
        raw_url = self.api_url_var.get().strip()
        
        if not api_key:
            self._model_status_label.configure(text="⚠️ 请先填写 API Key", text_color=C["warn"])
            return
        
        if not raw_url:
            self._model_status_label.configure(text="⚠️ 请先填写请求地址", text_color=C["warn"])
            return
        
        # 禁用按钮，显示加载中
        self._refresh_models_btn.configure(state="disabled", text="加载中...")
        self._model_status_label.configure(text="正在获取模型列表...", text_color=C["accent"])
        
        def _worker():
            try:
                # 构建请求头
                if "anthropic" in raw_url.lower():
                    headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
                else:
                    headers = {"Authorization": f"Bearer {api_key}"}
                
                # 尝试多种端点获取模型列表
                base = raw_url.rstrip("/")
                urls_to_try = [
                    f"{base}/v1/models",
                    f"{base.replace('/anthropic', '/v1')}/models",
                    f"{base}/models",
                ]
                
                models = []
                for url in urls_to_try:
                    try:
                        resp = requests.get(url, headers=headers, timeout=10)
                        if resp.status_code == 200:
                            data = resp.json()
                            if "data" in data:
                                models = [m.get("id", "") for m in data.get("data", []) if m.get("id")]
                            elif isinstance(data, list):
                                models = [m.get("id", "") if isinstance(m, dict) else str(m) for m in data]
                            if models:
                                break
                    except Exception:
                        continue
                
                if models:
                    models = sorted(list(set(models)))
                    self.safe_after(lambda: self._update_model_list(models))
                else:
                    # 使用默认模型列表
                    self.safe_after(lambda: self._use_default_models())
                    
            except requests.exceptions.Timeout:
                self.safe_after(lambda: self._model_status_label.configure(
                    text="⚠️ 请求超时", text_color=C["warn"]))
            except requests.exceptions.ConnectionError:
                self.safe_after(lambda: self._model_status_label.configure(
                    text="❌ 无法连接到服务器", text_color=C["red"]))
            except Exception as e:
                self.safe_after(lambda: self._model_status_label.configure(
                    text=f"⚠️ 错误: {str(e)[:50]}", text_color=C["warn"]))
            finally:
                self.safe_after(lambda: self._refresh_models_btn.configure(
                    state="normal", text="🔄 刷新"))
        
        threading.Thread(target=_worker, daemon=True).start()
    
    def _update_model_list(self, models):
        """更新模型下拉框"""
        current = self.api_model_var.get()
        self.api_model_combo.configure(values=models)
        # 如果当前模型在列表中，保持选中
        if current in models:
            self.api_model_combo.set(current)
        elif models:
            self.api_model_var.set(models[0])
            self.api_model_combo.set(models[0])
        self._model_status_label.configure(
            text=f"✅ 找到 {len(models)} 个可用模型", text_color=C["green"])
    
    def _use_default_models(self):
        """使用默认模型列表"""
        default_models = [
            "mimo-v2.5-pro", "mimo-v2.5-turbo", "mimo-v2.5-lite",
            "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022",
            "gpt-4o", "gpt-4o-mini", "gpt-4-turbo",
        ]
        self._update_model_list(default_models)
        self._model_status_label.configure(
            text="✅ 使用默认模型列表（API 不支持 /models 端点）", text_color=C["accent"])

    def save_settings(self):
        self.config["api_provider"] = self.api_provider_var.get().strip()
        self.config["api_website"] = self.api_website_var.get().strip()
        self.config["api_key"] = self.api_key_var.get().strip()
        self.config["api_base_url"] = self.api_url_var.get().strip()
        self.config["api_model"] = self.api_model_var.get().strip()
        self.config["api_full_url"] = self.api_full_url_var.get()
        self.config["api_format"] = self.api_format_var.get()
        self.config["api_auth_field"] = self.api_auth_var.get()
        self.config["api_custom_header"] = self.api_custom_header_var.get().strip()
        self.config["api_adv_expanded"] = self._adv_expanded.get()
        if hasattr(self, "bailian_key_var"):
            self.config["bailian_api_key"] = self.bailian_key_var.get().strip()
            self.config["bailian_mode"] = self.bailian_mode_var.get()
            self.config["bailian_model"] = self.bailian_model_var.get()
            self.config["bailian_ratio"] = self.bailian_ratio_var.get()
            self.config["bailian_video_duration"] = self.video_duration_var.get()
        if hasattr(self, "tts_engine_var"):
            self.config["tts_engine"] = self.tts_engine_var.get()
            voice_display = self.tts_voice_var.get()
            self.config["tts_voice"] = self.tts_voice_map.get(voice_display, "sambert-zhichu-v1")
            self.config["tts_custom_model"] = self.tts_custom_model_var.get().strip()
            self.config["tts_adv_mode"] = self.tts_adv_mode_var.get()
            self.config["tts_ref_audio"] = self.tts_ref_audio_var.get().strip()
            self.config["tts_prompt_text"] = self.tts_prompt_text_var.get().strip()
        if hasattr(self, "sovits_url_var"):
            self.config["sovits_url"] = self.sovits_url_var.get().strip()
            self.config["sovits_bat_path"] = self.sovits_bat_var.get().strip()
            self.config["sovits_character"] = self.sovits_character_var.get().strip()
            self.config["sovits_emotion"] = self.sovits_emotion_var.get().strip()
        if hasattr(self, "mimo_api_key_var"):
            self.config["mimo_api_key"] = self.mimo_api_key_var.get().strip()
        save_config(self.config)
        self.settings_status.configure(text="✅ 设置已保存到 config.json", text_color=C["green"])
        self.root.after(3000, lambda: self.settings_status.configure(text=""))

    def reset_settings(self):
        self.api_provider_var.set("Xiaomi MiMo")
        self.api_website_var.set("https://platform.xiaomimimo.com")
        self.api_url_var.set(DEFAULT_CONFIG["api_base_url"])
        self.api_key_var.set(DEFAULT_CONFIG["api_key"])
        self.api_model_var.set(DEFAULT_CONFIG["api_model"])
        self.api_full_url_var.set(False)
        self.api_format_var.set(API_FORMATS[0])
        self.api_auth_var.set(AUTH_FIELDS[0])
        self.api_custom_header_var.set("Authorization")
        self._on_full_url_toggle()
        self.settings_status.configure(text="已恢复为默认值（尚未保存）", text_color=C["warn"])
        self.root.after(3000, lambda: self.settings_status.configure(text=""))
