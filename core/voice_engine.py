"""AI Content Studio - Voice/TTS Engine Module
智能配音页面：UI + 三种 TTS 引擎逻辑
"""

from core.config_module import (
    ctk, tk, messagebox, filedialog,
    os, time, json, requests, threading, base64, mimetypes,
    time as _time, logging,
    C, FONT_TITLE, FONT_H2, FONT_BODY, FONT_SMALL, FONT_MONO, FONT_MONO_SM,
    PAD_XS, PAD_SM, PAD_MD, PAD_LG, PAD_XL,
    BTN_HEIGHT_SM, BTN_HEIGHT_MD, BTN_HEIGHT_LG, INPUT_HEIGHT,
    CORNER_RADIUS, CORNER_RADIUS_LG,
    SectionCard, LogBox, CyberButton, save_config,
)


class VoiceEngineMixin:
    """智能配音 - UI + 三种TTS引擎(百炼/SoVITS/MiMo)逻辑"""
    pass
