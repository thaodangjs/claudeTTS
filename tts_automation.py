"""
TTS Automation Tool - Chuyển đổi truyện thành audio tự động
Sử dụng Edge-TTS với giọng nam/nữ tiếng Việt
"""

import asyncio
import json
import os
import re
import time
from pathlib import Path
from typing import List, Dict, Optional
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import edge_tts
import boto3
from botocore.client import Config
from supabase import create_client, Client
from gtts import gTTS
import pyttsx3

class TTSAutomation:
    def __init__(self):
        # TTS Engine (mặc định: edge-tts)
        self.tts_engine = "edge-tts"  # edge-tts, gtts, pyttsx3
        
        # Cấu hình giọng đọc Edge-TTS tiếng Việt
        self.VOICE_MALE = "vi-VN-NamMinhNeural"
        self.VOICE_FEMALE = "vi-VN-HoaiMyNeural"
        
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
        self.delay_between_chapters = 3  # giây
        self.delay_between_voices = 1    # giây
        
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
        """Làm sạch tên file"""
        # Loại bỏ ký tự không hợp lệ
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        # Giới hạn độ dài
        if len(filename) > 100:
            filename = filename[:100]
        return filename
    
    async def generate_audio_edge_tts(self, text: str, voice: str, output_path: Path, progress_callback=None, max_retries=3):
        """Tạo audio bằng Edge-TTS"""
        for attempt in range(max_retries):
            try:
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(str(output_path))
                
                if output_path.exists() and output_path.stat().st_size > 0:
                    if progress_callback:
                        progress_callback(f"✓ Đã tạo: {output_path.name} ({output_path.stat().st_size} bytes)")
                    return True
                else:
                    raise ValueError("File không được tạo hoặc rỗng")
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    if progress_callback:
                        progress_callback(f"⚠ Lỗi (thử lại {attempt + 1}/{max_retries}): {e}")
                        progress_callback(f"⏳ Chờ {wait_time}s trước khi thử lại...")
                    await asyncio.sleep(wait_time)
                else:
                    if progress_callback:
                        progress_callback(f"✗ Lỗi Edge-TTS sau {max_retries} lần thử: {e}")
                    return False
        return False
    
    def generate_audio_gtts(self, text: str, output_path: Path, progress_callback=None):
        """Tạo audio bằng Google TTS (gTTS)"""
        try:
            # gTTS chỉ hỗ trợ giọng nữ tiếng Việt
            tts = gTTS(text=text, lang='vi', slow=False)
            tts.save(str(output_path))
            
            if output_path.exists() and output_path.stat().st_size > 0:
                if progress_callback:
                    progress_callback(f"✓ Đã tạo (gTTS): {output_path.name} ({output_path.stat().st_size} bytes)")
                return True
            return False
        except Exception as e:
            if progress_callback:
                progress_callback(f"✗ Lỗi gTTS: {e}")
            return False
    
    def generate_audio_pyttsx3(self, text: str, output_path: Path, progress_callback=None):
        """Tạo audio bằng pyttsx3 (Offline)"""
        try:
            engine = pyttsx3.init()
            engine.save_to_file(text, str(output_path))
            engine.runAndWait()
            
            if output_path.exists() and output_path.stat().st_size > 0:
                if progress_callback:
                    progress_callback(f"✓ Đã tạo (pyttsx3): {output_path.name} ({output_path.stat().st_size} bytes)")
                return True
            return False
        except Exception as e:
            if progress_callback:
                progress_callback(f"✗ Lỗi pyttsx3: {e}")
            return False
    
    async def generate_audio(self, text: str, voice: str, output_path: Path, progress_callback=None, max_retries=3):
        """Tạo file audio từ text - hỗ trợ nhiều engine"""
        # Làm sạch text
        clean_text = self.clean_text_for_tts(text)
        
        if not clean_text:
            if progress_callback:
                progress_callback(f"✗ Text rỗng sau khi làm sạch")
            return False
        
        # Chọn engine theo cấu hình
        if self.tts_engine == "edge-tts":
            return await self.generate_audio_edge_tts(clean_text, voice, output_path, progress_callback, max_retries)
        elif self.tts_engine == "gtts":
            # gTTS không cần async
            return self.generate_audio_gtts(clean_text, output_path, progress_callback)
        elif self.tts_engine == "pyttsx3":
            # pyttsx3 không cần async
            return self.generate_audio_pyttsx3(clean_text, output_path, progress_callback)
        else:
            if progress_callback:
                progress_callback(f"✗ TTS engine không hợp lệ: {self.tts_engine}")
            return False
    
    async def process_chapter(self, story: Dict, chapter: Dict, progress_callback=None):
        """Xử lý một chương: tạo audio nam/nữ, upload R2, cập nhật Supabase"""
        try:
            story_title = self.sanitize_filename(story["title"])
            chapter_num = chapter.get("chapter_number", 0)
            chapter_title = self.sanitize_filename(chapter["title"])
            
            # Tạo thư mục cho truyện
            story_dir = self.OUTPUT_DIR / story_title
            story_dir.mkdir(exist_ok=True)
            
            # Tên file: {story_slug}_chuong_{num}_{voice}.mp3
            base_filename = f"{story_title}_chuong_{chapter_num:04d}"
            male_filename = f"{base_filename}_male.mp3"
            female_filename = f"{base_filename}_female.mp3"
            
            male_path = story_dir / male_filename
            female_path = story_dir / female_filename
            
            # Lấy nội dung chương
            content = chapter.get("content", "")
            if not content:
                if progress_callback:
                    progress_callback(f"⚠ Chương {chapter_num} không có nội dung")
                return False
            
            if progress_callback:
                progress_callback(f"\n📖 Đang xử lý: {story_title} - Chương {chapter_num}")
            
            # Tạo audio giọng nam
            if progress_callback:
                progress_callback(f"🎙️ Tạo giọng nam...")
            male_success = await self.generate_audio(content, self.VOICE_MALE, male_path, progress_callback)
            
            if not male_success:
                if progress_callback:
                    progress_callback(f"⚠ Bỏ qua chương {chapter_num} do lỗi tạo audio nam")
                return False
            
            await asyncio.sleep(self.delay_between_voices)
            
            # Tạo audio giọng nữ
            if progress_callback:
                progress_callback(f"🎙️ Tạo giọng nữ...")
            female_success = await self.generate_audio(content, self.VOICE_FEMALE, female_path, progress_callback)
            
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
                
                # Kiểm tra file tồn tại trước khi upload
                if male_path.exists() and female_path.exists():
                    male_url = await self.upload_to_r2(male_path, story_title, male_filename)
                    female_url = await self.upload_to_r2(female_path, story_title, female_filename)
                    
                    if male_url and female_url:
                        if progress_callback:
                            progress_callback(f"✓ Đã upload lên R2")
                    else:
                        if progress_callback:
                            progress_callback(f"⚠ Upload R2 thất bại")
                else:
                    if progress_callback:
                        progress_callback(f"✗ File không tồn tại, bỏ qua upload R2")
            
            # Cập nhật Supabase nếu đã cấu hình
            if self.supabase_config.get("enabled") and male_url and female_url:
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
            # Kiểm tra file tồn tại
            if not file_path.exists():
                print(f"Lỗi: File không tồn tại: {file_path}")
                return None
            
            s3 = boto3.client(
                's3',
                endpoint_url=self.r2_config["endpoint_url"],
                aws_access_key_id=self.r2_config["access_key_id"],
                aws_secret_access_key=self.r2_config["secret_access_key"],
                config=Config(signature_version='s3v4')
            )
            
            # Key với prefix (S3 tự động tạo "thư mục" khi có /)
            # Ví dụ: audio/Ma_cuon_chieu/Ma_cuon_chieu_chuong_0001_male.mp3
            key = f"audio/{story_folder}/{filename}"
            
            # Upload file
            s3.upload_file(
                str(file_path),
                self.r2_config["bucket_name"],
                key,
                ExtraArgs={'ContentType': 'audio/mpeg'}
            )
            
            # Tạo URL công khai
            public_url = f"{self.r2_config['public_url']}/{key}"
            return public_url
            
        except Exception as e:
            print(f"Lỗi upload R2: {e}")
            return None
    
    async def update_supabase(self, chapter_id: str, male_url: str, female_url: str):
        """Cập nhật URL audio vào Supabase"""
        try:
            supabase: Client = create_client(
                self.supabase_config["url"],
                self.supabase_config["key"]
            )
            
            # Thêm hoặc cập nhật audio nam
            supabase.table("chapter_audios").upsert({
                "chapter_id": chapter_id,
                "voice": "male",
                "audio_url": male_url
            }, on_conflict="chapter_id,voice").execute()
            
            # Thêm hoặc cập nhật audio nữ
            supabase.table("chapter_audios").upsert({
                "chapter_id": chapter_id,
                "voice": "female",
                "audio_url": female_url
            }, on_conflict="chapter_id,voice").execute()
            
        except Exception as e:
            print(f"Lỗi cập nhật Supabase: {e}")
            raise


class TTSAutomationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("TTS Automation - Chuyển đổi truyện thành audio")
        self.root.geometry("1000x700")
        
        self.automation = TTSAutomation()
        self.selected_story_id = None
        self.selected_chapters = []
        
        self.setup_ui()
        self.load_initial_data()
    
    def setup_ui(self):
        """Thiết lập giao diện"""
        # Notebook (tabs)
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tab 1: Chọn truyện và chương
        tab_select = ttk.Frame(notebook)
        notebook.add(tab_select, text="1. Chọn truyện & chương")
        self.setup_select_tab(tab_select)
        
        # Tab 2: Cấu hình
        tab_config = ttk.Frame(notebook)
        notebook.add(tab_config, text="2. Cấu hình")
        self.setup_config_tab(tab_config)
        
        # Tab 3: Xử lý
        tab_process = ttk.Frame(notebook)
        notebook.add(tab_process, text="3. Xử lý")
        self.setup_process_tab(tab_process)
    
    def setup_select_tab(self, parent):
        """Tab chọn truyện và chương"""
        # Frame trái: Danh sách truyện
        left_frame = ttk.LabelFrame(parent, text="Danh sách truyện", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Listbox truyện
        scrollbar_stories = ttk.Scrollbar(left_frame)
        scrollbar_stories.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.stories_listbox = tk.Listbox(left_frame, yscrollcommand=scrollbar_stories.set)
        self.stories_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar_stories.config(command=self.stories_listbox.yview)
        
        self.stories_listbox.bind('<<ListboxSelect>>', self.on_story_select)
        
        # Frame phải: Danh sách chương
        right_frame = ttk.LabelFrame(parent, text="Danh sách chương", padding=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Buttons
        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(btn_frame, text="Chọn tất cả", command=self.select_all_chapters).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Bỏ chọn tất cả", command=self.deselect_all_chapters).pack(side=tk.LEFT, padx=2)
        
        # Listbox chương với checkbox
        scrollbar_chapters = ttk.Scrollbar(right_frame)
        scrollbar_chapters.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.chapters_listbox = tk.Listbox(right_frame, selectmode=tk.MULTIPLE, yscrollcommand=scrollbar_chapters.set)
        self.chapters_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar_chapters.config(command=self.chapters_listbox.yview)
    
    def setup_config_tab(self, parent):
        """Tab cấu hình R2 và Supabase"""
        # TTS Engine Selection
        tts_frame = ttk.LabelFrame(parent, text="TTS Engine (Chọn phương án chuyển giọng)", padding=10)
        tts_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(tts_frame, text="Chọn TTS Engine:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.tts_engine_var = tk.StringVar(value="edge-tts")
        
        engines = [
            ("edge-tts", "Edge-TTS (Microsoft) - Chất lượng tốt nhất, có giọng nam/nữ, dễ bị chặn IP"),
            ("gtts", "Google TTS (gTTS) - Ổn định hơn, chỉ giọng nữ, chất lượng trung bình"),
            ("pyttsx3", "pyttsx3 (Offline) - Hoàn toàn offline, chất lượng kém, giọng robot")
        ]
        
        for i, (value, label) in enumerate(engines, start=1):
            ttk.Radiobutton(
                tts_frame, 
                text=label, 
                variable=self.tts_engine_var, 
                value=value
            ).grid(row=i, column=0, columnspan=2, sticky=tk.W, pady=2, padx=20)
        
        ttk.Label(
            tts_frame, 
            text="⚠ Khuyến nghị: Edge-TTS (chính) + gTTS (dự phòng khi bị lỗi 403)",
            font=("Arial", 9, "italic"),
            foreground="#666"
        ).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=5, padx=20)
        
        # R2 Configuration
        r2_frame = ttk.LabelFrame(parent, text="Cloudflare R2 Configuration", padding=10)
        r2_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.r2_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(r2_frame, text="Bật upload lên R2", variable=self.r2_enabled).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        ttk.Label(r2_frame, text="Endpoint URL:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.r2_endpoint = ttk.Entry(r2_frame, width=50)
        self.r2_endpoint.grid(row=1, column=1, sticky=tk.EW, pady=2, padx=5)
        
        ttk.Label(r2_frame, text="Access Key ID:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.r2_access_key = ttk.Entry(r2_frame, width=50)
        self.r2_access_key.grid(row=2, column=1, sticky=tk.EW, pady=2, padx=5)
        
        ttk.Label(r2_frame, text="Secret Access Key:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.r2_secret_key = ttk.Entry(r2_frame, width=50, show="*")
        self.r2_secret_key.grid(row=3, column=1, sticky=tk.EW, pady=2, padx=5)
        
        ttk.Label(r2_frame, text="Bucket Name:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.r2_bucket = ttk.Entry(r2_frame, width=50)
        self.r2_bucket.grid(row=4, column=1, sticky=tk.EW, pady=2, padx=5)
        
        ttk.Label(r2_frame, text="Public URL:").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.r2_public_url = ttk.Entry(r2_frame, width=50)
        self.r2_public_url.grid(row=5, column=1, sticky=tk.EW, pady=2, padx=5)
        
        r2_frame.columnconfigure(1, weight=1)
        
        # Supabase Configuration
        supabase_frame = ttk.LabelFrame(parent, text="Supabase Configuration", padding=10)
        supabase_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.supabase_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(supabase_frame, text="Bật cập nhật Supabase", variable=self.supabase_enabled).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        ttk.Label(supabase_frame, text="Supabase URL:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.supabase_url = ttk.Entry(supabase_frame, width=50)
        self.supabase_url.grid(row=1, column=1, sticky=tk.EW, pady=2, padx=5)
        
        ttk.Label(supabase_frame, text="Supabase Key:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.supabase_key = ttk.Entry(supabase_frame, width=50, show="*")
        self.supabase_key.grid(row=2, column=1, sticky=tk.EW, pady=2, padx=5)
        
        supabase_frame.columnconfigure(1, weight=1)
        
        # Rate Limiting
        rate_frame = ttk.LabelFrame(parent, text="Rate Limiting (tránh bị chặn IP)", padding=10)
        rate_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(rate_frame, text="Delay giữa các chương (giây):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.delay_chapters = ttk.Spinbox(rate_frame, from_=1, to=60, width=10)
        self.delay_chapters.set(3)
        self.delay_chapters.grid(row=0, column=1, sticky=tk.W, pady=2, padx=5)
        
        ttk.Label(rate_frame, text="Delay giữa giọng nam/nữ (giây):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.delay_voices = ttk.Spinbox(rate_frame, from_=0, to=10, width=10)
        self.delay_voices.set(1)
        self.delay_voices.grid(row=1, column=1, sticky=tk.W, pady=2, padx=5)
        
        # Nút lưu cấu hình
        save_btn_frame = ttk.Frame(parent)
        save_btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(save_btn_frame, text="💾 Lưu cấu hình", command=self.save_config_to_file).pack(side=tk.LEFT, padx=5)
        ttk.Label(save_btn_frame, text="(Cấu hình sẽ được tự động load lần sau)", font=("Arial", 9, "italic")).pack(side=tk.LEFT, padx=5)
    
    def setup_process_tab(self, parent):
        """Tab xử lý"""
        # Info frame
        info_frame = ttk.Frame(parent)
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.info_label = ttk.Label(info_frame, text="Chưa chọn truyện", font=("Arial", 10, "bold"))
        self.info_label.pack(anchor=tk.W)
        
        # Progress
        progress_frame = ttk.Frame(parent)
        progress_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(progress_frame, text="Tiến độ:").pack(anchor=tk.W)
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        self.progress_label = ttk.Label(progress_frame, text="0/0 chương")
        self.progress_label.pack(anchor=tk.W)
        
        # Log
        log_frame = ttk.LabelFrame(parent, text="Log", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=20, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Buttons
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.start_btn = ttk.Button(btn_frame, text="🚀 Bắt đầu xử lý", command=self.start_processing)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="⏹ Dừng", command=self.stop_processing, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="🗑️ Xóa log", command=self.clear_log).pack(side=tk.LEFT, padx=5)
    
    def load_initial_data(self):
        """Load dữ liệu ban đầu và cấu hình"""
        if self.automation.load_data():
            self.populate_stories()
            self.log("✓ Đã load dữ liệu thành công")
        else:
            messagebox.showerror("Lỗi", "Không thể load dữ liệu từ myData/")
        
        # Tự động load cấu hình nếu có
        self.load_config_from_file()
    
    def populate_stories(self):
        """Hiển thị danh sách truyện"""
        self.stories_listbox.delete(0, tk.END)
        for story in self.automation.stories:
            title = story.get("title", "Không có tên")
            self.stories_listbox.insert(tk.END, title)
    
    def on_story_select(self, event):
        """Khi chọn truyện"""
        selection = self.stories_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        story = self.automation.stories[index]
        self.selected_story_id = story["id"]
        
        # Load chapters
        chapters = self.automation.get_chapters_by_story(self.selected_story_id)
        self.chapters_listbox.delete(0, tk.END)
        
        for chapter in chapters:
            chapter_num = chapter.get("chapter_number", 0)
            chapter_title = chapter.get("title", "Không có tên")
            self.chapters_listbox.insert(tk.END, f"Chương {chapter_num}: {chapter_title}")
        
        self.update_info_label()
    
    def select_all_chapters(self):
        """Chọn tất cả chương"""
        self.chapters_listbox.select_set(0, tk.END)
    
    def deselect_all_chapters(self):
        """Bỏ chọn tất cả chương"""
        self.chapters_listbox.select_clear(0, tk.END)
    
    def update_info_label(self):
        """Cập nhật thông tin"""
        if not self.selected_story_id:
            self.info_label.config(text="Chưa chọn truyện")
            return
        
        story = self.automation.get_story_by_id(self.selected_story_id)
        chapters = self.automation.get_chapters_by_story(self.selected_story_id)
        
        text = f"Truyện: {story['title']} | Tổng số chương: {len(chapters)}"
        self.info_label.config(text=text)
    
    def log(self, message):
        """Ghi log"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def clear_log(self):
        """Xóa log"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def start_processing(self):
        """Bắt đầu xử lý"""
        # Validate
        if not self.selected_story_id:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn truyện")
            return
        
        selected_indices = self.chapters_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn ít nhất một chương")
            return
        
        # Lấy cấu hình
        self.automation.r2_config = {
            "enabled": self.r2_enabled.get(),
            "endpoint_url": self.r2_endpoint.get(),
            "access_key_id": self.r2_access_key.get(),
            "secret_access_key": self.r2_secret_key.get(),
            "bucket_name": self.r2_bucket.get(),
            "public_url": self.r2_public_url.get()
        }
        
        self.automation.supabase_config = {
            "enabled": self.supabase_enabled.get(),
            "url": self.supabase_url.get(),
            "key": self.supabase_key.get()
        }
        
        self.automation.delay_between_chapters = int(self.delay_chapters.get())
        self.automation.delay_between_voices = int(self.delay_voices.get())
        
        # Áp dụng TTS engine đã chọn
        self.automation.tts_engine = self.tts_engine_var.get()
        
        # Disable buttons
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        # Start processing in thread
        self.processing_thread = threading.Thread(target=self.process_chapters, args=(selected_indices,))
        self.processing_thread.start()
    
    def process_chapters(self, selected_indices):
        """Xử lý các chương đã chọn"""
        try:
            story = self.automation.get_story_by_id(self.selected_story_id)
            all_chapters = self.automation.get_chapters_by_story(self.selected_story_id)
            
            selected_chapters = [all_chapters[i] for i in selected_indices]
            total = len(selected_chapters)
            
            self.log(f"\n{'='*60}")
            self.log(f"Bắt đầu xử lý {total} chương của truyện: {story['title']}")
            self.log(f"{'='*60}\n")
            
            # Update progress bar
            self.progress_bar['maximum'] = total
            self.progress_bar['value'] = 0
            
            # Process each chapter
            for idx, chapter in enumerate(selected_chapters, 1):
                self.progress_label.config(text=f"{idx}/{total} chương")
                
                # Run async function
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    self.automation.process_chapter(story, chapter, self.log)
                )
                loop.close()
                
                # Update progress
                self.progress_bar['value'] = idx
                self.root.update_idletasks()
            
            self.log(f"\n{'='*60}")
            self.log(f"✅ Hoàn thành! Đã xử lý {total} chương")
            self.log(f"{'='*60}\n")
            
            messagebox.showinfo("Thành công", f"Đã xử lý xong {total} chương!")
            
        except Exception as e:
            self.log(f"\n❌ Lỗi: {e}")
            messagebox.showerror("Lỗi", f"Có lỗi xảy ra: {e}")
        
        finally:
            # Re-enable buttons
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
    
    def stop_processing(self):
        """Dừng xử lý"""
        # TODO: Implement stop logic
        messagebox.showinfo("Thông báo", "Tính năng dừng đang được phát triển")
    
    def save_config_to_file(self):
        """Lưu cấu hình hiện tại vào file"""
        try:
            config = {
                "tts_engine": self.tts_engine_var.get(),
                "r2": {
                    "enabled": self.r2_enabled.get(),
                    "endpoint_url": self.r2_endpoint.get(),
                    "access_key_id": self.r2_access_key.get(),
                    "secret_access_key": self.r2_secret_key.get(),
                    "bucket_name": self.r2_bucket.get(),
                    "public_url": self.r2_public_url.get()
                },
                "supabase": {
                    "enabled": self.supabase_enabled.get(),
                    "url": self.supabase_url.get(),
                    "key": self.supabase_key.get()
                },
                "rate_limiting": {
                    "delay_chapters": int(self.delay_chapters.get()),
                    "delay_voices": int(self.delay_voices.get())
                }
            }
            
            if self.automation.save_config(config):
                messagebox.showinfo("Thành công", "Cấu hình đã được lưu!\nLần sau mở phần mềm sẽ tự động load.")
                self.log("💾 Đã lưu cấu hình vào config.json")
            else:
                messagebox.showerror("Lỗi", "Không thể lưu cấu hình")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi khi lưu cấu hình: {e}")
    
    def load_config_from_file(self):
        """Load cấu hình từ file và điền vào form"""
        config = self.automation.load_config()
        if config:
            try:
                # Load TTS engine
                if "tts_engine" in config:
                    self.tts_engine_var.set(config.get("tts_engine", "edge-tts"))
                
                # Load R2 config
                if "r2" in config:
                    self.r2_enabled.set(config["r2"].get("enabled", False))
                    self.r2_endpoint.insert(0, config["r2"].get("endpoint_url", ""))
                    self.r2_access_key.insert(0, config["r2"].get("access_key_id", ""))
                    self.r2_secret_key.insert(0, config["r2"].get("secret_access_key", ""))
                    self.r2_bucket.insert(0, config["r2"].get("bucket_name", ""))
                    self.r2_public_url.insert(0, config["r2"].get("public_url", ""))
                
                # Load Supabase config
                if "supabase" in config:
                    self.supabase_enabled.set(config["supabase"].get("enabled", False))
                    self.supabase_url.insert(0, config["supabase"].get("url", ""))
                    self.supabase_key.insert(0, config["supabase"].get("key", ""))
                
                # Load rate limiting
                if "rate_limiting" in config:
                    self.delay_chapters.set(config["rate_limiting"].get("delay_chapters", 3))
                    self.delay_voices.set(config["rate_limiting"].get("delay_voices", 1))
                
                self.log("✓ Đã load cấu hình từ config.json")
            except Exception as e:
                self.log(f"⚠ Lỗi khi load cấu hình: {e}")


def main():
    root = tk.Tk()
    app = TTSAutomationGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
