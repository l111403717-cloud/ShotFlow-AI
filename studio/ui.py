"""公共 UI 组件"""

import customtkinter as ctk
from .constants import C, FONT_H2, FONT_BODY, FONT_MONO_SM, CORNER_RADIUS, CORNER_RADIUS_LG, PAD_MD, PAD_SM, PAD_LG, BTN_HEIGHT_SM, BTN_HEIGHT_MD


class SectionCard(ctk.CTkFrame):
    def __init__(self, master, title="", **kwargs):
        super().__init__(master, fg_color=C["surface"], corner_radius=CORNER_RADIUS_LG,
                         border_width=1, border_color=C["border"], **kwargs)
        if title:
            ctk.CTkLabel(self, text=title, font=FONT_H2, text_color=C["accent"]
            ).pack(anchor="w", padx=PAD_LG, pady=(PAD_MD, PAD_SM))


class LogBox(ctk.CTkTextbox):
    def __init__(self, master, **kwargs):
        super().__init__(master, font=FONT_MONO_SM, fg_color=C["surface2"],
                         text_color=C["text2"], corner_radius=CORNER_RADIUS,
                         border_width=1, border_color=C["border"], state="disabled", **kwargs)

    def append(self, msg):
        self.configure(state="normal")
        self.insert("end", msg + "\n")
        self.see("end")
        self.configure(state="disabled")

    def clear_all(self):
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.configure(state="disabled")


class CyberButton(ctk.CTkButton):
    def __init__(self, master, variant="primary", **kwargs):
        styles = {
            "primary":   {"fg_color": C["accent"], "hover_color": C["accent_dim"], "text_color": C["bg"]},
            "secondary": {"fg_color": C["surface2"], "hover_color": C["surface3"], "text_color": C["text"]},
            "danger":    {"fg_color": C["accent3"], "hover_color": "#FF4757", "text_color": "#FFFFFF"},
        }
        defaults = {"corner_radius": CORNER_RADIUS, "height": BTN_HEIGHT_MD, "font": FONT_BODY}
        defaults.update(styles.get(variant, styles["primary"]))
        defaults.update(kwargs)
        super().__init__(master, **defaults)
