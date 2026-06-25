"""配置管理"""

import os
import json
from .constants import DEFAULT_CONFIG

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")


def load_config():
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            return {**DEFAULT_CONFIG, **cfg}
    except (json.JSONDecodeError, PermissionError, OSError) as e:
        print(f"[警告] config.json 读取失败，使用默认配置: {e}")
    return dict(DEFAULT_CONFIG)


def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except (PermissionError, OSError) as e:
        print(f"[警告] config.json 保存失败: {e}")
