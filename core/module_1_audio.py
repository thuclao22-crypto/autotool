import os
import math
import re
import json
import torch
import shutil
import tempfile
from faster_whisper import WhisperModel

class TranscriptionModule:
    def __init__(self, model_size="base"):
        """
        Khởi tạo Module 1 với mô hình Faster-Whisper.
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if self.device == "cuda" else "int8"
        print(f"[Hardware Acceleration] Faster-Whisper AI đang chạy trên thiết bị: {self.device.upper()} với compute_type: {compute_type}")
        self.model = WhisperModel(model_size, device=self.device, compute_type=compute_type)

    def format_time(self, seconds):
        """Chuyển đổi giây (float) sang định dạng SRT: HH:MM:SS,mmm"""
        ms = int((seconds - math.floor(seconds)) * 1000)
        s = int(math.floor(seconds))
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    def write_srt(self, formatted_srt_list, srt_path):
        """Hàm ghi file SRT từ list JSON"""
        with open(srt_path, "w", encoding="utf-8") as f:
            for idx, item in enumerate(formatted_srt_list, 1):
                f.write(f"{idx}\n")
                f.write(f"{item['start']} --> {item['end']}\n")
                f.write(f"{item['text']}\n\n")

    def extract_temp_audio(self, video_path, output_dir):
        """Trích xuất audio từ video để gửi lên Cloud API, tiết kiệm băng thông và tăng tốc độ"""
        try:
            from moviepy.video.io.VideoFileClip import VideoFileClip
            audio_path = os.path.join(output_dir, "temp_audio_api.mp3")
            with VideoFileClip(video_path) as clip:
                if clip.audio is not None:
                    clip.audio.write_audiofile(audio_path, logger=None, bitrate="64k")
                    return audio_path
        except Exception as e:
            print(f"[Extract Audio] Lỗi: {e}")
        return video_path # Fallback

    def transcribe(self, video_path, output_dir="outputs", selected_lang="Tự động nhận diện", gemini_key="", openai_key="", word_timestamps=True):
        if gemini_key:
            active_cloud_api = "Gemini"
            active_api_key = gemini_key
            print("--- [API LAI] Kích hoạt: Google Gemini AI (Audio Native) ---")
        elif openai_key:
            active_cloud_api = "OpenAI"
            active_api_key = openai_key
            print("--- [API LAI] Kích hoạt: OpenAI Whisper API (Audio Native) ---")
        else:
            active_cloud_api = None
            active_api_key = None
            print("--- [API LAI] Chế độ Offline: Sử dụng Faster-Whisper Local 100% ---")

        lang_map = {
            "Tiếng Việt": "vi", "Tiếng Anh": "en", "Tiếng Đức": "de", "Tiếng Nhật": "ja",
            "Tiếng Hàn": "ko", "Tiếng Trung": "zh", "Tự động nhận diện": None
        }
        whisper_lang = lang_map.get(selected_lang)

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        print(f"--- Đang bắt đầu xử lý: {video_path} ---")
        video_filename = os.path.basename(video_path).split('.')[0]
        srt_path = os.path.join(output_dir, f"{video_filename}.srt")
        
        api_error = False
        error_detail = ""
        result_segments = []
        detected_lang = whisper_lang

        # PHẦN 1: GỌI CLOUD API NẾU CÓ
        if active_cloud_api == "OpenAI":
            print(f"--- [OpenAI] Gửi trực tiếp Audio lên Cloud để nhận diện... ---")
            audio_path = self.extract_temp_audio(video_path, output_dir)
            try:
                from openai import OpenAI
                client = OpenAI(api_key=active_api_key)
                with open(audio_path, "rb") as audio_file:
                    response = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="verbose_json",
                        timestamp_granularities=["word", "segment"]
                    )
                detected_lang = response.language
                
                for seg in response.segments:
                    if isinstance(seg, dict):
                        seg_start = seg['start']
                        seg_end = seg['end']
                        seg_text = seg['text']
                        words_list = seg.get('words', [])
                    else:
                        seg_start = seg.start
                        seg_end = seg.end
                        seg_text = seg.text
                        words_list = seg.words if hasattr(seg, 'words') else []

                    # Convert words to dict format
                    clean_words = []
                    for w in words_list:
                        if isinstance(w, dict):
                            clean_words.append({"word": w["word"], "start": w["start"], "end": w["end"]})
                        else:
                            clean_words.append({"word": w.word, "start": w.start, "end": w.end})
                            
                    result_segments.append({
                        "start": seg_start,
                        "end": seg_end,
                        "text": seg_text,
                        "words": clean_words
                    })
                
            except Exception as e:
                print(f"[OpenAI API] Lỗi: {e}")
                api_error = True
                error_detail = str(e)
            
            if audio_path != video_path and os.path.exists(audio_path):
                try: os.remove(audio_path)
                except: pass

        elif active_cloud_api == "Gemini":
            print(f"--- [Gemini] Gửi trực tiếp Audio lên Cloud để nhận diện (Thử nghiệm)... ---")
            audio_path = self.extract_temp_audio(video_path, output_dir)
            try:
                import google.generativeai as genai
                genai.configure(api_key=active_api_key)
                
                # Cần upload_file
                import time
                audio_file = genai.upload_file(audio_path)
                
                # Polling chờ file xử lý xong bên máy chủ Gemini
                start_time = time.time()
                while audio_file.state.name == "PROCESSING":
                    if time.time() - start_time > 60:
                        raise Exception("Timeout khi chờ Gemini xử lý file audio (vượt quá 60s).")
                    time.sleep(2)
                    audio_file = genai.get_file(audio_file.name)
                
                if audio_file.state.name == "FAILED":
                    raise Exception("Gemini xử lý file audio thất bại (Trạng thái: FAILED).")
                    
                model = genai.GenerativeModel('gemini-flash-latest')
                prompt = (
                    "Please transcribe this audio. Output ONLY a valid JSON object with two keys: "
                    "'detected_language' (string, ISO 639-1 code like 'vi', 'en', 'ja') and "
                    "'segments' (an array of objects). Each object in 'segments' must have: "
                    "'start' (float seconds), 'end' (float seconds), 'text' (string sentence), "
                    "and 'words' (array of objects with 'start', 'end', 'word'). Do your best to estimate word timestamps. Output nothing but JSON."
                )
                response = model.generate_content([prompt, audio_file])
                
                raw_json = response.text.replace("```json", "").replace("```", "").strip()
                parsed_json = json.loads(raw_json)
                
                if isinstance(parsed_json, dict) and "segments" in parsed_json:
                    segments_json = parsed_json["segments"]
                    if "detected_language" in parsed_json and parsed_json["detected_language"]:
                        detected_lang = parsed_json["detected_language"]
                else:
                    segments_json = parsed_json # Đề phòng model trả thẳng về Array
                
                for seg in segments_json:
                    result_segments.append({
                        "start": seg["start"],
                        "end": seg["end"],
                        "text": seg["text"],
                        "words": seg.get("words", [])
                    })
            except Exception as e:
                print(f"[Gemini API] Lỗi: {e}")
                api_error = True
                error_detail = str(e)
            
            if audio_path != video_path and os.path.exists(audio_path):
                try: os.remove(audio_path)
                except: pass

        # PHẦN 2: CHẠY OFFLINE FASTER-WHISPER NẾU KHÔNG CÓ API HOẶC BỊ LỖI
        if active_cloud_api is None or api_error:
            print("--- [Whisper Local] Đang nhận diện âm thanh bằng Faster-Whisper... ---")
            # Thiết lập bias decoder
            initial_prompt = "Đây là một đoạn phụ đề tiếng Việt với đầy đủ dấu câu, viết hoa đầu dòng." if selected_lang in ["Tiếng Việt", "Tự động nhận diện"] else None
            
            segments, info = self.model.transcribe(
                video_path,
                language=whisper_lang,
                word_timestamps=word_timestamps,
                condition_on_previous_text=True,
                initial_prompt=initial_prompt,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500)
            )
            detected_lang = info.language
            print(f"--- [LID] Nhận diện ngôn ngữ: '{detected_lang}' (xác suất: {info.language_probability:.2%}) ---")

            for segment in segments:
                words_list = []
                if word_timestamps and segment.words:
                    for w in segment.words:
                        words_list.append({
                            "word": w.word,
                            "start": w.start,
                            "end": w.end
                        })
                result_segments.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text,
                    "words": words_list
                })

        # PHẦN 3: LÀM SẠCH VÀ BĂM NHỎ SRT
        formatted_srt_list = []
        for segment in result_segments:
            raw_text = segment['text']
            cleaned_text = self.clean_vietnamese_text(raw_text)
            words_list = segment.get('words', [])
            
            sub_texts, sub_words_lists = self.split_vietnamese_segments_with_words(cleaned_text, max_words=5, words_list=words_list)
            
            seg_start = segment['start']
            seg_end = segment['end']
            seg_duration = seg_end - seg_start
            num_subs = len(sub_texts)
            
            for s_idx, sub_text in enumerate(sub_texts):
                sub_words = sub_words_lists[s_idx] if s_idx < len(sub_words_lists) else []
                if sub_words:
                    s_t = sub_words[0]['start']
                    e_t = sub_words[-1]['end']
                else:
                    sub_duration = seg_duration / num_subs if num_subs > 0 else 0
                    s_t = seg_start + s_idx * sub_duration
                    e_t = s_t + sub_duration
                
                clean_sub_words = []
                for w in sub_words:
                    clean_sub_words.append({
                        'word': w['word'].strip(),
                        'start': w['start'],
                        'end': w['end']
                    })
                
                formatted_srt_list.append({
                    'start': self.format_time(s_t), 
                    'end': self.format_time(e_t),
                    'text': sub_text,
                    'words': clean_sub_words
                })

        print(f"--- Hoàn thành! Đã trích xuất {len(formatted_srt_list)} câu phụ đề ---")
        
        # Tạo file SRT
        self.write_srt(formatted_srt_list, srt_path)
        
        return srt_path, detected_lang, formatted_srt_list, api_error, error_detail

    def split_vietnamese_segments_with_words(self, text, max_words=5, words_list=None):
        words = text.split()
        if len(words) <= max_words:
            return [text], [words_list] if words_list else [[]]
        
        segments = []
        segments_words = []
        for i in range(0, len(words), max_words):
            segment_words = words[i:i+max_words]
            segments.append(" ".join(segment_words))
            if words_list:
                segments_words.append(words_list[i:i+max_words])
            else:
                segments_words.append([])
        return segments, segments_words

    def clean_vietnamese_text(self, text):
        vietnamese_corrections = {
            "thủ vếi": "về ai",
            "cuộc tôi": "cuộc đời tôi",
            "đơn cối": "đơn côi",
            "ghìên": "ghiền",
            "mì gõ": "Mì Gõ",
            "subscribe": "Đăng ký",
            "chanel": "kênh"
        }
        text_lower = text.lower()
        for wrong, right in vietnamese_corrections.items():
            if wrong in text_lower:
                text = re.sub(re.escape(wrong), right, text, flags=re.IGNORECASE)
                text_lower = text.lower()
            
        num_words_map = {
            "hai mươi mốt": "21", "hai mươi hai": "22", "hai mươi ba": "23", "hai mươi tư": "24", 
            "hai mươi lăm": "25", "hai mươi sáu": "26", "hai mươi bảy": "27", "hai mươi tám": "28", "hai mươi chín": "29",
            "ba mươi mốt": "31", "ba mươi hai": "32", "ba mươi ba": "33", "ba mươi tư": "34",
            "ba mươi lăm": "35", "ba mươi sáu": "36", "ba mươi bảy": "37", "ba mươi tám": "38", "ba mươi chín": "39",
            "bốn mươi mốt": "41", "bốn mươi hai": "42", "bốn mươi ba": "43", "bốn mươi tư": "44",
            "bốn mươi lăm": "45", "bốn mươi sáu": "46", "bốn mươi bảy": "47", "bốn mươi tám": "48", "bốn mươi chín": "49",
            "năm mươi mốt": "51", "năm mươi hai": "52", "năm mươi ba": "53", "năm mươi tư": "54",
            "năm mươi lăm": "55", "năm mươi sáu": "56", "năm mươi bảy": "57", "năm mươi tám": "58", "năm mươi chín": "59",
            "sáu mươi mốt": "61", "sáu mươi hai": "62", "sáu mươi ba": "63", "sáu mươi tư": "64",
            "sáu mươi lăm": "65", "sáu mươi sáu": "66", "sáu mươi bảy": "67", "sáu mươi tám": "68", "sáu mươi chín": "69",
            "bảy mươi mốt": "71", "bảy mươi hai": "72", "bảy mươi ba": "73", "bảy mươi tư": "74",
            "bảy mươi lăm": "75", "bảy mươi sáu": "76", "bảy mươi bảy": "77", "bảy mươi tám": "78", "bảy mươi chín": "79",
            "tám mươi mốt": "81", "tám mươi hai": "82", "tám mươi ba": "83", "tám mươi tư": "84",
            "tám mươi lăm": "85", "tám mươi sáu": "86", "tám mươi bảy": "87", "tám mươi tám": "88", "tám mươi chín": "89",
            "chín mươi mốt": "91", "chín mươi hai": "92", "chín mươi ba": "93", "chín mươi tư": "94",
            "chín mươi lăm": "95", "chín mươi sáu": "96", "chín mươi bảy": "97", "chín mươi tám": "98", "chín mươi chín": "99",
            "mười một": "11", "mười hai": "12", "mười ba": "13", "mười tư": "14", "mười lăm": "15",
            "mười sáu": "16", "mười bảy": "17", "mười tám": "18", "mười chín": "19",
            "hai mươi": "20", "ba mươi": "30", "bốn mươi": "40", "năm mươi": "50", "sáu mươi": "60",
            "bảy mươi": "70", "tám mươi": "80", "chín mươi": "90",
            "mười": "10"
        }
        for phrase, num_str in num_words_map.items():
            pattern = re.compile(rf'(?<!\w){phrase}(?!\w)', flags=re.IGNORECASE)
            text = pattern.sub(num_str, text)
            
        single_num_map = {
            "không": "0", "một": "1", "hai": "2", "ba": "3", "bốn": "4", "năm": "5",
            "sáu": "6", "bảy": "7", "tám": "8", "chín": "9"
        }
        context_words = ["số", "khoảng", "gần", "hơn", "được", "phút", "giờ", "giây", "ngày", "tháng", "%", "lúc"]
        for phrase, num_str in single_num_map.items():
            for ctx in context_words:
                pattern = re.compile(rf'(?<!\w)({ctx})\s+{phrase}(?!\w)', flags=re.IGNORECASE)
                text = pattern.sub(rf'\g<1> {num_str}', text)
                
        # Nâng cấp: Chuẩn hóa khoảng trắng thừa
        text = re.sub(r'\s+', ' ', text).strip()
        # Nâng cấp: Chuẩn hóa dấu câu dính chữ (thêm khoảng trắng sau dấu câu)
        text = re.sub(r'([.?!,])([^\s])', r'\1 \2', text)
        
        # Viết hoa chữ cái đầu tiên nếu đang là chữ thường (không hạ phần còn lại)
        if len(text) > 0 and text[0].islower():
            text = text[0].upper() + text[1:]
            
        # Viết hoa sau các dấu kết thúc câu (không hạ phần còn lại)
        def capitalize_match(match):
            return match.group(1) + match.group(2).upper()
        text = re.sub(r'([.?!]\s+)([a-zà-ỹ])', capitalize_match, text)
            
        return text

if __name__ == "__main__":
    pass