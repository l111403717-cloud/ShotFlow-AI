import customtkinter as ctk
import os
import sys

from theme import C, LogBox
from config import load_config
from core.app_context import AppContext

from pages.page_script import ScriptPage
from pages.page_visuals import VisualsPage
from pages.page_vidu import ViduPage

class AIContentStudio:
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
        self.root.title("AI Content Studio v7.0 - Cyber Edition")
        self.root.geometry("1600x960")
        self.root.minsize(1400, 800)
        self.root.configure(fg_color=C["bg"])

        self.config = load_config()
        self._current_page = None
        self._is_shutting_down = False

        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # 全局日志抽屉
        self._build_log_drawer()

        # 上下文注入
        self.ctx = AppContext(
            root=self.root,
            config=self.config,
            global_log=self.global_log,
            safe_after_fn=self.safe_after
        )

        self._build_sidebar()
        self._build_pages()
        self._show_page("Script")

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self.root, width=180, fg_color=C["surface"], corner_radius=0, border_width=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        ctk.CTkLabel(self.sidebar, text="⚡ AI Studio", font=("Segoe UI Semibold", 22, "bold"), text_color=C["accent"]).pack(pady=(32, 24), padx=16, anchor="w")

        self.nav_buttons = {}
        for key, label in self.NAV_ITEMS:
            btn = ctk.CTkButton(
                self.sidebar, text=f"  {label}", fg_color="transparent",
                hover_color=C["surface2"], text_color=C["text"], anchor="w",
                height=42, command=lambda k=key: self._show_page(k)
            )
            btn.pack(fill="x", padx=8, pady=4)
            self.nav_buttons[key] = btn

        self._log_visible = False
        self.log_toggle_btn = ctk.CTkButton(self.sidebar, text="📋 终端日志", command=self._toggle_log_drawer)
        self.log_toggle_btn.pack(fill="x", padx=8, pady=(16, 4), side="bottom")

    def _build_log_drawer(self):
        self.log_drawer = ctk.CTkFrame(self.root, fg_color=C["surface"], width=350, corner_radius=0, border_width=0)
        drawer_header = ctk.CTkFrame(self.log_drawer, fg_color=C["surface2"], corner_radius=0)
        drawer_header.pack(fill="x")
        ctk.CTkLabel(drawer_header, text="📋 终端日志", text_color=C["accent"]).pack(side="left", padx=12, pady=8)
        self.global_log = LogBox(self.log_drawer)
        self.global_log.pack(fill="both", expand=True, padx=8, pady=8)

    def _toggle_log_drawer(self):
        if self._log_visible:
            self.log_drawer.pack_forget()
            self._log_visible = False
        else:
            self.log_drawer.pack(side="right", fill="y")
            self._log_visible = True

    def _build_pages(self):
        self.page_frames = {}
        for key, _ in self.NAV_ITEMS:
            self.page_frames[key] = ctk.CTkFrame(self.root, fg_color=C["bg"], corner_radius=0)

        # 实例化页面并将实例注入 Context 中供相互调用
        self.ctx.register_page("Script", ScriptPage(self.page_frames["Script"], self.ctx))
        self.ctx.register_page("Visuals", VisualsPage(self.page_frames["Visuals"], self.ctx))
        self.ctx.register_page("Vidu", ViduPage(self.page_frames["Vidu"], self.ctx))

    def _show_page(self, key):
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.configure(fg_color=C["accent"], text_color=C["bg"])
            else:
                btn.configure(fg_color="transparent", text_color=C["text"])
        for frame in self.page_frames.values():
            frame.pack_forget()
        self.page_frames[key].pack(side="left", fill="both", expand=True)

    def safe_after(self, func):
        if not self._is_shutting_down:
            try:
                self.root.after(0, func)
            except Exception:
                pass

    def _on_closing(self):
        self._is_shutting_down = True
        self.root.quit()

if __name__ == "__main__":
    app = AIContentStudio()
    app.root.mainloop()
