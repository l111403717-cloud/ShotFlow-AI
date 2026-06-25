"""Assembly page mixin"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import requests
import json
import os
import time
import re
import subprocess
import wave
import struct
import shutil

from ..constants import (C, FONT_TITLE, FONT_H2, FONT_BODY, FONT_MONO, FONT_MONO_SM, FONT_SMALL,
                         PAD_MD, PAD_LG, PAD_SM, CORNER_RADIUS, CORNER_RADIUS_LG)
from ..ui import SectionCard, LogBox


class AssemblyMixin:

    def _build_page_assembly(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color=C["bg"])
        scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(scroll, text="一键总装 (FFmpeg)", font=FONT_TITLE,
                     text_color=C["accent"]).pack(anchor="w", padx=20, pady=(16, 8))

        card = SectionCard(scroll, title="总装状态")
        card.pack(fill="x", padx=20, pady=(0, 12))
        self.asm_status_label = ctk.CTkLabel(card, text="正在检测镜头...", font=FONT_H2, text_color=C["text"])
        self.asm_status_label.pack(anchor="w", padx=16, pady=(8, 4))
        self.asm_detail_label = ctk.CTkLabel(card, text="视频: -- | 音频: -- | 台词: --",
                                              font=FONT_SMALL, text_color=C["text3"])
        self.asm_detail_label.pack(anchor="w", padx=16, pady=(0, 12))
        ctk.CTkButton(card, text="刷新检测", font=FONT_SMALL, width=80,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text"], corner_radius=6, height=28,
                       command=self._refresh_assembly_status).pack(anchor="w", padx=16, pady=(0, 12))

        card = SectionCard(scroll, title="项目设置")
        card.pack(fill="x", padx=20, pady=(0, 12))
        ctk.CTkLabel(card, text="项目名称:", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w", padx=16, pady=(6, 0))
        self.project_name_var = tk.StringVar(value=self.config.get("project_name", ""))
        ctk.CTkEntry(card, textvariable=self.project_name_var, font=FONT_MONO,
                      placeholder_text="留空则使用 shot", fg_color=C["surface2"],
                      border_color=C["border"], corner_radius=8).pack(fill="x", padx=16, pady=(2, 8))
        ctk.CTkLabel(card, text="保存路径:", font=FONT_SMALL, text_color=C["text2"]).pack(anchor="w", padx=16)
        save_row = ctk.CTkFrame(card, fg_color="transparent")
        save_row.pack(fill="x", padx=16, pady=(2, 4))
        self.save_path_var = tk.StringVar(value=self.config.get("save_path", ""))
        ctk.CTkEntry(save_row, textvariable=self.save_path_var, font=FONT_MONO_SM,
                      placeholder_text="留空则使用程序根目录", fg_color=C["surface2"],
                      border_color=C["border"], corner_radius=8).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(save_row, text="浏览", width=60, font=FONT_SMALL,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text"], corner_radius=6, height=30,
                       command=self._browse_save_path).pack(side="left", padx=(6, 0))
        ctk.CTkLabel(card, text="音频/视频/成片均保存在此目录下",
                     font=FONT_SMALL, text_color=C["text3"]).pack(anchor="w", padx=16, pady=(0, 10))

        card = SectionCard(scroll, title="视频来源目录")
        card.pack(fill="x", padx=20, pady=(0, 12))
        dir_row = ctk.CTkFrame(card, fg_color="transparent")
        dir_row.pack(fill="x", padx=16, pady=(4, 4))
        self.asm_video_dir_var = tk.StringVar(value=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output_video"))
        ctk.CTkEntry(dir_row, textvariable=self.asm_video_dir_var, font=FONT_MONO_SM,
                      fg_color=C["surface2"], border_color=C["border"],
                      corner_radius=8).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(dir_row, text="浏览", width=60, font=FONT_SMALL,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text"], corner_radius=6, height=30,
                       command=self._browse_asm_video_dir).pack(side="left", padx=(6, 0))
        ctk.CTkLabel(card, text="程序会自动将视频按创建时间映射为 shot_X.mp4",
                     font=FONT_SMALL, text_color=C["text3"]).pack(anchor="w", padx=16, pady=(0, 10))

        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(4, 12))
        self.asm_start_btn = ctk.CTkButton(btn_frame, text="开始一键高质量合片", font=FONT_H2,
            fg_color=C["accent"], text_color=C["bg"], hover_color=C["accent2"],
            corner_radius=12, height=48, command=self._start_assembly)
        self.asm_start_btn.pack(fill="x", pady=(0, 8))
        ctk.CTkButton(btn_frame, text="打开最终成片目录", font=FONT_BODY,
                       fg_color=C["surface2"], hover_color=C["border"],
                       text_color=C["text"], corner_radius=10, height=38,
                       command=self._open_final_output).pack(anchor="w")

        ctk.CTkLabel(scroll, text="总装日志", font=FONT_H2, text_color=C["text"]).pack(anchor="w", padx=20, pady=(8, 4))
        self.asm_log = LogBox(scroll)
        self.asm_log.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        self.root.after(300, self._refresh_assembly_status)

    def _get_project_prefix(self):
        name = self.project_name_var.get().strip()
        return name if name else "shot"

    def _archive_old_files(self, sub_dirs=("output_video", "output_audio")):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        save = self.save_path_var.get().strip()
        root = save if save and os.path.isdir(save) else base
        files_to_archive = []
        for sub in sub_dirs:
            d = os.path.join(root, sub)
            if os.path.isdir(d):
                for f in os.listdir(d):
                    full = os.path.join(d, f)
                    if os.path.isfile(full): files_to_archive.append((sub, f, full))
        if not files_to_archive: return 0
        ts = time.strftime("%Y%m%d_%H%M%S")
        project = self.project_name_var.get().strip()
        folder_name = f"{project}_备份_{ts}" if project else f"默认项目_备份_{ts}"
        archive_dir = os.path.join(root, "archive_history", folder_name)
        os.makedirs(archive_dir, exist_ok=True)
        moved = 0
        for sub, fname, fpath in files_to_archive:
            dest_sub = os.path.join(archive_dir, sub)
            os.makedirs(dest_sub, exist_ok=True)
            try: shutil.move(fpath, os.path.join(dest_sub, fname)); moved += 1
            except Exception: pass
        return moved

    def _shot_name(self, idx, ext=""):
        name = self.project_name_var.get().strip()
        base = f"{name}_shot_{idx}" if name else f"shot_{idx}"
        return base + ext if ext else base

    def _tts_audio_name(self, idx, voice_name, text, ext=".wav"):
        voice = voice_name.strip() if voice_name else "默认"
        clean = text[:4] if text else ""
        clean = re.sub(r'[\\/:*?"<>|，。！？、；：\s\.\!\?\,\;\:]', '', clean)
        return f"{voice}_{clean}_{idx}{ext}"

    def _get_output_dir(self, sub_dir):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        save = self.save_path_var.get().strip()
        if save and os.path.isdir(save): return os.path.join(save, sub_dir)
        return os.path.join(base, sub_dir)

    def _asm_log(self, msg):
        self.safe_after(lambda: self.global_log.append(f"[{time.strftime('%H:%M:%S')}] {msg}"))

    def _browse_save_path(self):
        path = filedialog.askdirectory(title="选择保存路径")
        if path:
            self.save_path_var.set(path)
            self._save_assembly_config()
            self._refresh_assembly_status()

    def _browse_asm_video_dir(self):
        path = filedialog.askdirectory(title="选择视频来源目录")
        if path:
            self.asm_video_dir_var.set(path)
            self._refresh_assembly_status()

    def _save_assembly_config(self):
        self.config["project_name"] = self.project_name_var.get().strip()
        self.config["save_path"] = self.save_path_var.get().strip()
        if hasattr(self, "video_duration_var"):
            self.config["bailian_video_duration"] = self.video_duration_var.get()
        from ..config import save_config
        save_config(self.config)

    def _open_final_output(self):
        final_dir = self._get_output_dir("output_final")
        os.makedirs(final_dir, exist_ok=True)
        os.startfile(final_dir)

    def _find_file(self, directory, shot_num, ext):
        target = self._shot_name(shot_num, ext)
        exact = os.path.join(directory, target)
        if os.path.isfile(exact): return exact
        pattern = re.compile(rf"shot_{shot_num}{re.escape(ext)}$", re.IGNORECASE)
        if os.path.isdir(directory):
            for f in os.listdir(directory):
                if pattern.search(f): return os.path.join(directory, f)
        pattern2 = re.compile(rf"_{shot_num}{re.escape(ext)}$", re.IGNORECASE)
        if os.path.isdir(directory):
            for f in os.listdir(directory):
                if pattern2.search(f): return os.path.join(directory, f)
        return exact

    def _refresh_assembly_status(self):
        prefix = self._get_project_prefix()
        video_dir = self.asm_video_dir_var.get().strip()
        audio_dir = self._get_tts_audio_dir()

        renamed_count = 0
        if os.path.isdir(video_dir):
            existing_shots = set()
            unsorted_files = []
            for f in os.listdir(video_dir):
                if not f.lower().endswith(".mp4"): continue
                full = os.path.join(video_dir, f)
                m = re.match(r"(?:.+_)?shot_(\d+)\.mp4$", f, re.IGNORECASE)
                if m: existing_shots.add(int(m.group(1)))
                else: unsorted_files.append((os.path.getctime(full), f, full))
            unsorted_files.sort(key=lambda x: x[0])
            next_num = 0
            for ctime, fname, fpath in unsorted_files:
                while next_num in existing_shots: next_num += 1
                target_name = self._shot_name(next_num, ".mp4")
                target = os.path.join(video_dir, target_name)
                if fpath != target:
                    try: shutil.copy2(fpath, target); renamed_count += 1; existing_shots.add(next_num)
                    except Exception: pass
                next_num += 1

        video_shots = set()
        if os.path.isdir(video_dir):
            for f in os.listdir(video_dir):
                if f.lower().endswith(".mp4"):
                    m = re.match(r"(?:.+_)?shot_(\d+)\.mp4$", f, re.IGNORECASE)
                    if m: video_shots.add(int(m.group(1)))

        audio_shots = set()
        if os.path.isdir(audio_dir):
            for f in os.listdir(audio_dir):
                if f.lower().endswith(".wav"):
                    m = re.match(r"(?:.+_)?shot_(\d+)\.wav$", f, re.IGNORECASE)
                    if m: audio_shots.add(int(m.group(1))); continue
                    m = re.match(r".+_(\d+)\.wav$", f, re.IGNORECASE)
                    if m: audio_shots.add(int(m.group(1)))

        dialogue_count = 0
        try:
            content = self.tts_text.get("1.0", "end").strip()
            if content: dialogue_count = len([l for l in content.split("\n") if l.strip()])
        except Exception: pass

        matched = sorted(video_shots & audio_shots)
        total_video = len(video_shots)
        total_audio = len(audio_shots)

        if renamed_count:
            self.asm_status_label.configure(text=f"已自动映射 {renamed_count} 个视频 → 就绪镜头：{len(matched)} 个",
                text_color=C["green"] if matched else C["warn"])
        elif matched:
            self.asm_status_label.configure(text=f"当前准备就绪的镜头数量：{len(matched)} 个", text_color=C["green"])
        else:
            self.asm_status_label.configure(text="当前准备就绪的镜头数量：0 个", text_color=C["warn"])

        self.asm_detail_label.configure(
            text=f"项目: {prefix} | 视频: {total_video} | 音频: {total_audio} | 台词: {dialogue_count} | 匹配: {len(matched)}")
        self._matched_shots = matched
        self._video_shots_set = video_shots
        self._audio_shots_set = audio_shots

    def _start_assembly(self):
        self._save_assembly_config()
        self._refresh_assembly_status()
        if not hasattr(self, "_matched_shots") or not self._matched_shots:
            messagebox.showwarning("提示",
                "没有匹配的音画镜头！\n\n请确保：\n1. 视频目录下有 .mp4 文件\n2. 音频目录下有 shot_X.wav 文件\n\n"
                "程序会自动将视频按创建时间映射为 shot_X.mp4。")
            return
        dialogue_map = {}
        try:
            content = self.tts_text.get("1.0", "end").strip()
            if content:
                for i, line in enumerate(content.split("\n"), 1):
                    stripped = line.strip()
                    if stripped: dialogue_map[i] = stripped
        except Exception: pass
        self.asm_start_btn.configure(state="disabled", text="合片中...")
        self.asm_log.clear_all()
        self._asm_log(f"开始总装，共 {len(self._matched_shots)} 个镜头")
        threading.Thread(target=self._assembly_worker, args=(self._matched_shots, dialogue_map), daemon=True).start()

    def _assembly_worker(self, shots, dialogue_map):
        prefix = self._get_project_prefix()
        video_dir = self.asm_video_dir_var.get().strip()
        audio_dir = self._get_tts_audio_dir()
        final_dir = self._get_output_dir("output_final")
        os.makedirs(final_dir, exist_ok=True)
        try: video_duration = float(self.video_duration_var.get())
        except Exception: video_duration = 5.0
        success, fail = 0, 0

        for shot_num in shots:
            video_path = self._find_file(video_dir, shot_num, ".mp4")
            audio_path = self._find_file(audio_dir, shot_num, ".wav")
            srt_path = os.path.join(audio_dir, self._shot_name(shot_num, ".srt"))
            out_path = os.path.join(final_dir, self._shot_name(shot_num, "_FINAL.mp4"))
            if not os.path.isfile(video_path):
                self._asm_log(f"[{shot_num}] 视频不存在: {video_path}"); fail += 1; continue
            if not os.path.isfile(audio_path):
                self._asm_log(f"[{shot_num}] 音频不存在: {audio_path}"); fail += 1; continue
            try:
                audio_duration = self._get_wav_duration(audio_path)
                self._asm_log(f"[{shot_num}] 音频时长: {audio_duration:.2f}s")
            except Exception as e:
                self._asm_log(f"[{shot_num}] 读取音频失败: {e}"); fail += 1; continue
            dialogue_text = dialogue_map.get(shot_num, f"Shot {shot_num}")
            try:
                self._generate_srt(srt_path, dialogue_text, audio_duration)
                self._asm_log(f"[{shot_num}] 字幕已生成")
            except Exception as e:
                self._asm_log(f"[{shot_num}] 字幕生成失败: {e}"); fail += 1; continue
            pad_len = max(0, audio_duration - video_duration)
            try:
                self._run_ffmpeg_assembly(video_path, audio_path, srt_path, out_path, pad_len)
                self._asm_log(f"[镜头 {shot_num}] 合成成功！"); success += 1
            except Exception as e:
                self._asm_log(f"[{shot_num}] FFmpeg 合成失败: {e}"); fail += 1

        self._asm_log(f"{'='*40}")
        self._asm_log(f"总装完成: 成功 {success}，失败 {fail}")
        if success: self._asm_log(f"成片目录: {final_dir}")
        self.safe_after(lambda: self.asm_start_btn.configure(state="normal", text="开始一键高质量合片"))

    def _get_wav_duration(self, wav_path):
        with wave.open(wav_path, "rb") as wf:
            frames = wf.getnframes(); rate = wf.getframerate()
            channels = wf.getnchannels(); sw = wf.getsampwidth()
            header_dur = frames / rate
        file_size = os.path.getsize(wav_path)
        data_bytes = file_size - 44
        calc_dur = data_bytes / (rate * channels * sw)
        if header_dur > calc_dur * 2: return calc_dur
        return header_dur

    def _generate_srt(self, srt_path, text, duration):
        def _fmt_ts(seconds):
            h = int(seconds // 3600); m = int((seconds % 3600) // 60)
            s = int(seconds % 60); ms = int((seconds - int(seconds)) * 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(f"1\n00:00:00,000 --> {_fmt_ts(duration)}\n{text}\n")

    def _run_ffmpeg_assembly(self, video_path, audio_path, srt_path, out_path, pad_len):
        cmd = ["ffmpeg", "-y", "-i", video_path, "-f", "s16le", "-ar", "24000", "-ac", "1",
               "-i", audio_path, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
               "-c:a", "libmp3lame", "-b:a", "128k", "-shortest", out_path]
        self._asm_log(f"[{os.path.basename(out_path)}] FFmpeg 编码中...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(result.stderr[-300:] if result.stderr else "Unknown error")
