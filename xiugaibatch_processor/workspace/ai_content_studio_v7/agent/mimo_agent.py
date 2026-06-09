import customtkinter as ctk
from core.app_context import AppContext
import threading

class MiMoAgent:
    def __init__(self, master, context: AppContext):
        self.ctx = context
        self.master = master
        self._ui_window = None

    def open_chat(self):
        if self._ui_window is not None and self._ui_window.winfo_exists():
            self._ui_window.lift()
            return

        self._ui_window = ctk.CTkToplevel(self.master)
        self._ui_window.title("🤖 MiMo AI")
        # TODO: Claude 填充悬浮窗UI
    
    def process_command(self, cmd):
        # 耦合处理示例：智能体如何调用其他页面
        if "清空" in cmd:
            self.ctx.visuals_page.batch_clear()
            self.log("已清空视觉批处理列表")
        elif "提取" in cmd:
            self.ctx.visuals_page.extract_from_script()
            
    def log(self, msg):
        pass
