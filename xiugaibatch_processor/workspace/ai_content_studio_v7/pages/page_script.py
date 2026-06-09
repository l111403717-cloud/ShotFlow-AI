import threading
import json
import requests
from tkinter import filedialog, messagebox
import customtkinter as ctk

from theme import C, FONT_TITLE, FONT_H2, FONT_BODY, FONT_SMALL, FONT_MONO, SectionCard
from config import SYSTEM_PROMPT, VISUAL_SUFFIX

class ScriptPage:
    def __init__(self, parent, context):
        self.ctx = context
        self.frame = ctk.CTkScrollableFrame(parent, fg_color=C["bg"])
        self._build_ui()

    def _build_ui(self):
        ctk.CTkLabel(self.frame, text="动态剧本与分镜生成", font=FONT_TITLE,
                     text_color=C["text"]).pack(anchor="w", padx=20, pady=(16, 8))

        card = SectionCard(self.frame, title="故事创意 / 剧情大纲")
        card.pack(fill="x", padx=20, pady=(0, 12))

        self.story_input = ctk.CTkTextbox(card, height=100, font=FONT_BODY,
                                           fg_color=C["surface2"], text_color=C["text"],
                                           corner_radius=8, border_width=1,
                                           border_color=C["border"])
        self.story_input.pack(fill="x", padx=16, pady=(4, 12))
        self.story_input.insert("end", "例：一个废弃的太空站里，唯一的幸存者发现AI已经开始自己做梦...")

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 12))
        self.generate_btn = ctk.CTkButton(btn_row, text="生成动态镜头脚本",
                                           font=FONT_BODY, fg_color=C["accent"],
                                           text_color=C["bg"], hover_color=C["accent2"],
                                           corner_radius=10, height=38,
                                           command=self.start_generate_script)
        self.generate_btn.pack(side="left")
        ctk.CTkButton(btn_row, text="清空", font=FONT_BODY, width=70,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text"], corner_radius=10, height=38,
                       command=lambda: self.story_input.delete("1.0", "end")
                       ).pack(side="left", padx=8)
        ctk.CTkButton(btn_row, text="导出 TXT", font=FONT_BODY, width=90,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text"], corner_radius=10, height=38,
                       command=self.export_script).pack(side="left")
        ctk.CTkButton(btn_row, text="复制全部", font=FONT_BODY, width=80,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text"], corner_radius=10, height=38,
                       command=self.copy_script).pack(side="left", padx=8)

        card2 = SectionCard(self.frame, title="生成的镜头脚本")
        card2.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.script_output = ctk.CTkTextbox(card2, font=FONT_MONO,
                                             fg_color=C["surface2"], text_color=C["text"],
                                             corner_radius=8, border_width=1,
                                             border_color=C["border"])
        self.script_output.pack(fill="both", expand=True, padx=16, pady=(4, 16))

    def get_content(self):
        return self.script_output.get("1.0", "end").strip()

    def start_generate_script(self):
        idea = self.story_input.get("1.0", "end").strip()
        if not idea or idea.startswith("例："):
            messagebox.showwarning("提示", "请先输入故事创意或剧情大纲！")
            return
        self.generate_btn.configure(state="disabled", text="生成中...")
        self.script_output.delete("1.0", "end")
        self.script_output.insert("end", "正在调用 AI 生成镜头脚本，请稍候...\n")
        threading.Thread(target=self.generate_script, args=(idea,), daemon=True).start()

    def generate_script(self, idea):
        api_key = self.ctx.config.get("mimo_api_key", "").strip()
        if not api_key:
            api_key = self.ctx.config.get("api_key", "").strip()
        base_url = self.ctx.config.get("api_base_url", "https://token-plan-cn.xiaomimimo.com/anthropic").strip().rstrip("/")
        model = self.ctx.config.get("api_model", "mimo-v2.5-pro").strip()
        
        if not base_url or not api_key:
            self._script_error("错误：请先在「全局设置」中配置 Base URL 和 API Key。")
            return
        
        if "/anthropic" in base_url:
            base_url = base_url.replace("/anthropic", "/v1")
        elif not base_url.endswith("/v1"):
            base_url = base_url.rstrip("/") + "/v1"
            
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json; charset=utf-8",
            }
            url = f"{base_url}/chat/completions"
            payload = {
                "model": model, "temperature": 0.8, "max_tokens": 16384,
                "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                              {"role": "user", "content": idea}]
            }

            self._update_script_text("正在请求 API...\n")
            response = requests.post(url, headers=headers, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), timeout=120)
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                lines = content.split("\n")
                processed = []
                for line in lines:
                    processed.append(line)
                    stripped = line.strip()
                    if stripped.startswith("英文Prompt") or stripped.startswith("English Prompt"):
                        if VISUAL_SUFFIX.split(",")[0] not in stripped:
                            base = line.rstrip()
                            sep = ", " if base and not base.endswith(",") else " "
                            processed[-1] = base + sep + VISUAL_SUFFIX
                self._update_script_text("\n".join(processed))
            else:
                err = f"API 错误: HTTP {response.status_code}\n{response.text[:500]}"
                self._update_script_text(err)
        except requests.exceptions.Timeout:
            self._script_error("错误：请求超时（120秒）")
        except requests.exceptions.ConnectionError:
            self._script_error("错误：无法连接到 API 服务器")
        except Exception as e:
            self._script_error(f"错误：{e}")
        finally:
            self.ctx.safe_after(lambda: self.generate_btn.configure(state="normal", text="生成动态镜头脚本"))

    def _update_script_text(self, text):
        self.ctx.safe_after(lambda: (self.script_output.delete("1.0", "end"),
                                     self.script_output.insert("end", text)))

    def _script_error(self, msg):
        self._update_script_text(msg)

    def export_script(self):
        content = self.get_content()
        if not content:
            messagebox.showwarning("提示", "没有可导出的脚本内容！")
            return
        path = filedialog.asksaveasfilename(title="导出脚本", defaultextension=".txt",
                                             filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
                                             initialfile="镜头脚本.txt")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("完成", f"脚本已保存至:\n{path}")

    def copy_script(self):
        content = self.get_content()
        if not content:
            messagebox.showwarning("提示", "没有可复制的脚本内容！")
            return
        self.ctx.root.clipboard_clear()
        self.ctx.root.clipboard_append(content)
