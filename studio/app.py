"""AI Content Studio v7.0 — 主应用类"""

import customtkinter as ctk
import tkinter as tk
import os
import sys
import time
import json
import logging
import traceback
import threading

from .config import load_config, save_config
from .constants import C, FONT_TITLE, FONT_H2, FONT_BODY, FONT_SMALL, PAD_MD, PAD_SM, PAD_LG, PAD_XXL, CORNER_RADIUS, LOG_PATH
from .pages import (ScriptMixin, VisualsMixin, ViduMixin, VoiceMixin, ApiMixin, AssemblyMixin)

logging.basicConfig(filename=LOG_PATH, level=logging.ERROR,
                    format="%(asctime)s [%(levelname)s] %(message)s", encoding="utf-8")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

NAV_ITEMS = [
    ("Script", "剧本生成"),
    ("Visuals", "视觉引擎"),
    ("Vidu", "🎬 Vidu 视频"),
    ("Voice", "智能配音"),
    ("API", "全局设置"),
    ("Assembly", "一键总装"),
]


class BatchProcessor(ScriptMixin, VisualsMixin, ViduMixin, VoiceMixin, ApiMixin, AssemblyMixin):

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
        self._is_shutting_down = False

        self._mimo_history_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mimo_chat_history.json")
        self._mimo_messages = []
        self._mimo_session_id = time.strftime("%Y%m%d_%H%M%S")

        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        self._build_sidebar()
        self._build_pages()
        self._build_floating_mimo_button()
        self._show_page("Script")

    def _on_closing(self):
        self._is_shutting_down = True
        try: self.root.quit()
        except Exception: pass
        try: self.root.destroy()
        except Exception: pass

    def safe_after(self, func):
        if self._is_shutting_down: return
        try: self.root.after(0, func)
        except (tk.TclError, RuntimeError): pass

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self.root, width=180, fg_color=C["surface"], corner_radius=0, border_width=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        ctk.CTkLabel(self.sidebar, text="⚡ AI Studio", font=FONT_TITLE, text_color=C["accent"]
        ).pack(pady=(PAD_XXL, PAD_LG), padx=PAD_LG, anchor="w")

        self.nav_buttons = {}
        for key, label in NAV_ITEMS:
            btn = ctk.CTkButton(self.sidebar, text=f"  {label}", font=FONT_BODY,
                fg_color="transparent", hover_color=C["surface2"], text_color=C["text"],
                anchor="w", height=42, corner_radius=CORNER_RADIUS,
                command=lambda k=key: self._show_page(k))
            btn.pack(fill="x", padx=PAD_SM, pady=4)
            self.nav_buttons[key] = btn

        self._log_visible = False
        self.log_toggle_btn = ctk.CTkButton(self.sidebar, text="📋 终端日志", font=FONT_SMALL,
            fg_color=C["surface2"], hover_color=C["surface3"], text_color=C["text2"],
            anchor="w", height=36, corner_radius=CORNER_RADIUS, command=self._toggle_log_drawer)
        self.log_toggle_btn.pack(fill="x", padx=PAD_SM, pady=(PAD_LG, PAD_SM), side="bottom")

        ctk.CTkLabel(self.sidebar, text="v7.0 · Cyber Edition", font=FONT_SMALL, text_color=C["text3"]
        ).pack(side="bottom", pady=PAD_SM, padx=PAD_LG, anchor="w")

    def _show_page(self, key):
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.configure(fg_color=C["accent"], text_color=C["bg"], hover_color=C["accent_dim"])
            else:
                btn.configure(fg_color="transparent", text_color=C["text"], hover_color=C["surface2"])
        for frame in self.page_frames.values(): frame.pack_forget()
        self.page_frames[key].pack(side="right", fill="both", expand=True)
        self._current_page = key

    def _build_pages(self):
        self.page_frames = {}
        for key, _ in NAV_ITEMS:
            frame = ctk.CTkFrame(self.root, fg_color=C["bg"], corner_radius=0)
            self.page_frames[key] = frame
        self._build_log_drawer()
        self._build_page_script(self.page_frames["Script"])
        self._build_page_visuals(self.page_frames["Visuals"])
        self._build_page_vidu(self.page_frames["Vidu"])
        self._build_page_voice(self.page_frames["Voice"])
        self._build_page_api(self.page_frames["API"])
        self._build_page_assembly(self.page_frames["Assembly"])

    def _build_floating_mimo_button(self):
        self._mimo_fab = ctk.CTkButton(self.root, text="🤖", font=("Segoe UI Emoji", 22),
            width=52, height=52, corner_radius=26, fg_color=C["accent"],
            hover_color=C["accent_dim"], text_color=C["bg"],
            command=self._open_mimo_floating_chat)
        self._mimo_fab.place(relx=1.0, rely=1.0, x=-24, y=-24, anchor="se")
        self.root.bind("<Configure>", self._reposition_mimo_fab)

    def _reposition_mimo_fab(self, event=None):
        if hasattr(self, "_mimo_fab") and self._mimo_fab.winfo_exists():
            self._mimo_fab.place(relx=1.0, rely=1.0, x=-24, y=-24, anchor="se")

    def _open_mimo_floating_chat(self):
        if hasattr(self, "_mimo_chat_win") and self._mimo_chat_win is not None and self._mimo_chat_win.winfo_exists():
            self._mimo_chat_win.lift(); self._mimo_chat_win.focus_force(); return
        win = ctk.CTkToplevel(self.root)
        win.title("🤖 MiMo AI 智能体"); win.geometry("480x600")
        win.configure(fg_color=C["bg"]); win.attributes("-topmost", True)
        self._mimo_chat_win = win

        header = ctk.CTkFrame(win, fg_color=C["surface"], corner_radius=0)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="🤖 MiMo AI 智能体", font=FONT_H2, text_color=C["accent"]).pack(side="left", padx=PAD_MD, pady=4)
        ctk.CTkButton(header, text="✕", font=FONT_BODY, width=30, fg_color="transparent",
                       hover_color=C["accent3"], text_color=C["text2"], corner_radius=4,
                       command=win.destroy).pack(side="right", padx=PAD_SM)

        ctk.CTkLabel(win, text="💡 命令: 提取script提示词 / 第3条改成xxx / 全部优化 / 开始生成",
                     font=FONT_SMALL, text_color=C["text3"], wraplength=440).pack(anchor="w", padx=PAD_MD, pady=(4, 2))

        chat_frame = ctk.CTkFrame(win, fg_color=C["surface2"], corner_radius=8, border_width=1, border_color=C["border"])
        chat_frame.pack(fill="both", expand=True, padx=PAD_MD, pady=(0, PAD_SM))
        self.agent_chat_history = ctk.CTkTextbox(chat_frame, font=FONT_BODY, fg_color="transparent",
            text_color=C["text"], corner_radius=0)
        self.agent_chat_history.pack(fill="both", expand=True, padx=4, pady=4)
        self.agent_chat_history.configure(state="disabled")

        input_row = ctk.CTkFrame(win, fg_color="transparent")
        input_row.pack(fill="x", padx=PAD_MD, pady=(0, PAD_MD))
        self.agent_input = ctk.CTkEntry(input_row, font=FONT_BODY, fg_color=C["surface2"],
            border_color=C["border"], corner_radius=8, placeholder_text="输入命令给 MiMo...")
        self.agent_input.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(input_row, text="发送", font=FONT_BODY, width=60, fg_color=C["accent"],
                       text_color=C["bg"], hover_color=C["accent2"], corner_radius=8,
                       command=self._agent_send_command).pack(side="left")
        self.agent_input.bind("<Return>", lambda e: self._agent_send_command())

        def _on_close(): self._mimo_chat_win = None; win.destroy()
        win.protocol("WM_DELETE_WINDOW", _on_close)

    def _build_log_drawer(self):
        from .ui import LogBox
        self.log_drawer = ctk.CTkFrame(self.root, fg_color=C["surface"], width=350, corner_radius=0, border_width=0)
        drawer_header = ctk.CTkFrame(self.log_drawer, fg_color=C["surface2"], corner_radius=0)
        drawer_header.pack(fill="x")
        ctk.CTkLabel(drawer_header, text="📋 终端日志", font=FONT_H2, text_color=C["accent"]).pack(side="left", padx=PAD_MD, pady=4)
        ctk.CTkButton(drawer_header, text="✕", font=FONT_BODY, width=30, fg_color="transparent",
                       hover_color=C["accent3"], text_color=C["text2"], corner_radius=4,
                       command=self._toggle_log_drawer).pack(side="right", padx=PAD_SM)
        self.global_log = LogBox(self.log_drawer)
        self.global_log.pack(fill="both", expand=True, padx=PAD_SM, pady=PAD_SM)
        ctk.CTkButton(self.log_drawer, text="清空日志", font=FONT_SMALL, fg_color=C["surface2"],
                       hover_color=C["accent3"], text_color=C["text2"], corner_radius=CORNER_RADIUS,
                       height=28, command=self.global_log.clear_all).pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))

    def _toggle_log_drawer(self):
        if self._log_visible:
            self.log_drawer.pack_forget(); self._log_visible = False
            self.log_toggle_btn.configure(fg_color=C["surface2"], text_color=C["text2"])
        else:
            self.log_drawer.pack(side="right", fill="y",
                before=self.page_frames.get(self._current_page, self.page_frames["Script"]))
            self._log_visible = True
            self.log_toggle_btn.configure(fg_color=C["accent"], text_color=C["bg"])


def main():
    def _global_excepthook(exc_type, exc_value, exc_tb):
        msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logging.error("未捕获异常:\n%s", msg)
        print(f"\n[致命错误] 已写入 crash.log:\n{msg}", file=sys.stderr)
    sys.excepthook = _global_excepthook

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
