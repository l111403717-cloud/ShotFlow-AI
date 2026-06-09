import os
import json

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "api_base_url": "https://token-plan-cn.xiaomimimo.com/anthropic",
    "api_key": "tp-clgfpo6b15ix395enlisuyd5eifnderql0r4215zyifj3v5t",
    "api_model": "mimo-v2.5-pro",
    "image_width": "1920", "image_height": "1080",
    "dark_mode": True,
    "bailian_api_key": "", "bailian_mode": "图像生成 (Image)",
    "bailian_model": "qwen-image-2.0-pro", "bailian_video_duration": "5",
    "bailian_ratio": "1:1 (正方形)",
    "tts_engine": "bailian", "tts_voice": "sambert-zhichu-v1", "tts_custom_model": "",
    "tts_ref_audio": "", "tts_prompt_text": "", "tts_adv_mode": "preset",
    "sovits_url": "http://127.0.0.1:8080",
    "sovits_bat_path": r"D:\剪映\声音克隆\一键启动.bat",
    "sovits_character": "", "sovits_emotion": "平静",
    "mimo_api_key": "", "mimo_model": "MiMo-V2.5-TTS", "mimo_voice": "mimo-female-01",
    "vidu_api_key": "", "vidu_model": "viduq3-pro",
    "vidu_duration": "5", "vidu_resolution": "720p",
    "vidu_style": "general", "vidu_aspect_ratio": "16:9",
    "vidu_seed": "0", "vidu_bgm": False, "vidu_audio": True,
    "vidu_off_peak": False, "vidu_watermark": False,
    "vidu_movement_amplitude": "auto",
    "project_name": "",
    "save_path": "",
}

VISUAL_SUFFIX = "cinematic lighting, breathtaking depth of field, hyper-realistic textures, 8k resolution, Unreal Engine 5 style render, high-contrast"

SYSTEM_PROMPT = """你是一位专业的悬疑与科幻影视导演兼分镜师。
用户会给你一个故事创意或剧情大纲，你需要：
1. 根据剧情节奏，动态决定需要的镜头数量（不需要固定数量，可以是3~15个镜头，按剧情自然拆分）。
2. 每个镜头必须包含以下字段：
   - 镜头编号 (Shot Number)
   - 景别 (Shot Type): 如大远景、远景、全景、中景、近景、特写、大特写
   - 时长 (Duration): 如 3s, 5s
   - 画面描述 (Visual Description): 详细的中文画面描述
   - 英文Prompt: 可直接用于AI图像/视频生成的英文 Prompt
   - 运镜方式 (Camera Movement): 如推、拉、摇、移、跟、升、降、固定
   - 配乐/音效建议 (Audio Suggestion): 简短的配乐或音效描述
3. 输出格式使用清晰的结构化文本，每个镜头之间用分隔线隔开。
4. Prompt 必须是英文，适合AI图像或视频生成模型使用。
请用中文输出整体结构，英文 Prompt 部分用英文。"""

class PipelineType:
    TEXT_TO_VIDEO = "t2v"
    IMAGE_TO_VIDEO = "i2v"
    REF_TO_VIDEO = "r2v"
    VIDEO_EDIT = "edit"
    TEXT_TO_IMAGE = "text2img"
    IMAGE_GEN = "img"

def get_pipeline_type(model: str) -> str:
    model_lower = model.lower()
    if model_lower.endswith("-t2v") or "-t2v-" in model_lower:
        return PipelineType.TEXT_TO_VIDEO
    elif model_lower.endswith("-i2v") or "-i2v-" in model_lower:
        return PipelineType.IMAGE_TO_VIDEO
    elif model_lower.endswith("-r2v") or "-r2v-" in model_lower:
        return PipelineType.REF_TO_VIDEO
    elif "videoedit" in model_lower or "video-edit" in model_lower:
        return PipelineType.VIDEO_EDIT
    else:
        return PipelineType.IMAGE_GEN

BAILIAN_MODEL_MAP = {
    "图像生成 (Image)": [
        "qwen-image-2.0-pro",
        "qwen-image-2.0-pro-2026-04-22",
        "qwen-image-2.0-pro-2026-03-03",
        "wan2.7-image-pro",
        "qwen-image-2.0",
        "qwen-image-2.0-2026-03-03",
        "wan2.7-image",
    ],
    "视频生成 (Video)": [
        "wan2.7-t2v", "wan2.7-t2v-2026-04-25",
        "wan2.7-i2v", "wan2.7-i2v-2026-04-25",
        "wan2.7-r2v",
        "happyhorse-1.0-t2v", "happyhorse-1.0-i2v", "happyhorse-1.0-r2v",
        "wan2.7-videoedit", "happyhorse-1.0-video-edit",
    ],
}

def _model_hint(model: str) -> str:
    p = get_pipeline_type(model)
    hints = {
        PipelineType.TEXT_TO_VIDEO:   "✅ 无需参考图",
        PipelineType.IMAGE_TO_VIDEO:  "📎 需要参考图",
        PipelineType.REF_TO_VIDEO:    "📎 需要参考视频",
        PipelineType.VIDEO_EDIT:      "📎 需要素材",
        PipelineType.IMAGE_GEN:       "✏️ 文生图",
    }
    return f"{model}  ({hints.get(p, '')})"

def _extract_model_id(display_name: str) -> str:
    return display_name.split("  (")[0].strip()

MODEL_PIPELINE_CACHE = {}
for _models in BAILIAN_MODEL_MAP.values():
    for _m in _models:
        MODEL_PIPELINE_CACHE[_m] = get_pipeline_type(_m)

VIDEO_MODELS = BAILIAN_MODEL_MAP["视频生成 (Video)"]
EDIT_MODELS  = [m for m in VIDEO_MODELS if "videoedit" in m or "video-edit" in m]
I2V_MODELS   = [m for m in VIDEO_MODELS if "-i2v" in m]
R2V_MODELS   = [m for m in VIDEO_MODELS if "-r2v" in m]
IMAGE_MODELS = BAILIAN_MODEL_MAP["图像生成 (Image)"]

BAILIAN_BASE_URL = "https://dashscope.aliyuncs.com/api/v1"

VIDU_BASE_URL = "https://api.vidu.cn"
VIDU_MODELS = ["viduq3-pro", "viduq3-turbo", "viduq2", "viduq1"]
VIDU_STYLES = ["general", "anime"]
VIDU_RESOLUTIONS = ["540p", "720p", "1080p"]
VIDU_ASPECT_RATIOS = ["16:9", "9:16", "1:1", "3:4", "4:3"]
VIDU_MOVEMENT_AMPLITUDES = ["auto", "small", "medium", "large"]

VIDU_CREDIT_RATES = {"1080p": 24, "720p": 20, "540p": 9}
VIDU_MODEL_DURATION = {
    "viduq3-pro":   (1, 16),
    "viduq3-turbo": (1, 16),
    "viduq2":       (1, 10),
    "viduq1":       (5, 5),
}

def load_config():
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            merged = {**DEFAULT_CONFIG, **cfg}
            return merged
    except Exception as e:
        print(f"[警告] config.json 读取失败，使用默认配置: {e}")
    return dict(DEFAULT_CONFIG)

def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[警告] config.json 保存失败: {e}")
