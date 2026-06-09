import customtkinter as ctk

C = {
    "bg":           "#080808",      # 最深背景
    "surface":      "#0F0F0F",      # 卡片底色
    "surface2":     "#161616",      # 输入框/次级容器
    "surface3":     "#1A1A1A",      # 悬停态
    "border":       "#252525",      # 微弱边框
    "border_focus": "#3A3A3A",      # 聚焦边框
    "accent":       "#00FF9D",      # 赛博绿（主按钮/激活态）
    "accent_dim":   "#00CC7D",      # 赛博绿暗调
    "accent2":      "#00D4FF",      # 赛博蓝（辅助强调）
    "accent3":      "#FF6B9D",      # 赛博粉（警告/删除）
    "text":         "#F0F0F0",      # 主文字
    "text2":        "#A0A0A0",      # 次要文字
    "text3":        "#606060",      # 占位符/禁用态
    "red":          "#FF4757",
    "green":        "#2ED573",
    "blue":         "#1E90FF",
    "warn":         "#FFA502",
}

FONT_TITLE   = ("Segoe UI Semibold", 22, "bold")
FONT_H2      = ("Segoe UI Semibold", 13)
FONT_BODY    = ("Segoe UI", 11)
FONT_SMALL   = ("Segoe UI", 9)
FONT_MONO    = ("Cascadia Code", 11)
FONT_MONO_SM = ("Cascadia Code", 10)

PAD_XS = 4
PAD_SM = 8
PAD_MD = 12
PAD_LG = 16
PAD_XL = 24
PAD_XXL = 32

BTN_HEIGHT_SM = 28
BTN_HEIGHT_MD = 34
BTN_HEIGHT_LG = 40
INPUT_HEIGHT = 32
CORNER_RADIUS = 8
CORNER_RADIUS_LG = 12

class SectionCard(ctk.CTkFrame):
    def __init__(self, master, title="", **kwargs):
        super().__init__(
            master,
            fg_color=C["surface"],
            corner_radius=CORNER_RADIUS_LG,
            border_width=1,
            border_color=C["border"],
            **kwargs
        )
        if title:
            ctk.CTkLabel(
                self, text=title, font=FONT_H2,
                text_color=C["accent"]
            ).pack(anchor="w", padx=PAD_LG, pady=(PAD_MD, PAD_SM))

class LogBox(ctk.CTkTextbox):
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            font=FONT_MONO_SM,
            fg_color=C["surface2"],
            text_color=C["text2"],
            corner_radius=CORNER_RADIUS,
            border_width=1,
            border_color=C["border"],
            state="disabled",
            **kwargs
        )

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
            "primary": {
                "fg_color": C["accent"],
                "hover_color": C["accent_dim"],
                "text_color": C["bg"],
            },
            "secondary": {
                "fg_color": C["surface2"],
                "hover_color": C["surface3"],
                "text_color": C["text"],
            },
            "danger": {
                "fg_color": C["accent3"],
                "hover_color": "#FF4757",
                "text_color": "#FFFFFF",
            },
        }
        style = styles.get(variant, styles["primary"])
        defaults = {
            "corner_radius": CORNER_RADIUS,
            "height": BTN_HEIGHT_MD,
            "font": FONT_BODY,
        }
        defaults.update(style)
        defaults.update(kwargs)
        super().__init__(master, **defaults)
