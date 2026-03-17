"""
TTS Automation Tool - Chuyển đổi truyện thành audio tự động
Hỗ trợ Edge-TTS (Microsoft Neural) và gTTS (Google Translate TTS)
"""

import asyncio
import json
import os
import random
import re
import shutil
import time
import unicodedata
from pathlib import Path
from typing import List, Dict, Optional
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import boto3
from botocore.client import Config
# from supabase import create_client, Client  # Tạm thời comment
import requests
import edge_tts
from gtts import gTTS


class TTSAutomation:
    def __init__(self):
        # TTS Engine
        self.tts_engine = "edge-tts"  # "edge-tts" hoặc "gtts"

        # Edge-TTS config
        self.edge_voice_female = "vi-VN-HoaiMyNeural"
        self.edge_voice_male   = "vi-VN-NamMinhNeural"
        self.edge_chunk_size   = 500   # ký tự / đoạn
        self.edge_delay_min    = 2     # delay tối thiểu giữa các chunk (s)
        self.edge_delay_max    = 5     # delay tối đa
        self.edge_max_retries  = 3

        # Anti-block state (dùng chung cho cả hai engine)
        self._consecutive_failures = 0
        self._last_request_time    = 0.0

        # Đường dẫn
        self.DATA_DIR   = Path("myData")
        self.OUTPUT_DIR = Path("audio_output")
        self.OUTPUT_DIR.mkdir(exist_ok=True)
        self.CONFIG_FILE = Path("config.json")

        # Dữ liệu
        self.stories: List[Dict]  = []
        self.chapters: List[Dict] = []

        # Credentials (được nhập từ GUI)
        self.r2_config       = {}
        self.supabase_config = {}

        # Rate limiting
        self.delay_between_chapters = 3
        self.delay_between_voices   = 1

    # ------------------------------------------------------------------ Data

    def load_data(self):
        """Đọc dữ liệu từ file JSON"""
        try:
            with open(self.DATA_DIR / "stories_rows.json", "r", encoding="utf-8") as f:
                self.stories = json.load(f)
            with open(self.DATA_DIR / "chapters_private_rows.json", "r", encoding="utf-8") as f:
                self.chapters = json.load(f)
            return True
        except Exception as e:
            print(f"Lỗi khi đọc dữ liệu: {e}")
            return False

    def save_config(self, config: Dict) -> bool:
        """Lưu cấu hình vào file"""
        try:
            with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Lỗi khi lưu cấu hình: {e}")
            return False

    def load_config(self) -> Optional[Dict]:
        """Load cấu hình từ file"""
        try:
            if self.CONFIG_FILE.exists():
                with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            return None
        except Exception as e:
            print(f"Lỗi khi load cấu hình: {e}")
            return None

    def get_story_by_id(self, story_id: str) -> Optional[Dict]:
        for story in self.stories:
            if story["id"] == story_id:
                return story
        return None

    def get_chapters_by_story(self, story_id: str) -> List[Dict]:
        story_chapters = [ch for ch in self.chapters if ch["story_id"] == story_id]
        story_chapters.sort(key=lambda x: x.get("chapter_number", 0))
        return story_chapters

    # ------------------------------------------------------------------ Text utils

    def clean_text_for_tts(self, text: str) -> str:
        """Làm sạch text để phù hợp với TTS"""
        text = re.sub(
            r'[^\w\s\.,!?;:\-\(\)\"\'àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩị'
            r'òóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ'
            r'ÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ]',
            ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def sanitize_filename(self, filename: str) -> str:
        """Làm sạch tên file: bỏ dấu, dùng underscore"""
        filename = filename.replace('đ', 'd').replace('Đ', 'D')
        filename = unicodedata.normalize('NFD', filename)
        filename = ''.join(c for c in filename if unicodedata.category(c) != 'Mn')
        filename = re.sub(r'\s+', '_', filename.strip())
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        if len(filename) > 100:
            filename = filename[:100]
        return filename

    def split_text(self, text: str, max_length: int = 500) -> List[str]:
        """Chia nhỏ text thành các đoạn theo câu, tối đa max_length ký tự."""
        sentences = re.split(r'([.!?。！？]+)', text)
        chunks: List[str] = []
        current = ""

        for i in range(0, len(sentences), 2):
            sentence  = sentences[i]
            delimiter = sentences[i + 1] if i + 1 < len(sentences) else ""
            piece = sentence + delimiter

            if len(current) + len(piece) <= max_length:
                current += piece
            else:
                if current:
                    chunks.append(current.strip())
                # Nếu câu đơn quá dài → chia cứng
                if len(piece) > max_length:
                    for j in range(0, len(piece), max_length):
                        chunks.append(piece[j:j + max_length].strip())
                    current = ""
                else:
                    current = piece

        if current:
            chunks.append(current.strip())

        return [c for c in chunks if c] or [text[i:i+max_length] for i in range(0, len(text), max_length)]

    # ------------------------------------------------------------------ Audio utils

    @staticmethod
    def _is_valid_audio(data: bytes) -> bool:
        """Kiểm tra data có phải audio hợp lệ không (magic bytes)."""
        if len(data) < 4:
            return False
        if data[:3] == b'ID3':          # MP3 với ID3 tag
            return True
        if data[0] == 0xFF and (data[1] & 0xE0) == 0xE0:  # MPEG sync word
            return True
        if data[:4] == b'RIFF':         # WAV
            return True
        return False

    def _merge_mp3_files(self, temp_files: list, output_path: Path):
        """Ghép nhiều file MP3 thành một (binary concat)."""
        if len(temp_files) == 1:
            shutil.move(str(temp_files[0]), str(output_path))
            return
        try:
            with open(str(output_path), 'wb') as outf:
                for tf in temp_files:
                    outf.write(tf.read_bytes())
        finally:
            for tf in temp_files:
                tf.unlink(missing_ok=True)

    # ------------------------------------------------------------------ Edge-TTS

    async def _generate_single_edge_tts(
            self, text: str, output_path: Path, voice: str,
            progress_callback=None) -> bool:
        """Tạo 1 file MP3 bằng Edge-TTS. Retry + exponential backoff + circuit breaker."""
        max_retries = self.edge_max_retries

        for attempt in range(max_retries):
            # Circuit breaker
            if self._consecutive_failures >= 5:
                wait = 180
                if progress_callback:
                    progress_callback(
                        f"    ⛔ Circuit breaker: tạm dừng {wait}s "
                        f"({self._consecutive_failures} lỗi liên tiếp)...")
                await asyncio.sleep(wait)
                self._consecutive_failures = 0
            elif self._consecutive_failures >= 3:
                wait = 60
                if progress_callback:
                    progress_callback(
                        f"    ⚠ Tạm dừng {wait}s sau {self._consecutive_failures} lỗi liên tiếp...")
                await asyncio.sleep(wait)

            # Rate limiting: đảm bảo min delay giữa các request
            elapsed = time.monotonic() - self._last_request_time
            if elapsed < self.edge_delay_min:
                await asyncio.sleep(self.edge_delay_min - elapsed)

            try:
                self._last_request_time = time.monotonic()
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(str(output_path))

                if output_path.exists() and output_path.stat().st_size > 100:
                    self._consecutive_failures = 0
                    return True
                else:
                    raise ValueError("File audio rỗng hoặc quá nhỏ")

            except Exception as e:
                self._consecutive_failures += 1
                err_str = str(e)
                is_403 = "403" in err_str or "InvalidResponse" in err_str

                if attempt < max_retries - 1:
                    # Exponential backoff + jitter
                    base_wait = (attempt + 1) * 3
                    jitter    = random.uniform(1, 3)
                    wait      = base_wait + jitter
                    if is_403:
                        wait = max(wait, 15)  # 403 → chờ tối thiểu 15s
                    if progress_callback:
                        progress_callback(f"    ⚠ Edge-TTS lỗi: {err_str[:100]}")
                        progress_callback(
                            f"    ⏳ Retry {attempt+2}/{max_retries} sau {wait:.0f}s...")
                    await asyncio.sleep(wait)
                else:
                    if progress_callback:
                        progress_callback(
                            f"    ✗ Edge-TTS thất bại sau {max_retries} lần: {err_str[:120]}")
                    return False

        return False

    async def generate_audio_edge_tts(
            self, text: str, output_path: Path,
            progress_callback=None, voice: Optional[str] = None) -> bool:
        """Tạo audio Edge-TTS. Chia chunks, tạo từng đoạn, merge MP3."""
        voice  = voice or self.edge_voice_female
        chunks = self.split_text(text, max_length=self.edge_chunk_size)

        if len(chunks) > 1 and progress_callback:
            progress_callback(
                f"  📝 {len(text)} ký tự → {len(chunks)} đoạn "
                f"({self.edge_chunk_size} ký tự/đoạn)...")

        temp_files: List[Path] = []
        skipped = 0

        for i, chunk in enumerate(chunks):
            if len(chunks) > 1 and progress_callback:
                progress_callback(f"  📝 Đoạn {i+1}/{len(chunks)} ({len(chunk)} ký tự)...")

            temp_file = output_path.parent / f"tmp_edge_{output_path.stem}_{i}.mp3"
            success   = await self._generate_single_edge_tts(
                chunk, temp_file, voice, progress_callback)

            if not success:
                temp_file.unlink(missing_ok=True)
                skipped += 1
                if progress_callback:
                    progress_callback(f"  ⚠ Bỏ qua đoạn {i+1}/{len(chunks)} (lỗi, tiếp tục...)")
                if i < len(chunks) - 1:
                    await asyncio.sleep(1)
                continue

            temp_files.append(temp_file)

            # Delay ngẫu nhiên giữa các đoạn (chống chặn IP)
            if i < len(chunks) - 1:
                delay = random.uniform(self.edge_delay_min, self.edge_delay_max)
                if len(chunks) > 1 and progress_callback:
                    progress_callback(f"    ⏳ Chờ {delay:.1f}s trước đoạn tiếp theo...")
                await asyncio.sleep(delay)

        if not temp_files:
            if progress_callback:
                progress_callback(f"  ✗ Tất cả {len(chunks)} đoạn đều thất bại")
            return False

        if skipped > 0 and progress_callback:
            progress_callback(
                f"  ⚠ Bỏ qua {skipped}/{len(chunks)} đoạn lỗi, "
                f"ghép {len(temp_files)} đoạn còn lại...")
        elif len(temp_files) > 1 and progress_callback:
            progress_callback(f"  🔗 Ghép {len(temp_files)} đoạn MP3...")

        self._merge_mp3_files(temp_files, output_path)

        if output_path.exists() and output_path.stat().st_size > 0:
            if len(chunks) > 1 and progress_callback:
                progress_callback(
                    f"  ✓ Ghép xong: {output_path.name} "
                    f"({output_path.stat().st_size:,} bytes)")
            return True
        return False

    # ------------------------------------------------------------------ gTTS

    async def generate_audio_gtts(
            self, text: str, output_path: Path,
            progress_callback=None, voice: Optional[str] = None,
            max_retries: int = 3) -> bool:
        """Tạo audio gTTS (chỉ giọng nữ tiếng Việt). Sync trong executor."""
        loop = asyncio.get_event_loop()

        def _do():
            tts = gTTS(text=text, lang='vi', slow=False)
            tts.save(str(output_path))

        for attempt in range(max_retries):
            try:
                await loop.run_in_executor(None, _do)
                if output_path.exists() and output_path.stat().st_size > 100:
                    if progress_callback:
                        progress_callback(
                            f"  ✓ gTTS: {output_path.name} "
                            f"({output_path.stat().st_size:,} bytes)")
                    self._consecutive_failures = 0
                    return True
                else:
                    raise ValueError("File audio rỗng")
            except Exception as e:
                self._consecutive_failures += 1
                if attempt < max_retries - 1:
                    wait = (attempt + 1) * 2 + random.uniform(0.5, 1.5)
                    if progress_callback:
                        progress_callback(f"  ⚠ gTTS lỗi: {e}")
                        progress_callback(f"  ⏳ Retry {attempt+2}/{max_retries} sau {wait:.0f}s...")
                    await asyncio.sleep(wait)
                else:
                    if progress_callback:
                        progress_callback(f"  ✗ gTTS thất bại: {e}")
                    return False
        return False

    # ------------------------------------------------------------------ Router

    async def generate_audio(
            self, text: str, voice: Optional[str], output_path: Path,
            progress_callback=None, max_retries: int = 3) -> bool:
        """Route sang engine đang dùng."""
        clean_text = self.clean_text_for_tts(text)
        if not clean_text:
            if progress_callback:
                progress_callback("  ✗ Text rỗng sau khi làm sạch")
            return False

        if self.tts_engine == "gtts":
            return await self.generate_audio_gtts(
                clean_text, output_path, progress_callback, voice, max_retries)
        else:
            return await self.generate_audio_edge_tts(
                clean_text, output_path, progress_callback, voice)

    # ------------------------------------------------------------------ Chapter

    async def process_chapter(
            self, story: Dict, chapter: Dict, progress_callback=None) -> bool:
        """Xử lý một chương: tạo audio nam/nữ, upload R2, cập nhật Supabase."""
        try:
            story_title = self.sanitize_filename(story["title"])
            chapter_num = chapter.get("chapter_number", 0)

            story_dir = self.OUTPUT_DIR / story_title
            story_dir.mkdir(exist_ok=True)

            # Cấu hình theo engine
            if self.tts_engine == "gtts":
                male_voice   = None         # gTTS không hỗ trợ giọng nam
                female_voice = None
                engine_label = "gTTS"
                skip_male    = True
            else:
                male_voice   = self.edge_voice_male
                female_voice = self.edge_voice_female
                engine_label = "Edge-TTS"
                skip_male    = False

            base_filename  = f"{story_title}_chuong_{chapter_num:04d}"
            male_filename  = f"{base_filename}_male.mp3"
            female_filename = f"{base_filename}_female.mp3"
            male_path   = story_dir / male_filename
            female_path = story_dir / female_filename

            content = chapter.get("content", "")
            if not content:
                if progress_callback:
                    progress_callback(f"  ⚠ Chương {chapter_num} không có nội dung")
                return False

            chapter_title_text = chapter.get("title", f"Chương {chapter_num}")
            full_content = f"{chapter_title_text}. {content}"

            if progress_callback:
                progress_callback(
                    f"\n📖 Đang xử lý ({engine_label}): {story_title} — Chương {chapter_num}")

            # ----- GIỌNG NAM -----
            if skip_male:
                if progress_callback:
                    progress_callback("  ⚠ gTTS không hỗ trợ giọng nam — bỏ qua file male")
                male_success = True  # không cần file nam
                male_path    = None
            else:
                if progress_callback:
                    progress_callback(f"  🎙 Tạo giọng nam ({male_voice})...")
                male_success = await self.generate_audio(
                    full_content, male_voice, male_path, progress_callback)
                if not male_success:
                    if progress_callback:
                        progress_callback(f"  ⚠ Bỏ qua chương {chapter_num} (lỗi giọng nam)")
                    return False
                await asyncio.sleep(self.delay_between_voices)

            # ----- GIỌNG NỮ -----
            if progress_callback:
                lbl = female_voice or "vi (gTTS)"
                progress_callback(f"  🎙 Tạo giọng nữ ({lbl})...")
            female_success = await self.generate_audio(
                full_content, female_voice, female_path, progress_callback)
            if not female_success:
                if progress_callback:
                    progress_callback(f"  ⚠ Bỏ qua chương {chapter_num} (lỗi giọng nữ)")
                return False

            # ----- Log local -----
            if progress_callback:
                if male_path and male_path.exists():
                    progress_callback(f"  💾 File: {male_path}")
                progress_callback(f"  💾 File: {female_path}")

            # ----- Upload R2 -----
            male_url   = None
            female_url = None

            if self.r2_config.get("enabled"):
                if progress_callback:
                    progress_callback("  ☁ Đang upload lên R2...")
                if male_path and male_path.exists():
                    male_url = await self.upload_to_r2(male_path, story_title, male_filename)
                if female_path.exists():
                    female_url = await self.upload_to_r2(female_path, story_title, female_filename)
                if progress_callback:
                    if female_url:
                        progress_callback("  ✓ Đã upload lên R2")
                    else:
                        progress_callback("  ⚠ Upload R2 thất bại")

            # ----- Supabase -----
            if self.supabase_config.get("enabled") and female_url:
                if progress_callback:
                    progress_callback("  💾 Đang cập nhật Supabase...")
                await self.update_supabase(chapter["id"], male_url, female_url)
                if progress_callback:
                    progress_callback("  ✓ Đã cập nhật Supabase")

            await asyncio.sleep(self.delay_between_chapters)
            return True

        except Exception as e:
            if progress_callback:
                progress_callback(f"  ✗ Lỗi xử lý chương: {e}")
            return False

    # ------------------------------------------------------------------ Cloud

    async def upload_to_r2(
            self, file_path: Path, story_folder: str, filename: str) -> Optional[str]:
        """Upload file lên Cloudflare R2."""
        try:
            if not file_path.exists():
                return None
            if file_path.stat().st_size == 0:
                return None

            loop = asyncio.get_event_loop()

            def _upload():
                s3 = boto3.client(
                    's3',
                    endpoint_url=self.r2_config["endpoint_url"],
                    aws_access_key_id=self.r2_config["access_key_id"],
                    aws_secret_access_key=self.r2_config["secret_access_key"],
                    config=Config(signature_version='s3v4',
                                  s3={'addressing_style': 'path'}),
                    verify=False
                )
                key = f"audio/{story_folder}/{filename}"
                content_type = 'audio/mpeg'
                s3.upload_file(
                    str(file_path),
                    self.r2_config["bucket_name"],
                    key,
                    ExtraArgs={'ContentType': content_type}
                )
                return f"{self.r2_config['public_url']}/{key}"

            return await loop.run_in_executor(None, _upload)

        except Exception as e:
            print(f"Lỗi upload R2: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def update_supabase(self, chapter_id: str, male_url: Optional[str], female_url: Optional[str]):
        """Ghi URL audio vào bảng chapter_audios.
        Schema: chapter_audios(id, chapter_id, voice='male'|'female', audio_url, created_at, updated_at)
        Chiến lược: DELETE cũ → INSERT mới (tránh duplicate do không có UNIQUE constraint).
        """
        try:
            base_url = self.supabase_config["url"].rstrip("/")
            key      = self.supabase_config["key"]

            records = []
            if male_url:
                records.append({"chapter_id": chapter_id, "voice": "male",   "audio_url": male_url})
            if female_url:
                records.append({"chapter_id": chapter_id, "voice": "female", "audio_url": female_url})
            if not records:
                return

            loop = asyncio.get_event_loop()

            def _do():
                headers = {
                    "apikey":        key,
                    "Authorization": f"Bearer {key}",
                    "Content-Type":  "application/json",
                    "Prefer":        "return=minimal",
                }
                for rec in records:
                    voice = rec["voice"]
                    # Xóa record cũ để tránh duplicate
                    requests.delete(
                        f"{base_url}/rest/v1/chapter_audios",
                        params={"chapter_id": f"eq.{chapter_id}", "voice": f"eq.{voice}"},
                        headers=headers,
                        timeout=15,
                    )
                    # Insert record mới
                    resp = requests.post(
                        f"{base_url}/rest/v1/chapter_audios",
                        headers=headers,
                        json=rec,
                        timeout=15,
                    )
                    resp.raise_for_status()

            await loop.run_in_executor(None, _do)

        except Exception as e:
            print(f"Lỗi cập nhật Supabase: {e}")
            raise


# ═══════════════════════════════════════════════════════════════════════════════
#  GUI
# ═══════════════════════════════════════════════════════════════════════════════

class TTSAutomationGUI:
    """GUI 2 panel: trái = chọn truyện/chương (luôn hiện), phải = Cấu hình + Xử lý."""

    def __init__(self, root):
        self.root = root
        self.root.title("TTS Automation — Edge-TTS / gTTS")
        self.root.geometry("1150x720")
        self.root.minsize(900, 600)

        self.automation        = TTSAutomation()
        self.selected_story_id = None
        self._stop_event       = threading.Event()

        self._build_ui()
        self._load_initial()

    # ------------------------------------------------------------------ UI build

    def _build_ui(self):
        # Header bar
        hdr = ttk.Frame(self.root, padding=(8, 4))
        hdr.pack(fill=tk.X, side=tk.TOP)
        ttk.Label(hdr, text="TTS Automation",
                  font=("Arial", 11, "bold")).pack(side=tk.LEFT)
        self._tts_status_lbl = ttk.Label(hdr, text="", foreground="gray",
                                         font=("Arial", 9))
        self._tts_status_lbl.pack(side=tk.RIGHT, padx=(0, 4))
        ttk.Button(hdr, text="Test TTS",
                   command=self._test_tts).pack(side=tk.RIGHT, padx=6)
        ttk.Separator(self.root, orient=tk.HORIZONTAL).pack(fill=tk.X)

        # Main paned window
        paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL,
                               sashwidth=5, sashrelief=tk.RAISED, bg="#d0d0d0")
        paned.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        left = ttk.Frame(paned, padding=4)
        paned.add(left, minsize=270)
        self._build_selection(left)

        right = ttk.Frame(paned, padding=4)
        paned.add(right, minsize=560)
        self._build_right(right)

    def _build_selection(self, parent):
        sf = ttk.LabelFrame(parent, text="Truyện", padding=4)
        sf.pack(fill=tk.BOTH, expand=False, pady=(0, 6))
        sb = ttk.Scrollbar(sf)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._story_lb = tk.Listbox(sf, yscrollcommand=sb.set, height=9,
                                    exportselection=False, activestyle="dotbox")
        self._story_lb.pack(fill=tk.BOTH, expand=True)
        sb.config(command=self._story_lb.yview)
        self._story_lb.bind("<<ListboxSelect>>", self._on_story_select)

        cf = ttk.LabelFrame(parent, text="Chương", padding=4)
        cf.pack(fill=tk.BOTH, expand=True)

        br = ttk.Frame(cf)
        br.pack(fill=tk.X, pady=(0, 3))
        ttk.Button(br, text="Chọn tất cả", command=self._select_all).pack(side=tk.LEFT)
        ttk.Button(br, text="Bỏ hết",
                   command=self._deselect_all).pack(side=tk.LEFT, padx=4)

        sb2 = ttk.Scrollbar(cf)
        sb2.pack(side=tk.RIGHT, fill=tk.Y)
        self._chap_lb = tk.Listbox(cf, selectmode=tk.MULTIPLE, yscrollcommand=sb2.set,
                                   exportselection=False, activestyle="dotbox")
        self._chap_lb.pack(fill=tk.BOTH, expand=True)
        sb2.config(command=self._chap_lb.yview)
        self._chap_lb.bind("<<ListboxSelect>>", self._on_chap_select)

        self._sel_lbl = ttk.Label(parent, text="Chưa chọn chương nào",
                                  foreground="#555", font=("Arial", 9, "italic"))
        self._sel_lbl.pack(anchor=tk.W, pady=(4, 0))

    def _build_right(self, parent):
        nb = ttk.Notebook(parent)
        nb.pack(fill=tk.BOTH, expand=True)
        self._notebook = nb
        nb.bind("<<NotebookTabChanged>>", self._on_tab_change)

        tab_cfg = ttk.Frame(nb)
        nb.add(tab_cfg, text="  ⚙  Cấu hình  ")
        self._build_config_tab(tab_cfg)

        tab_proc = ttk.Frame(nb)
        nb.add(tab_proc, text="  ▶  Xử lý  ")
        self._build_process_tab(tab_proc)

    def _build_config_tab(self, parent):
        canvas = tk.Canvas(parent, highlightthickness=0)
        vsb = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        frm = ttk.Frame(canvas, padding=(10, 8))
        win = canvas.create_window((0, 0), window=frm, anchor=tk.NW)
        frm.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))

        # ── Engine ──────────────────────────────────────────────────────────
        ef = ttk.LabelFrame(frm, text="TTS Engine", padding=8)
        ef.pack(fill=tk.X, pady=(0, 8))
        self._engine_frame = ef
        self._engine_var = tk.StringVar(value="edge-tts")
        ttk.Radiobutton(
            ef,
            text="Edge-TTS — Giọng nam + nữ, chất lượng Neural cao (Microsoft)",
            variable=self._engine_var, value="edge-tts",
            command=self._on_engine_change).pack(anchor=tk.W)
        ttk.Radiobutton(
            ef,
            text="gTTS — Backup, chỉ giọng nữ (Google Translate)",
            variable=self._engine_var, value="gtts",
            command=self._on_engine_change).pack(anchor=tk.W)

        # ── Edge-TTS config ─────────────────────────────────────────────────
        self._edge_frame = ttk.LabelFrame(frm, text="Edge-TTS", padding=8)
        ef2 = self._edge_frame

        ttk.Label(ef2, text="Giọng nữ:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(ef2, text="vi-VN-HoaiMyNeural",
                  foreground="#0055cc").grid(row=0, column=1, sticky=tk.W, padx=4)
        ttk.Label(ef2, text="Giọng nam:").grid(row=0, column=2, sticky=tk.W, padx=(14, 0))
        ttk.Label(ef2, text="vi-VN-NamMinhNeural",
                  foreground="#0055cc").grid(row=0, column=3, sticky=tk.W, padx=4)

        ttk.Label(ef2, text="Ký tự/đoạn:").grid(row=1, column=0, sticky=tk.W, pady=(8, 0))
        self._edge_chunk = ttk.Spinbox(ef2, from_=100, to=2000, width=7)
        self._edge_chunk.set(500)
        self._edge_chunk.grid(row=1, column=1, sticky=tk.W, padx=4, pady=(8, 0))
        ttk.Label(ef2, text="(mặc định 500, giảm nếu bị lỗi)",
                  foreground="#666", font=("Arial", 8)).grid(
            row=1, column=2, columnspan=2, sticky=tk.W, padx=(14, 0), pady=(8, 0))

        ttk.Label(ef2, text="Delay min (s):").grid(row=2, column=0, sticky=tk.W, pady=(6, 0))
        self._edge_delay_min = ttk.Spinbox(ef2, from_=1, to=30, width=7)
        self._edge_delay_min.set(2)
        self._edge_delay_min.grid(row=2, column=1, sticky=tk.W, padx=4, pady=(6, 0))

        ttk.Label(ef2, text="Delay max (s):").grid(row=2, column=2, sticky=tk.W, padx=(14, 0), pady=(6, 0))
        self._edge_delay_max = ttk.Spinbox(ef2, from_=2, to=60, width=7)
        self._edge_delay_max.set(5)
        self._edge_delay_max.grid(row=2, column=3, sticky=tk.W, padx=4, pady=(6, 0))

        ttk.Label(ef2, text="← Delay ngẫu nhiên giữa các đoạn (chống lỗi 403)",
                  foreground="#666", font=("Arial", 8)).grid(
            row=3, column=0, columnspan=4, sticky=tk.W, pady=(2, 0))

        ef2.columnconfigure(1, weight=1)

        # ── gTTS config ─────────────────────────────────────────────────────
        self._gtts_frame = ttk.LabelFrame(frm, text="gTTS", padding=8)
        gf = self._gtts_frame

        ttk.Label(gf,
                  text="⚠ gTTS chỉ có 1 giọng nữ duy nhất (Google Translate).",
                  foreground="#cc6600", font=("Arial", 9)).pack(anchor=tk.W)
        ttk.Label(gf,
                  text="Giọng nam sẽ bị bỏ qua — chỉ tạo file female.mp3.",
                  foreground="#cc6600", font=("Arial", 9)).pack(anchor=tk.W, pady=(2, 0))
        ttk.Label(gf,
                  text="Khuyến nghị: dùng Edge-TTS làm engine chính.",
                  foreground="#555", font=("Arial", 8, "italic")).pack(anchor=tk.W, pady=(4, 0))

        # ── Tốc độ ──────────────────────────────────────────────────────────
        df = ttk.LabelFrame(frm, text="Tốc độ xử lý", padding=8)
        df.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(df, text="Delay giữa chương (s):").grid(row=0, column=0, sticky=tk.W)
        self._delay_ch = ttk.Spinbox(df, from_=1, to=60, width=7)
        self._delay_ch.set(3)
        self._delay_ch.grid(row=0, column=1, sticky=tk.W, padx=4)
        ttk.Label(df, text="Delay giữa giọng (s):").grid(row=1, column=0, sticky=tk.W, pady=3)
        self._delay_v = ttk.Spinbox(df, from_=0, to=10, width=7)
        self._delay_v.set(1)
        self._delay_v.grid(row=1, column=1, sticky=tk.W, padx=4)

        # ── R2 ──────────────────────────────────────────────────────────────
        r2f = ttk.LabelFrame(frm, text="Cloudflare R2  (tuỳ chọn)", padding=8)
        r2f.pack(fill=tk.X, pady=(0, 8))
        self._r2_on = tk.BooleanVar(value=False)
        ttk.Checkbutton(r2f, text="Bật upload R2",
                        variable=self._r2_on).grid(row=0, column=0, columnspan=2, sticky=tk.W)
        for i, (lbl, attr, hidden) in enumerate([
            ("Endpoint URL:", "_r2_ep", False),
            ("Access Key ID:", "_r2_ak", False),
            ("Secret Key:",    "_r2_sk", True),
            ("Bucket:",        "_r2_bk", False),
            ("Public URL:",    "_r2_pu", False),
        ], 1):
            ttk.Label(r2f, text=lbl).grid(row=i, column=0, sticky=tk.W, pady=1)
            e = ttk.Entry(r2f, width=44, show="*" if hidden else "")
            e.grid(row=i, column=1, sticky=tk.EW, padx=4, pady=1)
            setattr(self, attr, e)
        r2f.columnconfigure(1, weight=1)

        # ── Supabase ─────────────────────────────────────────────────────────
        spf = ttk.LabelFrame(frm, text="Supabase  (tuỳ chọn)", padding=8)
        spf.pack(fill=tk.X, pady=(0, 8))
        self._sp_on = tk.BooleanVar(value=False)
        ttk.Checkbutton(spf, text="Bật Supabase",
                        variable=self._sp_on).grid(row=0, column=0, columnspan=2, sticky=tk.W)
        ttk.Label(spf, text="URL:").grid(row=1, column=0, sticky=tk.W, pady=1)
        self._sp_url = ttk.Entry(spf, width=44)
        self._sp_url.grid(row=1, column=1, sticky=tk.EW, padx=4)
        ttk.Label(spf, text="Key:").grid(row=2, column=0, sticky=tk.W, pady=1)
        self._sp_key = ttk.Entry(spf, width=44, show="*")
        self._sp_key.grid(row=2, column=1, sticky=tk.EW, padx=4)
        spf.columnconfigure(1, weight=1)

        ttk.Button(frm, text="💾  Lưu cấu hình",
                   command=self._save_config).pack(anchor=tk.W, pady=4)

        # Show correct engine frame on startup
        self._on_engine_change()

    def _on_engine_change(self):
        """Show/hide config frame theo engine."""
        self._edge_frame.pack_forget()
        self._gtts_frame.pack_forget()
        engine = self._engine_var.get()
        if engine == "gtts":
            self._gtts_frame.pack(fill=tk.X, pady=(0, 8), after=self._engine_frame)
        else:
            self._edge_frame.pack(fill=tk.X, pady=(0, 8), after=self._engine_frame)

    def _build_process_tab(self, parent):
        self._proc_summary = ttk.Label(
            parent, text="Chưa chọn truyện / chương",
            font=("Arial", 10, "bold"))
        self._proc_summary.pack(anchor=tk.W, padx=8, pady=(6, 2))

        pf = ttk.Frame(parent)
        pf.pack(fill=tk.X, padx=8, pady=(0, 4))
        self._prog_bar = ttk.Progressbar(pf, mode="determinate")
        self._prog_bar.pack(fill=tk.X)
        self._prog_lbl = ttk.Label(pf, text="", font=("Arial", 9))
        self._prog_lbl.pack(anchor=tk.W)
        self._eta_lbl = ttk.Label(pf, text="", font=("Arial", 9), foreground="#555")
        self._eta_lbl.pack(anchor=tk.W)

        bf = ttk.Frame(parent)
        bf.pack(fill=tk.X, padx=8, pady=(0, 4))
        self._start_btn = ttk.Button(
            bf, text="🚀  Bắt đầu xử lý", command=self._start)
        self._start_btn.pack(side=tk.LEFT)
        self._stop_btn = ttk.Button(
            bf, text="⏹  Dừng", command=self._stop, state=tk.DISABLED)
        self._stop_btn.pack(side=tk.LEFT, padx=6)
        ttk.Button(bf, text="🗑  Xóa log",
                   command=self._clear_log).pack(side=tk.LEFT)

        lf = ttk.LabelFrame(parent, text="Log", padding=4)
        lf.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))
        self._log_txt = scrolledtext.ScrolledText(
            lf, state=tk.DISABLED, font=("Consolas", 9), wrap=tk.WORD)
        self._log_txt.pack(fill=tk.BOTH, expand=True)

    # ------------------------------------------------------------------ Events

    def _on_story_select(self, _event=None):
        sel = self._story_lb.curselection()
        if not sel:
            return
        story = self.automation.stories[sel[0]]
        self.selected_story_id = story["id"]

        chapters = self.automation.get_chapters_by_story(self.selected_story_id)
        self._chap_lb.delete(0, tk.END)
        for ch in chapters:
            num   = ch.get("chapter_number", 0)
            title = ch.get("title", "—")
            self._chap_lb.insert(tk.END, f"Chương {num}: {title}")

        self._update_sel_label()
        self._update_proc_summary()

    def _on_chap_select(self, _event=None):
        self._update_sel_label()
        self._update_proc_summary()

    def _select_all(self):
        self._chap_lb.select_set(0, tk.END)
        self._on_chap_select()

    def _deselect_all(self):
        self._chap_lb.select_clear(0, tk.END)
        self._on_chap_select()

    def _on_tab_change(self, _event=None):
        self._update_proc_summary()

    def _update_sel_label(self):
        n = len(self._chap_lb.curselection())
        if n == 0:
            self._sel_lbl.config(text="Chưa chọn chương nào", foreground="#888")
        else:
            self._sel_lbl.config(text=f"✔ Đã chọn {n} chương", foreground="#006600")

    def _update_proc_summary(self):
        if not self.selected_story_id:
            self._proc_summary.config(text="← Chọn truyện và chương ở panel bên trái")
            return
        story = self.automation.get_story_by_id(self.selected_story_id)
        n     = len(self._chap_lb.curselection())
        name  = story.get("title", "?") if story else "?"
        self._proc_summary.config(
            text=f"Truyện: {name}   |   Đã chọn {n} chương sẽ xử lý")

    # ------------------------------------------------------------------ Test TTS

    def _test_tts(self):
        """Thử sinh audio ngắn để kiểm tra engine hiện tại."""
        self._apply_config_to_automation()
        engine = self.automation.tts_engine
        self._tts_status_lbl.config(text=f"⬤ Đang test {engine}…", foreground="orange")
        self.root.update_idletasks()

        def _do():
            ok  = False
            msg = ""
            try:
                test_text = "Xin chào, đây là thử nghiệm giọng đọc."
                test_path = Path("audio_output") / "_test_tts.mp3"
                test_path.parent.mkdir(exist_ok=True)

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                if engine == "gtts":
                    ok = loop.run_until_complete(
                        self.automation.generate_audio_gtts(test_text, test_path))
                else:
                    ok = loop.run_until_complete(
                        self.automation.generate_audio_edge_tts(
                            test_text, test_path,
                            voice=self.automation.edge_voice_female))
                loop.close()
                test_path.unlink(missing_ok=True)
                msg = f"⬤ {engine} OK" if ok else f"⬤ {engine} THẤT BẠI"
            except Exception as e:
                msg = f"⬤ Lỗi: {str(e)[:60]}"

            color = "#006600" if ok else "red"
            self.root.after(0, lambda: self._tts_status_lbl.config(
                text=msg, foreground=color))

        threading.Thread(target=_do, daemon=True).start()

    # ------------------------------------------------------------------ Config

    def _save_config(self):
        try:
            cfg = {
                "tts_engine": self._engine_var.get(),
                "edge_tts": {
                    "chunk_size": int(self._edge_chunk.get()),
                    "delay_min":  int(self._edge_delay_min.get()),
                    "delay_max":  int(self._edge_delay_max.get()),
                },
                "r2": {
                    "enabled":           self._r2_on.get(),
                    "endpoint_url":      self._r2_ep.get(),
                    "access_key_id":     self._r2_ak.get(),
                    "secret_access_key": self._r2_sk.get(),
                    "bucket_name":       self._r2_bk.get(),
                    "public_url":        self._r2_pu.get(),
                },
                "supabase": {
                    "enabled": self._sp_on.get(),
                    "url":     self._sp_url.get(),
                    "key":     self._sp_key.get(),
                },
                "rate_limiting": {
                    "delay_chapters": int(self._delay_ch.get()),
                    "delay_voices":   int(self._delay_v.get()),
                },
            }
            if self.automation.save_config(cfg):
                messagebox.showinfo("Thành công", "Cấu hình đã lưu!\nLần sau mở sẽ tự load.")
                self.log("💾 Đã lưu cấu hình vào config.json")
            else:
                messagebox.showerror("Lỗi", "Không thể lưu cấu hình")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi khi lưu: {e}")

    def _load_config(self):
        cfg = self.automation.load_config()
        if not cfg:
            return
        try:
            self._engine_var.set(cfg.get("tts_engine", "edge-tts"))

            edge = cfg.get("edge_tts", {})
            self._edge_chunk.set(edge.get("chunk_size", 500))
            self._edge_delay_min.set(edge.get("delay_min", 2))
            self._edge_delay_max.set(edge.get("delay_max", 5))

            r2 = cfg.get("r2", {})
            self._r2_on.set(r2.get("enabled", False))
            self._r2_ep.insert(0, r2.get("endpoint_url", ""))
            self._r2_ak.insert(0, r2.get("access_key_id", ""))
            self._r2_sk.insert(0, r2.get("secret_access_key", ""))
            self._r2_bk.insert(0, r2.get("bucket_name", ""))
            self._r2_pu.insert(0, r2.get("public_url", ""))

            sp = cfg.get("supabase", {})
            self._sp_on.set(sp.get("enabled", False))
            self._sp_url.insert(0, sp.get("url", ""))
            self._sp_key.insert(0, sp.get("key", ""))

            rl = cfg.get("rate_limiting", {})
            self._delay_ch.set(rl.get("delay_chapters", 3))
            self._delay_v.set(rl.get("delay_voices", 1))

            self._on_engine_change()
            self.log("✓ Đã load cấu hình từ config.json")
        except Exception as e:
            self.log(f"⚠ Lỗi khi load cấu hình: {e}")

    # ------------------------------------------------------------------ Processing

    def _apply_config_to_automation(self):
        self.automation.tts_engine = self._engine_var.get()

        # Edge-TTS
        self.automation.edge_chunk_size = int(self._edge_chunk.get())
        self.automation.edge_delay_min  = int(self._edge_delay_min.get())
        self.automation.edge_delay_max  = int(self._edge_delay_max.get())

        # Rate limiting
        self.automation.delay_between_chapters = int(self._delay_ch.get())
        self.automation.delay_between_voices   = int(self._delay_v.get())

        # Cloud
        self.automation.r2_config = {
            "enabled":           self._r2_on.get(),
            "endpoint_url":      self._r2_ep.get(),
            "access_key_id":     self._r2_ak.get(),
            "secret_access_key": self._r2_sk.get(),
            "bucket_name":       self._r2_bk.get(),
            "public_url":        self._r2_pu.get(),
        }
        self.automation.supabase_config = {
            "enabled": self._sp_on.get(),
            "url":     self._sp_url.get(),
            "key":     self._sp_key.get(),
        }

    def _start(self):
        if not self.selected_story_id:
            messagebox.showwarning("Cảnh báo", "Chưa chọn truyện")
            return
        indices = self._chap_lb.curselection()
        if not indices:
            messagebox.showwarning("Cảnh báo", "Chưa chọn chương nào")
            return

        self._apply_config_to_automation()
        self._stop_event.clear()
        self._start_btn.config(state=tk.DISABLED)
        self._stop_btn.config(state=tk.NORMAL)
        self._notebook.select(1)

        threading.Thread(
            target=self._run_processing, args=(indices,), daemon=True).start()

    def _stop(self):
        self._stop_event.set()
        self.log("⏹ Đang dừng sau chương hiện tại…")

    def _run_processing(self, selected_indices):
        try:
            story        = self.automation.get_story_by_id(self.selected_story_id)
            all_chapters = self.automation.get_chapters_by_story(self.selected_story_id)
            chapters     = [all_chapters[i] for i in selected_indices]
            total        = len(chapters)

            self.log(f"\n{'='*60}")
            self.log(f"Truyện: {story['title']}  |  {total} chương  |  Engine: {self.automation.tts_engine}")
            self.log(f"{'='*60}\n")

            self.root.after(0, lambda: self._prog_bar.configure(maximum=total, value=0))

            success_count    = 0
            fail_count       = 0
            chapter_durations: list = []

            for idx, chapter in enumerate(chapters, 1):
                if self._stop_event.is_set():
                    self.log("⏹ Đã dừng theo yêu cầu.")
                    break

                # ETA: ước tính thời gian còn lại dựa trên trung bình mỗi chương
                if chapter_durations:
                    avg_secs = sum(chapter_durations) / len(chapter_durations)
                    eta_secs = avg_secs * (total - idx + 1)
                    eta_str  = self._fmt_eta(eta_secs)
                    self.root.after(0, lambda s=eta_str, i=idx, t=total: (
                        self._prog_lbl.config(text=f"Đang xử lý {i}/{t}…"),
                        self._eta_lbl.config(text=f"⏱ Còn lại ≈ {s}")
                    ))
                else:
                    self.root.after(0, lambda i=idx, t=total: (
                        self._prog_lbl.config(text=f"Đang xử lý {i}/{t}…"),
                        self._eta_lbl.config(text="⏱ Đang tính thời gian…")
                    ))

                chapter_start = time.monotonic()

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                ok = loop.run_until_complete(
                    self.automation.process_chapter(story, chapter, self.log))
                loop.close()

                chapter_durations.append(time.monotonic() - chapter_start)

                if ok:
                    success_count += 1
                else:
                    fail_count += 1

                self.root.after(0, lambda i=idx: self._prog_bar.configure(value=i))

            self.log(f"\n{'='*60}")
            if fail_count == 0:
                self.log(f"✅ Hoàn thành!  Thành công {success_count}/{total} chương")
            else:
                self.log(f"⚠  Xong!  Thành công {success_count} | Thất bại {fail_count} / {total} chương")
            self.log(f"{'='*60}\n")

            def _show_done():
                if fail_count == 0:
                    messagebox.showinfo("Xong", f"Thành công {success_count}/{total} chương!")
                else:
                    messagebox.showwarning(
                        "Hoàn thành (có lỗi)",
                        f"Thành công {success_count}, thất bại {fail_count} / {total} chương.\n"
                        "Xem log để biết chi tiết.")

            self.root.after(0, _show_done)

        except Exception as e:
            self.log(f"\n❌ Lỗi nghiêm trọng: {e}")
            self.root.after(0, lambda: messagebox.showerror("Lỗi", f"Có lỗi xảy ra:\n{e}"))
        finally:
            self.root.after(0, self._reset_buttons)

    @staticmethod
    def _fmt_eta(seconds: float) -> str:
        s = int(seconds)
        h, rem = divmod(s, 3600)
        m, s   = divmod(rem, 60)
        if h > 0:
            return f"{h}h {m:02d}m {s:02d}s"
        if m > 0:
            return f"{m}m {s:02d}s"
        return f"{s}s"

    def _reset_buttons(self):
        self._start_btn.config(state=tk.NORMAL)
        self._stop_btn.config(state=tk.DISABLED)
        self._prog_lbl.config(text="")
        self._eta_lbl.config(text="")

    # ------------------------------------------------------------------ Log

    def log(self, message: str):
        def _do():
            self._log_txt.config(state=tk.NORMAL)
            self._log_txt.insert(tk.END, message + "\n")
            self._log_txt.see(tk.END)
            self._log_txt.config(state=tk.DISABLED)
        self.root.after(0, _do)

    def _clear_log(self):
        self._log_txt.config(state=tk.NORMAL)
        self._log_txt.delete("1.0", tk.END)
        self._log_txt.config(state=tk.DISABLED)

    # ------------------------------------------------------------------ Init data

    def _load_initial(self):
        if self.automation.load_data():
            for s in self.automation.stories:
                self._story_lb.insert(tk.END, s.get("title", "—"))
            self.log("✓ Đã load dữ liệu thành công")
        else:
            messagebox.showerror(
                "Lỗi",
                "Không load được dữ liệu từ myData/\n"
                "Kiểm tra file stories_rows.json và chapters_private_rows.json")
        self._load_config()


def main():
    root = tk.Tk()
    TTSAutomationGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
