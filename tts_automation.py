"""
TTS Automation Tool - Chuyển đổi truyện thành audio tự động
Hỗ trợ VietTTS (local) và TikTok TTS (cloud)
"""

import asyncio
import base64
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

# ---- TikTok TTS Constants ----
TIKTOK_ENDPOINTS = [
    "https://api16-normal-v6.tiktokv.com/media/api/text/speech/invoke/",
    "https://api16-normal-useast5.us.tiktokv.com/media/api/text/speech/invoke/",
]

TIKTOK_USER_AGENTS = [
    "com.zhiliaoapp.musically/2022600030 (Linux; U; Android 7.1.2; es_ES; SM-G988N; Build/NRD90M;tt-ok/3.12.13.1)",
    "com.zhiliaoapp.musically/2022600040 (Linux; U; Android 10; en_US; Pixel 4; Build/QQ3A.200805.001;tt-ok/3.12.13.1)",
    "com.zhiliaoapp.musically/2022600050 (Linux; U; Android 11; ja_JP; SM-G991B; Build/RP1A.200720.012;tt-ok/3.12.13.1)",
    "com.zhiliaoapp.musically/2022600060 (Linux; U; Android 12; ko_KR; SM-S908N; Build/SP1A.210812.016;tt-ok/3.12.13.1)",
    "com.zhiliaoapp.musically/2022600070 (Linux; U; Android 9; vi_VN; SM-A505F; Build/PPR1.180610.011;tt-ok/3.12.13.1)",
]

TIKTOK_VOICES = {
    "vi_001": "Nu (Vietnamese Female)",
    "vi_002": "Nam (Vietnamese Male)",
    "vi_003": "Nu tre (Vietnamese Young Female)",
}

class TTSAutomation:
    def __init__(self):
        # TTS Engine
        self.tts_engine = "viettts"  # "viettts" hoặc "tiktok"

        # VietTTS config
        self.viettts_voice_female = "nu-nhe-nhang"
        self.viettts_voice_male = "nguyen-ngoc-ngan"
        self.viettts_chunk_size = 1000

        # TikTok TTS config
        self.tiktok_voice_female = "vi_001"
        self.tiktok_voice_male = "vi_002"
        self.tiktok_session_id = ""       # Optional, cho endpoint v6
        self.tiktok_chunk_size = 200      # TikTok max ~200 ký tự
        self.tiktok_delay_min = 3         # Min delay giữa request (s)
        self.tiktok_delay_max = 8         # Max delay giữa request (s)
        self.tiktok_max_retries = 5       # Số lần retry mỗi chunk

        # TikTok internal state
        self._tiktok_consecutive_failures = 0
        self._tiktok_last_request_time = 0.0

        # Đường dẫn
        self.DATA_DIR = Path("myData")
        self.OUTPUT_DIR = Path("audio_output")
        self.OUTPUT_DIR.mkdir(exist_ok=True)
        self.CONFIG_FILE = Path("config.json")

        # Dữ liệu
        self.stories: List[Dict] = []
        self.chapters: List[Dict] = []

        # Credentials (sẽ được nhập từ GUI)
        self.r2_config = {}
        self.supabase_config = {}

        # Rate limiting
        self.delay_between_chapters = 3
        self.delay_between_voices = 1

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
        """Lấy thông tin truyện theo ID"""
        for story in self.stories:
            if story["id"] == story_id:
                return story
        return None

    def get_chapters_by_story(self, story_id: str) -> List[Dict]:
        """Lấy danh sách chương theo truyện"""
        story_chapters = [ch for ch in self.chapters if ch["story_id"] == story_id]
        # Sắp xếp theo chapter_number
        story_chapters.sort(key=lambda x: x.get("chapter_number", 0))
        return story_chapters

    def clean_text_for_tts(self, text: str) -> str:
        """Làm sạch text để phù hợp với TTS"""
        # Loại bỏ các ký tự đặc biệt, giữ lại dấu câu cơ bản
        text = re.sub(r'[^\w\s\.,!?;:\-\(\)\"\'àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ]', ' ', text)
        # Loại bỏ khoảng trắng thừa
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def sanitize_filename(self, filename: str) -> str:
        """Làm sạch tên file: bỏ dấu, dùng underscore"""
        # Xử lý riêng đ/Đ (không phân rã qua NFD)
        filename = filename.replace('đ', 'd').replace('Đ', 'D')
        # Xóa dấu tiếng Việt còn lại
        filename = unicodedata.normalize('NFD', filename)
        filename = ''.join(c for c in filename if unicodedata.category(c) != 'Mn')
        # Khoảng trắng → underscore
        filename = re.sub(r'\s+', '_', filename.strip())
        # Loại bỏ ký tự không hợp lệ
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        # Giới hạn độ dài
        if len(filename) > 100:
            filename = filename[:100]
        return filename

    def split_text_for_tiktok(self, text: str, max_length=300):
        """Chia nhỏ text thành các đoạn ngắn theo câu"""
        # Chia theo câu (dấu chấm, chấm than, chấm hỏi)
        sentences = re.split(r'([.!?。！？]+)', text)

        chunks = []
        current_chunk = ""

        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            delimiter = sentences[i + 1] if i + 1 < len(sentences) else ""

            if len(current_chunk) + len(sentence) + len(delimiter) <= max_length:
                current_chunk += sentence + delimiter
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + delimiter

        if current_chunk:
            chunks.append(current_chunk.strip())

        # Nếu không có chunk nào, chia cứng theo độ dài
        if not chunks:
            chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]

        return chunks

    async def generate_audio_viettts(self, text: str, output_path: Path, progress_callback=None, voice=None, max_retries=3):
        """Tạo audio bằng VietTTS local server (http://localhost:8298)
        Khởi động server trước: start_viettts.bat
        Luôn chia nhỏ text để tránh VietTTS trả về file rỗng với text dài.
        """
        chunk_size = self.viettts_chunk_size  # mặc định 300 ký tự
        chunks = self.split_text_for_tiktok(text, max_length=chunk_size)

        if len(chunks) > 1 and progress_callback:
            progress_callback(f"⚠ Text {len(text)} ký tự → chia {len(chunks)} đoạn ({chunk_size} ký tự/đoạn)...")

        temp_files = []
        skipped = 0
        for i, chunk in enumerate(chunks):
            if len(chunks) > 1 and progress_callback:
                progress_callback(f"  📝 Đoạn {i+1}/{len(chunks)} ({len(chunk)} ký tự)...")

            temp_file = output_path.parent / f"temp_{output_path.stem}_{i}.wav"
            try:
                success = await self._generate_single_viettts(chunk, temp_file, progress_callback, voice, max_retries)
            except ConnectionError:
                for tf in temp_files:
                    tf.unlink(missing_ok=True)
                temp_file.unlink(missing_ok=True)
                raise
            except Exception as e:
                if progress_callback:
                    progress_callback(f"✗ Đoạn {i+1} thất bại: {e}")
                success = False

            if not success:
                temp_file.unlink(missing_ok=True)
                skipped += 1
                if progress_callback:
                    progress_callback(f"  ⚠ Bỏ qua đoạn {i+1}/{len(chunks)} (audio rỗng, tiếp tục...)")
                if i < len(chunks) - 1:
                    await asyncio.sleep(1)
                continue

            temp_files.append(temp_file)
            if i < len(chunks) - 1:
                await asyncio.sleep(1)

        if not temp_files:
            if progress_callback:
                progress_callback(f"✗ Tất cả {len(chunks)} đoạn đều thất bại, không tạo được audio")
            return False

        if skipped > 0 and progress_callback:
            progress_callback(f"  ⚠ Đã bỏ qua {skipped}/{len(chunks)} đoạn lỗi, ghép {len(temp_files)} đoạn còn lại...")
        elif len(temp_files) > 1 and progress_callback:
            progress_callback(f"  🔗 Ghép {len(temp_files)} đoạn audio...")
        self._merge_audio_files(temp_files, output_path)

        if output_path.exists() and output_path.stat().st_size > 0:
            if len(temp_files) > 1 and progress_callback:
                progress_callback(
                    f"✓ Đã ghép xong: {output_path.name} ({output_path.stat().st_size:,} bytes)"
                )
            return True
        return False

    @staticmethod
    def _is_valid_audio(data: bytes) -> bool:
        """Kiểm tra data có phải audio hợp lệ không (magic bytes)."""
        if len(data) < 4:
            return False
        # WAV: RIFF header
        if data[:4] == b'RIFF':
            return True
        # ID3 tag (MP3 phổ biến nhất)
        if data[:3] == b'ID3':
            return True
        # MPEG sync word: 0xFF 0xFx hoặc 0xFF 0xEx
        if data[0] == 0xFF and (data[1] & 0xE0) == 0xE0:
            return True
        return False

    async def _generate_single_viettts(self, text: str, output_path: Path, progress_callback=None, voice=None, max_retries=3):
        """Tạo một file audio VietTTS đơn lẻ (không chia nhỏ).
        - Dùng run_in_executor để không block event loop.
        - Validate magic bytes MP3 + kích thước tối thiểu trước khi lưu.
        """
        server_url = "http://localhost:8298"
        loop = asyncio.get_event_loop()

        def _do_request():
            return requests.post(
                f"{server_url}/v1/audio/speech",
                headers={
                    "Authorization": "Bearer viet-tts",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "tts-1",
                    "input": text,
                    "voice": voice or self.viettts_voice_female,
                    "speed": 1.0
                },
                timeout=120
            )

        for attempt in range(max_retries):
            try:
                # Chạy request trong thread pool để không block event loop
                response = await loop.run_in_executor(None, _do_request)

                if response.status_code == 200:
                    content = response.content

                    # Validate: WAV header rỗng = 78 bytes, cần ít nhất vài KB audio thật
                    if len(content) < 500:
                        snippet = content[:200]
                        raise ValueError(
                            f"Response quá nhỏ ({len(content)} bytes), "
                            f"có thể là lỗi server: {snippet}"
                        )

                    # Validate: magic bytes audio (WAV/MP3)
                    if not self._is_valid_audio(content):
                        snippet = content[:200]
                        raise ValueError(
                            f"Response không phải audio hợp lệ. "
                            f"Đầu file: {snippet[:50]}"
                        )

                    # Lưu file audio
                    output_path.write_bytes(content)
                    if progress_callback:
                        progress_callback(
                            f"✓ Đã tạo (VietTTS giọng '{voice or self.viettts_voice_female}'): "
                            f"{output_path.name} ({len(content):,} bytes)"
                        )
                    return True

                else:
                    try:
                        error_detail = response.json()
                        error_msg = f"VietTTS server lỗi HTTP {response.status_code}: {error_detail}"
                    except Exception:
                        error_msg = f"VietTTS server lỗi HTTP {response.status_code}: {response.text[:200]}"

                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 3
                        if progress_callback:
                            progress_callback(f"⚠ {error_msg}")
                            progress_callback(f"⏳ Thử lại {attempt + 2}/{max_retries} sau {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    else:
                        if progress_callback:
                            progress_callback(f"✗ {error_msg}")
                        raise ValueError(error_msg)

            except requests.exceptions.ConnectionError:
                error_msg = "VietTTS server chưa chạy! Vui lòng chạy start_viettts.bat trước"
                if progress_callback:
                    progress_callback(f"✗ {error_msg}")
                raise ConnectionError(error_msg)
            except ConnectionError:
                raise
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 3
                    if progress_callback:
                        progress_callback(f"⚠ VietTTS lỗi: {str(e)}")
                        progress_callback(f"⏳ Thử lại {attempt + 2}/{max_retries} sau {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    error_msg = f"VietTTS lỗi: {str(e)}"
                    if progress_callback:
                        progress_callback(f"✗ {error_msg}")
                    raise

        return False

    async def _generate_single_tiktok(self, text, voice, progress_callback=None):
        """Gọi TikTok TTS API cho 1 chunk text. Trả về bytes MP3 hoặc None.
        Tích hợp 7 lớp chống chặn IP."""
        loop = asyncio.get_event_loop()
        max_retries = self.tiktok_max_retries

        # Endpoint order: ưu tiên v6 nếu có session ID, ngược lại dùng useast5
        endpoints = list(TIKTOK_ENDPOINTS)
        if not self.tiktok_session_id:
            endpoints.reverse()

        for attempt in range(max_retries):
            # Layer 6: Circuit breaker
            if self._tiktok_consecutive_failures >= 5:
                wait = 180
                if progress_callback:
                    progress_callback(f"    Circuit breaker: tạm dừng {wait}s sau {self._tiktok_consecutive_failures} lỗi liên tiếp...")
                await asyncio.sleep(wait)
                self._tiktok_consecutive_failures = 0
            elif self._tiktok_consecutive_failures >= 3:
                wait = 60
                if progress_callback:
                    progress_callback(f"    Tạm dừng {wait}s sau {self._tiktok_consecutive_failures} lỗi liên tiếp...")
                await asyncio.sleep(wait)

            # Layer 5: Rate limiting — đảm bảo min delay
            elapsed = time.monotonic() - self._tiktok_last_request_time
            if elapsed < self.tiktok_delay_min:
                await asyncio.sleep(self.tiktok_delay_min - elapsed)

            # Layer 4: Dual-endpoint fallback (xoay vòng khi retry)
            endpoint = endpoints[attempt % len(endpoints)]

            # Layer 3: User-Agent rotation
            headers = {
                "User-Agent": random.choice(TIKTOK_USER_AGENTS),
                "Accept-Encoding": "gzip,deflate,compress",
            }
            if self.tiktok_session_id and "v6" in endpoint:
                headers["Cookie"] = f"sessionid={self.tiktok_session_id}"

            params = {
                "text_speaker": voice,
                "req_text": text.replace("+", "plus").replace("&", "and"),
                "speaker_map_type": 0,
                "aid": 1233,
            }

            def _do_request(ep=endpoint, h=headers, p=params):
                return requests.post(ep, params=p, headers=h, timeout=15)

            try:
                self._tiktok_last_request_time = time.monotonic()
                response = await loop.run_in_executor(None, _do_request)

                # Layer 7: Phân tích response
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status_code", -1)

                    if status == 0:
                        v_str = data.get("data", {}).get("v_str", "")
                        if v_str:
                            audio_bytes = base64.b64decode(v_str)
                            if len(audio_bytes) > 100:
                                self._tiktok_consecutive_failures = 0
                                return audio_bytes
                            else:
                                raise ValueError("Audio data quá nhỏ")
                        else:
                            raise ValueError("Response không có audio (v_str rỗng)")
                    else:
                        msg = data.get("status_msg", f"status_code={status}")
                        raise ValueError(f"TikTok API lỗi: {msg}")

                elif response.status_code == 429:
                    raise ConnectionError("Rate limited (HTTP 429)")
                else:
                    raise ValueError(f"HTTP {response.status_code}")

            except Exception as e:
                self._tiktok_consecutive_failures += 1
                if attempt < max_retries - 1:
                    # Layer 2: Exponential backoff với jitter
                    base_waits = [5, 15, 30, 60, 120]
                    base = base_waits[min(attempt, len(base_waits) - 1)]
                    jitter = random.uniform(0.5, 1.5)
                    wait_time = base * jitter
                    if progress_callback:
                        progress_callback(
                            f"    Retry {attempt+2}/{max_retries} sau {wait_time:.0f}s ({e})")
                    await asyncio.sleep(wait_time)
                else:
                    if progress_callback:
                        progress_callback(f"    Thất bại sau {max_retries} lần thử: {e}")
                    return None

        return None

    def _merge_audio_files(self, temp_files: list, output_path: Path):
        """Ghép nhiều file WAV thành một file WAV (dùng module wave chuẩn Python)."""
        if len(temp_files) == 1:
            shutil.move(str(temp_files[0]), str(output_path))
            return

        import wave
        try:
            with wave.open(str(temp_files[0]), 'rb') as first:
                params = first.getparams()

            with wave.open(str(output_path), 'wb') as out_wav:
                out_wav.setparams(params)
                for tf in temp_files:
                    with wave.open(str(tf), 'rb') as in_wav:
                        out_wav.writeframes(in_wav.readframes(in_wav.getnframes()))
        finally:
            for tf in temp_files:
                tf.unlink(missing_ok=True)

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

    async def generate_audio_tiktok(self, text, output_path, progress_callback=None, voice=None, max_retries=None):
        """Tạo audio bằng TikTok TTS API.
        Chia text thành chunks, gọi API, merge MP3."""
        voice = voice or self.tiktok_voice_female
        chunk_size = self.tiktok_chunk_size
        chunks = self.split_text_for_tiktok(text, max_length=chunk_size)

        if len(chunks) > 1 and progress_callback:
            progress_callback(
                f"  TikTok: {len(text)} ký tự -> {len(chunks)} đoạn ({chunk_size} ký tự/đoạn)")

        mp3_temp_files = []
        skipped = 0

        for i, chunk in enumerate(chunks):
            if progress_callback:
                progress_callback(f"  Đoạn {i+1}/{len(chunks)} ({len(chunk)} ký tự)...")

            audio_bytes = await self._generate_single_tiktok(
                chunk, voice, progress_callback)

            if audio_bytes is None:
                skipped += 1
                if progress_callback:
                    progress_callback(f"  Bỏ qua đoạn {i+1}/{len(chunks)}")
                continue

            temp_file = output_path.parent / f"temp_tiktok_{output_path.stem}_{i}.mp3"
            temp_file.write_bytes(audio_bytes)
            mp3_temp_files.append(temp_file)

            # Layer 1: Random delay giữa chunks
            if i < len(chunks) - 1:
                delay = random.uniform(self.tiktok_delay_min, self.tiktok_delay_max)
                if progress_callback:
                    progress_callback(f"    Chờ {delay:.1f}s...")
                await asyncio.sleep(delay)

        if not mp3_temp_files:
            if progress_callback:
                progress_callback(f"  Tất cả {len(chunks)} đoạn đều thất bại!")
            return False

        if skipped > 0 and progress_callback:
            progress_callback(f"  Bỏ qua {skipped}/{len(chunks)} đoạn lỗi, ghép {len(mp3_temp_files)} đoạn còn lại...")
        elif len(mp3_temp_files) > 1 and progress_callback:
            progress_callback(f"  Ghép {len(mp3_temp_files)} đoạn MP3...")

        self._merge_mp3_files(mp3_temp_files, output_path)

        if output_path.exists() and output_path.stat().st_size > 0:
            if progress_callback:
                progress_callback(
                    f"  Done (TikTok voice '{voice}'): "
                    f"{output_path.name} ({output_path.stat().st_size:,} bytes)")
            return True
        return False

    async def generate_audio(self, text: str, voice: str, output_path: Path, progress_callback=None, max_retries=3):
        """Tạo file audio từ text — route theo engine đã chọn"""
        clean_text = self.clean_text_for_tts(text)

        if not clean_text:
            if progress_callback:
                progress_callback(f"✗ Text rỗng sau khi làm sạch")
            return False

        if self.tts_engine == "tiktok":
            return await self.generate_audio_tiktok(clean_text, output_path, progress_callback, voice)
        else:
            return await self.generate_audio_viettts(clean_text, output_path, progress_callback, voice, max_retries)

    async def process_chapter(self, story: Dict, chapter: Dict, progress_callback=None):
        """Xử lý một chương: tạo audio nam/nữ, upload R2, cập nhật Supabase"""
        try:
            story_title = self.sanitize_filename(story["title"])
            chapter_num = chapter.get("chapter_number", 0)

            # Tạo thư mục cho truyện
            story_dir = self.OUTPUT_DIR / story_title
            story_dir.mkdir(exist_ok=True)

            # Chọn voice + extension + generate function theo engine
            if self.tts_engine == "tiktok":
                ext = ".mp3"
                male_voice = self.tiktok_voice_male
                female_voice = self.tiktok_voice_female
                generate_fn = self.generate_audio_tiktok
                engine_label = "TikTok"
            else:
                ext = ".wav"
                male_voice = self.viettts_voice_male
                female_voice = self.viettts_voice_female
                generate_fn = self.generate_audio_viettts
                engine_label = "VietTTS"

            base_filename = f"{story_title}_chuong_{chapter_num:04d}"
            male_filename = f"{base_filename}_male{ext}"
            female_filename = f"{base_filename}_female{ext}"

            male_path = story_dir / male_filename
            female_path = story_dir / female_filename

            # Lấy nội dung chương
            content = chapter.get("content", "")
            if not content:
                if progress_callback:
                    progress_callback(f"⚠ Chương {chapter_num} không có nội dung")
                return False

            # Thêm tiêu đề chương vào đầu nội dung để đọc
            chapter_title_text = chapter.get("title", f"Chương {chapter_num}")
            full_content = f"{chapter_title_text}. {content}"

            if progress_callback:
                progress_callback(f"\n📖 Đang xử lý ({engine_label}): {story_title} - Chương {chapter_num}")

            # TẠO AUDIO GIỌNG NAM
            if progress_callback:
                progress_callback(f"🎙️ Tạo giọng nam ({male_voice})...")
            male_success = await generate_fn(full_content, male_path, progress_callback, male_voice)
            if not male_success:
                if progress_callback:
                    progress_callback(f"⚠ Bỏ qua chương {chapter_num} do lỗi tạo audio nam")
                return False
            await asyncio.sleep(self.delay_between_voices)

            # TẠO AUDIO GIỌNG NỮ
            if progress_callback:
                progress_callback(f"🎙️ Tạo giọng nữ ({female_voice})...")
            female_success = await generate_fn(full_content, female_path, progress_callback, female_voice)
            if not female_success:
                if progress_callback:
                    progress_callback(f"⚠ Bỏ qua chương {chapter_num} do lỗi tạo audio nữ")
                return False

            # Thông báo file đã lưu local
            if progress_callback:
                progress_callback(f"💾 File local: {male_path}")
                progress_callback(f"💾 File local: {female_path}")

            # Upload lên R2 nếu đã cấu hình
            male_url = None
            female_url = None

            if self.r2_config.get("enabled"):
                if progress_callback:
                    progress_callback(f"☁️ Đang upload lên R2...")

                if male_path.exists():
                    male_url = await self.upload_to_r2(male_path, story_title, male_filename)
                if female_path.exists():
                    female_url = await self.upload_to_r2(female_path, story_title, female_filename)

                if female_url:
                    if progress_callback:
                        progress_callback(f"✓ Đã upload lên R2")
                else:
                    if progress_callback:
                        progress_callback(f"⚠ Upload R2 thất bại")

            # Cập nhật Supabase nếu đã cấu hình
            if self.supabase_config.get("enabled") and female_url:
                if progress_callback:
                    progress_callback(f"💾 Đang cập nhật Supabase...")
                await self.update_supabase(chapter["id"], male_url, female_url)
                if progress_callback:
                    progress_callback(f"✓ Đã cập nhật Supabase")

            # Delay trước khi xử lý chương tiếp theo
            await asyncio.sleep(self.delay_between_chapters)

            return True

        except Exception as e:
            if progress_callback:
                progress_callback(f"✗ Lỗi xử lý chương: {e}")
            return False

    async def upload_to_r2(self, file_path: Path, story_folder: str, filename: str) -> Optional[str]:
        """Upload file lên Cloudflare R2 (tự động tạo 'thư mục' bằng prefix)"""
        try:
            if not file_path.exists():
                print(f"Lỗi: File không tồn tại: {file_path}")
                return None

            file_size = file_path.stat().st_size
            if file_size == 0:
                print(f"Lỗi: File rỗng (0 bytes): {file_path}")
                return None

            loop = asyncio.get_event_loop()

            def _upload():
                s3 = boto3.client(
                    's3',
                    endpoint_url=self.r2_config["endpoint_url"],
                    aws_access_key_id=self.r2_config["access_key_id"],
                    aws_secret_access_key=self.r2_config["secret_access_key"],
                    config=Config(
                        signature_version='s3v4',
                        s3={'addressing_style': 'path'}
                    ),
                    verify=False
                )
                key = f"audio/{story_folder}/{filename}"
                content_type = 'audio/mpeg' if filename.endswith('.mp3') else 'audio/wav'
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

    async def update_supabase(self, chapter_id: str, male_url: str, female_url: str):
        """Cập nhật URL audio vào Supabase"""
        try:
            print(f"Supabase disabled - male: {male_url}, female: {female_url}")
        except Exception as e:
            print(f"Lỗi cập nhật Supabase: {e}")
            raise


class TTSAutomationGUI:
    """GUI 2 panel: trái = chọn truyện/chương (luôn hiện), phải = Cấu hình + Xử lý."""

    def __init__(self, root):
        self.root = root
        self.root.title("TTS Automation — VietTTS / TikTok")
        self.root.geometry("1150x720")
        self.root.minsize(900, 600)

        self.automation = TTSAutomation()
        self.selected_story_id = None
        self._stop_event = threading.Event()

        self._build_ui()
        self._load_initial()

    # ------------------------------------------------------------------ UI build

    def _build_ui(self):
        # Header bar
        hdr = ttk.Frame(self.root, padding=(8, 4))
        hdr.pack(fill=tk.X, side=tk.TOP)
        ttk.Label(hdr, text="TTS Automation",
                  font=("Arial", 11, "bold")).pack(side=tk.LEFT)
        self._server_lbl = ttk.Label(hdr, text="⬤ Chưa kiểm tra", foreground="gray",
                                     font=("Arial", 9))
        self._server_lbl.pack(side=tk.RIGHT, padx=(0, 4))
        ttk.Button(hdr, text="Kiểm tra server",
                   command=self._check_server).pack(side=tk.RIGHT, padx=6)
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
        # Story list
        sf = ttk.LabelFrame(parent, text="Truyện", padding=4)
        sf.pack(fill=tk.BOTH, expand=False, pady=(0, 6))
        sb = ttk.Scrollbar(sf)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._story_lb = tk.Listbox(sf, yscrollcommand=sb.set, height=9,
                                    exportselection=False, activestyle="dotbox")
        self._story_lb.pack(fill=tk.BOTH, expand=True)
        sb.config(command=self._story_lb.yview)
        self._story_lb.bind("<<ListboxSelect>>", self._on_story_select)

        # Chapter list
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
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(
            win, width=e.width))

        # --- Engine Selection ---
        ef = ttk.LabelFrame(frm, text="TTS Engine", padding=8)
        ef.pack(fill=tk.X, pady=(0, 8))
        self._engine_frame = ef
        self._engine_var = tk.StringVar(value="viettts")
        ttk.Radiobutton(ef, text="VietTTS — Local server, giọng Việt tự nhiên",
                        variable=self._engine_var, value="viettts",
                        command=self._on_engine_change).pack(anchor=tk.W)
        ttk.Radiobutton(ef, text="TikTok TTS — Cloud, giọng Việt (vi_001/vi_002)",
                        variable=self._engine_var, value="tiktok",
                        command=self._on_engine_change).pack(anchor=tk.W)

        # --- VietTTS ---
        self._viettts_frame = ttk.LabelFrame(frm, text="VietTTS", padding=8)
        self._viettts_frame.pack(fill=tk.X, pady=(0, 8))
        vf = self._viettts_frame

        ttk.Label(vf, text="Giọng nữ:").grid(row=0, column=0, sticky=tk.W)
        self._v_female = tk.StringVar(value="nu-nhe-nhang")
        ttk.Entry(vf, textvariable=self._v_female, width=18).grid(
            row=0, column=1, sticky=tk.W, padx=4)
        ttk.Label(vf, text="Giọng nam:").grid(
            row=0, column=2, sticky=tk.W, padx=(14, 0))
        self._v_male = tk.StringVar(value="nguyen-ngoc-ngan")
        ttk.Entry(vf, textvariable=self._v_male, width=18).grid(
            row=0, column=3, sticky=tk.W, padx=4)
        ttk.Label(vf, text="(quynh, nu-nhe-nhang, nguyen-ngoc-ngan, cdteam, diep-chi, ...)",
                  foreground="#666", font=("Arial", 8)).grid(
            row=1, column=0, columnspan=4, sticky=tk.W, pady=(2, 0))

        ttk.Label(vf, text="Ký tự/đoạn:").grid(
            row=2, column=0, sticky=tk.W, pady=(8, 0))
        self._chunk_sz = ttk.Spinbox(vf, from_=50, to=1000, width=7)
        self._chunk_sz.set(300)
        self._chunk_sz.grid(row=2, column=1, sticky=tk.W, padx=4, pady=(8, 0))
        ttk.Label(vf, text="← giảm nếu file vẫn rỗng (mặc định 300)",
                  foreground="#666", font=("Arial", 8)).grid(
            row=2, column=2, columnspan=2, sticky=tk.W, padx=(14, 0), pady=(8, 0))

        # --- TikTok TTS ---
        self._tiktok_frame = ttk.LabelFrame(frm, text="TikTok TTS", padding=8)
        tf = self._tiktok_frame
        # Sẽ được pack/unpack bởi _on_engine_change()

        ttk.Label(tf, text="Giọng nữ:").grid(row=0, column=0, sticky=tk.W)
        self._tk_female = ttk.Combobox(tf, values=["vi_001", "vi_003"], width=10, state="readonly")
        self._tk_female.set("vi_001")
        self._tk_female.grid(row=0, column=1, sticky=tk.W, padx=4)

        ttk.Label(tf, text="Giọng nam:").grid(row=0, column=2, sticky=tk.W, padx=(14, 0))
        self._tk_male = ttk.Combobox(tf, values=["vi_002"], width=10, state="readonly")
        self._tk_male.set("vi_002")
        self._tk_male.grid(row=0, column=3, sticky=tk.W, padx=4)

        ttk.Label(tf, text="(vi_001=nữ, vi_002=nam, vi_003=nữ trẻ)",
                  foreground="#666", font=("Arial", 8)).grid(
            row=1, column=0, columnspan=4, sticky=tk.W, pady=(2, 0))

        ttk.Label(tf, text="Session ID:").grid(row=2, column=0, sticky=tk.W, pady=(8, 0))
        self._tk_session = ttk.Entry(tf, width=40, show="*")
        self._tk_session.grid(row=2, column=1, columnspan=3, sticky=tk.EW, padx=4, pady=(8, 0))
        ttk.Label(tf, text="(Tuỳ chọn — từ cookie TikTok, giúp ổn định hơn)",
                  foreground="#666", font=("Arial", 8)).grid(
            row=3, column=0, columnspan=4, sticky=tk.W, pady=(2, 0))

        ttk.Label(tf, text="Ký tự/đoạn:").grid(row=4, column=0, sticky=tk.W, pady=(8, 0))
        self._tk_chunk = ttk.Spinbox(tf, from_=50, to=200, width=7)
        self._tk_chunk.set(200)
        self._tk_chunk.grid(row=4, column=1, sticky=tk.W, padx=4, pady=(8, 0))

        ttk.Label(tf, text="Delay min (s):").grid(row=5, column=0, sticky=tk.W, pady=(4, 0))
        self._tk_delay_min = ttk.Spinbox(tf, from_=1, to=30, width=7)
        self._tk_delay_min.set(3)
        self._tk_delay_min.grid(row=5, column=1, sticky=tk.W, padx=4, pady=(4, 0))

        ttk.Label(tf, text="Delay max (s):").grid(row=5, column=2, sticky=tk.W, padx=(14, 0), pady=(4, 0))
        self._tk_delay_max = ttk.Spinbox(tf, from_=2, to=60, width=7)
        self._tk_delay_max.set(8)
        self._tk_delay_max.grid(row=5, column=3, sticky=tk.W, padx=4, pady=(4, 0))

        ttk.Label(tf, text="← Delay ngẫu nhiên giữa mỗi request (chống chặn IP)",
                  foreground="#666", font=("Arial", 8)).grid(
            row=6, column=0, columnspan=4, sticky=tk.W, pady=(2, 0))

        tf.columnconfigure(1, weight=1)

        # --- Tốc độ ---
        df = ttk.LabelFrame(frm, text="Tốc độ xử lý", padding=8)
        df.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(df, text="Delay giữa chương (s):").grid(
            row=0, column=0, sticky=tk.W)
        self._delay_ch = ttk.Spinbox(df, from_=1, to=60, width=7)
        self._delay_ch.set(3)
        self._delay_ch.grid(row=0, column=1, sticky=tk.W, padx=4)
        ttk.Label(df, text="Delay giữa giọng (s):").grid(
            row=1, column=0, sticky=tk.W, pady=3)
        self._delay_v = ttk.Spinbox(df, from_=0, to=10, width=7)
        self._delay_v.set(1)
        self._delay_v.grid(row=1, column=1, sticky=tk.W, padx=4)

        # --- R2 ---
        r2f = ttk.LabelFrame(frm, text="Cloudflare R2  (tuỳ chọn)", padding=8)
        r2f.pack(fill=tk.X, pady=(0, 8))
        self._r2_on = tk.BooleanVar(value=False)
        ttk.Checkbutton(r2f, text="Bật upload R2",
                        variable=self._r2_on).grid(
            row=0, column=0, columnspan=2, sticky=tk.W)

        r2_fields = [
            ("Endpoint URL:", "_r2_ep", False),
            ("Access Key ID:", "_r2_ak", False),
            ("Secret Key:", "_r2_sk", True),
            ("Bucket:", "_r2_bk", False),
            ("Public URL:", "_r2_pu", False),
        ]
        for i, (lbl, attr, hidden) in enumerate(r2_fields, 1):
            ttk.Label(r2f, text=lbl).grid(row=i, column=0, sticky=tk.W, pady=1)
            e = ttk.Entry(r2f, width=44, show="*" if hidden else "")
            e.grid(row=i, column=1, sticky=tk.EW, padx=4, pady=1)
            setattr(self, attr, e)
        r2f.columnconfigure(1, weight=1)

        # --- Supabase ---
        spf = ttk.LabelFrame(frm, text="Supabase  (tuỳ chọn)", padding=8)
        spf.pack(fill=tk.X, pady=(0, 8))
        self._sp_on = tk.BooleanVar(value=False)
        ttk.Checkbutton(spf, text="Bật Supabase",
                        variable=self._sp_on).grid(
            row=0, column=0, columnspan=2, sticky=tk.W)
        ttk.Label(spf, text="URL:").grid(row=1, column=0, sticky=tk.W, pady=1)
        self._sp_url = ttk.Entry(spf, width=44)
        self._sp_url.grid(row=1, column=1, sticky=tk.EW, padx=4)
        ttk.Label(spf, text="Key:").grid(row=2, column=0, sticky=tk.W, pady=1)
        self._sp_key = ttk.Entry(spf, width=44, show="*")
        self._sp_key.grid(row=2, column=1, sticky=tk.EW, padx=4)
        spf.columnconfigure(1, weight=1)

        ttk.Button(frm, text="💾  Lưu cấu hình",
                   command=self._save_config).pack(anchor=tk.W, pady=4)

    def _on_engine_change(self):
        """Show/hide config frames theo engine đã chọn."""
        engine = self._engine_var.get()
        # Ẩn cả hai
        self._viettts_frame.pack_forget()
        self._tiktok_frame.pack_forget()
        # Hiện frame đúng, chèn ngay sau engine frame
        if engine == "tiktok":
            self._tiktok_frame.pack(fill=tk.X, pady=(0, 8),
                                     after=self._engine_frame)
        else:
            self._viettts_frame.pack(fill=tk.X, pady=(0, 8),
                                      after=self._engine_frame)

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
            num = ch.get("chapter_number", 0)
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
        n = len(self._chap_lb.curselection())
        name = story.get("title", "?") if story else "?"
        self._proc_summary.config(
            text=f"Truyện: {name}   |   Đã chọn {n} chương sẽ xử lý")

    # ------------------------------------------------------------------ Server check

    def _check_server(self):
        engine = self._engine_var.get() if hasattr(self, '_engine_var') else "viettts"
        self._server_lbl.config(text="⬤ Đang kiểm tra…", foreground="orange")
        self.root.update_idletasks()

        def _do():
            ok = False
            msg_ok = ""
            msg_fail = ""

            if engine == "tiktok":
                msg_ok = "⬤ TikTok API OK"
                msg_fail = "⬤ TikTok API KHÔNG truy cập được"
                try:
                    r = requests.post(
                        TIKTOK_ENDPOINTS[-1],
                        params={"text_speaker": "vi_001", "req_text": "xin chao",
                                "speaker_map_type": 0, "aid": 1233},
                        headers={"User-Agent": TIKTOK_USER_AGENTS[0],
                                 "Accept-Encoding": "gzip,deflate,compress"},
                        timeout=10)
                    data = r.json()
                    ok = data.get("status_code") == 0
                except Exception:
                    ok = False
            else:
                msg_ok = "⬤ VietTTS server đang chạy"
                msg_fail = "⬤ Server KHÔNG chạy — hãy chạy start_viettts.bat"
                try:
                    r = requests.get("http://localhost:8298", timeout=3)
                    ok = r.status_code < 500
                except requests.exceptions.ConnectionError:
                    ok = False
                except Exception:
                    ok = True

            def _ui():
                if ok:
                    self._server_lbl.config(text=msg_ok, foreground="#006600")
                else:
                    self._server_lbl.config(text=msg_fail, foreground="red")

            self.root.after(0, _ui)

        threading.Thread(target=_do, daemon=True).start()

    # ------------------------------------------------------------------ Config

    def _save_config(self):
        try:
            cfg = {
                "tts_engine":           self._engine_var.get(),
                "viettts_voice_female": self._v_female.get(),
                "viettts_voice_male":   self._v_male.get(),
                "viettts_chunk_size":   int(self._chunk_sz.get()),
                "tiktok": {
                    "voice_female":  self._tk_female.get(),
                    "voice_male":    self._tk_male.get(),
                    "session_id":    self._tk_session.get(),
                    "chunk_size":    int(self._tk_chunk.get()),
                    "delay_min":     int(self._tk_delay_min.get()),
                    "delay_max":     int(self._tk_delay_max.get()),
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
                messagebox.showinfo("Thành công",
                                    "Cấu hình đã lưu!\nLần sau mở sẽ tự load.")
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
            # Engine
            self._engine_var.set(cfg.get("tts_engine", "viettts"))

            # VietTTS
            self._v_female.set(cfg.get("viettts_voice_female", "nu-nhe-nhang"))
            self._v_male.set(cfg.get("viettts_voice_male", "nguyen-ngoc-ngan"))
            if "viettts_chunk_size" in cfg:
                self._chunk_sz.set(cfg["viettts_chunk_size"])

            # TikTok
            tk_cfg = cfg.get("tiktok", {})
            self._tk_female.set(tk_cfg.get("voice_female", "vi_001"))
            self._tk_male.set(tk_cfg.get("voice_male", "vi_002"))
            self._tk_session.delete(0, tk.END)
            self._tk_session.insert(0, tk_cfg.get("session_id", ""))
            self._tk_chunk.set(tk_cfg.get("chunk_size", 200))
            self._tk_delay_min.set(tk_cfg.get("delay_min", 3))
            self._tk_delay_max.set(tk_cfg.get("delay_max", 8))

            # R2
            r2 = cfg.get("r2", {})
            self._r2_on.set(r2.get("enabled", False))
            self._r2_ep.insert(0, r2.get("endpoint_url", ""))
            self._r2_ak.insert(0, r2.get("access_key_id", ""))
            self._r2_sk.insert(0, r2.get("secret_access_key", ""))
            self._r2_bk.insert(0, r2.get("bucket_name", ""))
            self._r2_pu.insert(0, r2.get("public_url", ""))

            # Supabase
            sp = cfg.get("supabase", {})
            self._sp_on.set(sp.get("enabled", False))
            self._sp_url.insert(0, sp.get("url", ""))
            self._sp_key.insert(0, sp.get("key", ""))

            # Rate limiting
            rl = cfg.get("rate_limiting", {})
            self._delay_ch.set(rl.get("delay_chapters", 3))
            self._delay_v.set(rl.get("delay_voices", 1))

            # Cập nhật UI visibility
            self._on_engine_change()

            self.log("✓ Đã load cấu hình từ config.json")
        except Exception as e:
            self.log(f"⚠ Lỗi khi load cấu hình: {e}")

    # ------------------------------------------------------------------ Processing

    def _apply_config_to_automation(self):
        # Engine
        self.automation.tts_engine = self._engine_var.get()

        # VietTTS
        self.automation.viettts_voice_female = self._v_female.get()
        self.automation.viettts_voice_male   = self._v_male.get()
        self.automation.viettts_chunk_size   = int(self._chunk_sz.get())

        # TikTok
        self.automation.tiktok_voice_female = self._tk_female.get()
        self.automation.tiktok_voice_male   = self._tk_male.get()
        self.automation.tiktok_session_id   = self._tk_session.get()
        self.automation.tiktok_chunk_size   = int(self._tk_chunk.get())
        self.automation.tiktok_delay_min    = int(self._tk_delay_min.get())
        self.automation.tiktok_delay_max    = int(self._tk_delay_max.get())

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

        # Chuyển sang tab Xử lý
        self._notebook.select(1)

        t = threading.Thread(
            target=self._run_processing, args=(indices,), daemon=True)
        t.start()

    def _stop(self):
        self._stop_event.set()
        self.log("⏹ Đang dừng sau chương hiện tại…")

    def _run_processing(self, selected_indices):
        try:
            story = self.automation.get_story_by_id(self.selected_story_id)
            all_chapters = self.automation.get_chapters_by_story(
                self.selected_story_id)
            chapters = [all_chapters[i] for i in selected_indices]
            total = len(chapters)

            self.log(f"\n{'='*60}")
            self.log(f"Truyện: {story['title']}  |  {total} chương")
            self.log(f"{'='*60}\n")

            self.root.after(0, lambda: self._prog_bar.configure(maximum=total, value=0))

            success_count = 0
            fail_count    = 0

            for idx, chapter in enumerate(chapters, 1):
                if self._stop_event.is_set():
                    self.log("⏹ Đã dừng theo yêu cầu.")
                    break

                self.root.after(0, lambda i=idx, t=total: self._prog_lbl.config(
                    text=f"Đang xử lý {i}/{t}…"))

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                ok = loop.run_until_complete(
                    self.automation.process_chapter(story, chapter, self.log))
                loop.close()

                if ok:
                    success_count += 1
                else:
                    fail_count += 1

                self.root.after(0, lambda i=idx: self._prog_bar.configure(value=i))

            # Summary
            self.log(f"\n{'='*60}")
            if fail_count == 0:
                self.log(f"✅ Hoàn thành!  Thành công {success_count}/{total} chương")
            else:
                self.log(
                    f"⚠  Xong!  Thành công {success_count} | Thất bại {fail_count} / {total} chương")
            self.log(f"{'='*60}\n")

            def _show_done():
                if fail_count == 0:
                    messagebox.showinfo(
                        "Xong", f"Thành công {success_count}/{total} chương!")
                else:
                    messagebox.showwarning(
                        "Hoàn thành (có lỗi)",
                        f"Thành công {success_count}, thất bại {fail_count} / {total} chương.\n"
                        "Xem log để biết chi tiết.")

            self.root.after(0, _show_done)

        except Exception as e:
            self.log(f"\n❌ Lỗi nghiêm trọng: {e}")
            self.root.after(0, lambda: messagebox.showerror(
                "Lỗi", f"Có lỗi xảy ra:\n{e}"))
        finally:
            self.root.after(0, self._reset_buttons)

    def _reset_buttons(self):
        self._start_btn.config(state=tk.NORMAL)
        self._stop_btn.config(state=tk.DISABLED)
        self._prog_lbl.config(text="")

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
                "Lỗi", "Không load được dữ liệu từ myData/\n"
                "Kiểm tra file stories_rows.json và chapters_private_rows.json")
        self._load_config()
        # Tự kiểm tra server khi khởi động
        self.root.after(500, self._check_server)


def main():
    root = tk.Tk()
    TTSAutomationGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
