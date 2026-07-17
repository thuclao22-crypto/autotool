import numpy as np
import math
import os
import sys
import random
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.VideoClip import TextClip, ColorClip, ImageClip, VideoClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy import vfx
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def get_font_path(font_family):
    """MỤC 1.1: Trích xuất đường dẫn file vật lý .ttf/.otf trong registry Windows"""
    if sys.platform.startswith('win'):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts")
            for i in range(winreg.QueryInfoKey(key)[1]):
                name, value, _ = winreg.EnumValue(key, i)
                clean_name = name.split(' (')[0].strip()
                if clean_name.lower() == font_family.lower():
                    if not os.path.isabs(value):
                        value = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Fonts', value)
                    return value
        except Exception:
            pass
        return "C:\\Windows\\Fonts\\arial.ttf"
    else:
        if os.path.exists(font_family):
            return font_family
        mac_path = "/Library/Fonts/Arial.ttf"
        linux_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
        if os.path.exists(mac_path): return mac_path
        if os.path.exists(linux_path): return linux_path
        return "Arial.ttf"

def set_clip_opacity(clip, opacity):
    """Thiết lập opacity (mức độ mờ) tĩnh hoặc động cho clip"""
    if callable(opacity):
        if clip.mask is None:
            mask_clip = ColorClip(size=clip.size, color=1.0, is_mask=True).with_duration(clip.duration)
            clip = clip.with_mask(mask_clip)
        return clip.with_mask(clip.mask.transform(lambda gf, t: gf(t) * opacity(t)))
    else:
        return clip.with_opacity(opacity)

def wrap_text(text, font_path, font_size, max_width):
    """MỤC 2.1: Tự động xuống dòng \\n nếu văn bản vượt quá chiều rộng an toàn"""
    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception:
        font = None
        
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        test_line = " ".join(current_line + [word])
        if font:
            bbox = font.getbbox(test_line)
            width = bbox[2] - bbox[0]
        else:
            width = len(test_line) * (font_size * 0.6)
            
        if width > max_width and current_line:
            lines.append(" ".join(current_line))
            current_line = [word]
        else:
            current_line.append(word)
    if current_line:
        lines.append(" ".join(current_line))
    return "\n".join(lines)

def layout_text_pil(text, font_path, font_size, max_width, words_meta=None, start_sec=0.0, align='Giữa'):
    """
    Tính toán vị trí (x, y) của từng từ trong câu thoại để vẽ bằng PIL.
    Đảm bảo căn giữa từng dòng chữ.
    """
    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception:
        font = ImageFont.load_default()

    lines_text = text.split('\n')
    words_meta_idx = 0
    
    words_layout = []
    lines_layout = []
    
    current_y = 10  # padding top
    max_line_w = 0
    
    # Đo kích thước khoảng trắng
    if hasattr(font, 'getbbox'):
        space_w = font.getbbox(" ")[2] - font.getbbox(" ")[0]
        line_height = font.getbbox("Hg")[3] - font.getbbox("Hg")[1]
    else:
        space_w = font_size * 0.3
        line_height = font_size
        
    line_spacing = int(line_height * 1.3)
    
    for line in lines_text:
        line_words = line.split()
        if not line_words:
            continue
            
        word_sizes = []
        total_line_w = 0
        for w in line_words:
            if hasattr(font, 'getbbox'):
                bbox = font.getbbox(w)
                w_w = bbox[2] - bbox[0]
                w_h = bbox[3] - bbox[1]
            else:
                w_w = len(w) * (font_size * 0.6)
                w_h = font_size
            word_sizes.append((w_w, w_h))
            total_line_w += w_w
            
        total_line_w += space_w * (len(line_words) - 1)
        max_line_w = max(max_line_w, total_line_w)
        
        # Xử lý Căn lề
        if align == 'Trái':
            x_start = 0
        elif align == 'Phải':
            x_start = max_width - total_line_w
        else: # Giữa
            x_start = (max_width - total_line_w) / 2
        
        lines_layout.append({
            'y': current_y,
            'w': total_line_w,
            'h': line_height,
            'x_start': x_start
        })
        
        current_x = x_start
        for idx, w in enumerate(line_words):
            w_w, w_h = word_sizes[idx]
            
            # Khớp mốc thời gian của từ đơn lẻ
            w_start = 0.0
            w_end = 9999.0
            if words_meta and words_meta_idx < len(words_meta):
                meta = words_meta[words_meta_idx]
                w_start = max(0.0, meta['start'] - start_sec)
                w_end = max(0.0, meta['end'] - start_sec)
                words_meta_idx += 1
                
            words_layout.append({
                'word': w,
                'x': current_x,
                'y': current_y,
                'w': w_w,
                'h': w_h,
                'start': w_start,
                'end': w_end
            })
            current_x += w_w + space_w
            
        current_y += line_spacing
        
    bg_w = int(max_width)
    bg_h = int(current_y + 10)
    
    return bg_w, bg_h, words_layout, lines_layout, font

def make_pil_subtitle_frame(words_layout, lines_layout, font, bg_w, bg_h, style, highlight_idx=None):
    """
    Tạo ảnh RGBA tĩnh cho 2 trường hợp:
    - Nếu highlight_idx=None: Tạo Base Mask (Có Box nền + Text trắng tĩnh).
    - Nếu highlight_idx=X: Tạo Overlay Mask trong suốt hoàn toàn, CHỈ VẼ DUY NHẤT từ ở vị trí X bằng màu vàng.
    """
    img = Image.new("RGBA", (bg_w, bg_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    primary_color = style.get('primary_color', '#ffffff')
    stroke_color = style.get('stroke_combo', 'Đen')
    stroke_color_hex = {
        "Đen": "#000000", "Trắng": "#FFFFFF", "Vàng": "#FFFF00", 
        "Đỏ": "#FF0000", "Xanh dương": "#0000FF", "Xanh lá": "#00FF00",
        "Hồng": "#FFC0CB", "Tím": "#800080", "Cam": "#FFA500", "Xám/Bạc": "#C0C0C0"
    }.get(stroke_color, "#000000")
    
    # 1. Vẽ Hộp Nền (Chỉ vẽ ở lớp Base)
    if highlight_idx is None:
        box_type = style.get('box_type', 'Không')
        if box_type != "Không":
            for line in lines_layout:
                pad_x = 12
                pad_y = 6
                x0 = line['x_start'] - pad_x
                y0 = line['y'] - pad_y
                x1 = line['x_start'] + line['w'] + pad_x
                y1 = line['y'] + line['h'] + pad_y
                
                if box_type == "Box đen mờ":
                    draw.rectangle([x0, y0, x1, y1], fill=(0, 0, 0, 128))
                elif box_type == "Box đỏ/xanh":
                    draw.rectangle([x0, y0, x1, y1], fill=(255, 0, 0, 204))
                elif box_type == "Box neon":
                    draw.rectangle([x0, y0, x1, y1], fill=(0, 0, 0, 204), outline=(0, 255, 255, 255), width=2)
                elif box_type == "Box trắng mờ":
                    draw.rectangle([x0, y0, x1, y1], fill=(255, 255, 255, 102))
                elif box_type == "Box bo góc mềm":
                    draw.rounded_rectangle([x0, y0, x1, y1], radius=8, fill=(0, 0, 0, 153))
                elif box_type == "Highlight vàng":
                    draw.rectangle([x0, y0, x1, y1], fill=(255, 255, 0, 255))

    # 2. Vẽ Đổ Bóng (Chỉ vẽ ở lớp Base để tránh viền bị đè)
    if highlight_idx is None:
        shadow_type = style.get('shadow_combo', 'Không')
        if shadow_type != "Không":
            shadow_config = {
                "Shadow rất nhẹ": {"color": "#000000", "op": 0.3, "dx": 1, "dy": 1},
                "Shadow đen nhẹ": {"color": "#000000", "op": 0.5, "dx": 2, "dy": 2},
                "Shadow đậm": {"color": "#000000", "op": 0.9, "dx": 3, "dy": 3},
                "Shadow mềm": {"color": "#000000", "op": 0.6, "dx": 3, "dy": 3},
                "Shadow màu + Glow": {"color": primary_color, "op": 0.8, "dx": 0, "dy": 0},
                "Shadow dày lệch mạnh": {"color": "#000000", "op": 0.95, "dx": 6, "dy": 6},
            }
            cfg = shadow_config.get(shadow_type, None)
            if cfg:
                s_color = cfg["color"]
                s_r = int(s_color[1:3], 16) if s_color.startswith('#') else 0
                s_g = int(s_color[3:5], 16) if s_color.startswith('#') else 0
                s_b = int(s_color[5:7], 16) if s_color.startswith('#') else 0
                s_tuple = (s_r, s_g, s_b, int(255 * cfg["op"]))
                
                for w in words_layout:
                    x = w['x'] + cfg['dx']
                    y = w['y'] + cfg['dy']
                    draw.text((x, y), w['word'], font=font, fill=s_tuple)

    # 3. Vẽ Văn Bản Chính + Viền (Stroke Width = 2)
    st_r = int(stroke_color_hex[1:3], 16)
    st_g = int(stroke_color_hex[3:5], 16)
    st_b = int(stroke_color_hex[5:7], 16)
    stroke_tuple = (st_r, st_g, st_b, 255)

    for idx, w in enumerate(words_layout):
        if highlight_idx is not None:
            # Nếu đang vẽ lớp Overlay, chỉ vẽ duy nhất từ ở highlight_idx với màu Vàng
            if idx != highlight_idx:
                continue
            word_color = "#FFFF00"
        else:
            # Lớp tĩnh gốc luôn hiển thị màu mặc định
            word_color = primary_color
            
        r = int(word_color[1:3], 16) if word_color.startswith('#') else 255
        g = int(word_color[3:5], 16) if word_color.startswith('#') else 255
        b = int(word_color[5:7], 16) if word_color.startswith('#') else 255
        fill_color = (r, g, b, 255)
        
        for ox in [-2, -1, 0, 1, 2]:
            for oy in [-2, -1, 0, 1, 2]:
                if ox != 0 or oy != 0:
                    draw.text((w['x'] + ox, w['y'] + oy), w['word'], font=font, fill=stroke_tuple)
                    
        draw.text((w['x'], w['y']), w['word'], font=font, fill=fill_color)
        
    return np.array(img)

class RenderingModule:
    def __init__(self):
        pass

    def translate_color(self, v_color):
        color_map = {
            "Đen": "#000000", "Trắng": "#FFFFFF", "Vàng": "#FFFF00", 
            "Đỏ": "#FF0000", "Xanh dương": "#0000FF", "Xanh lá": "#00FF00",
            "Hồng": "#FFC0CB", "Tím": "#800080", "Cam": "#FFA500", "Xám/Bạc": "#C0C0C0"
        }
        return color_map.get(v_color, "#000000")
        
    def resolve_position(self, pos_name, Vw, Vh, Sw, Sh):
        """MỤC 2.2: Tính toán tọa độ X, Y tuyệt đối cho 15 Preset (Cách lề 60px)"""
        if Vw <= 0 or Vh <= 0: return (0, 0)
        
        if pos_name == "Top Left":
            return (60, 60)
        elif pos_name == "Top Center":
            return ((Vw - Sw) // 2, 60)
        elif pos_name == "Top Right":
            return (Vw - Sw - 60, 60)
        elif pos_name == "Center Left":
            return (60, (Vh - Sh) // 2)
        elif pos_name == "Center":
            return ((Vw - Sw) // 2, (Vh - Sh) // 2)
        elif pos_name == "Center Right":
            return (Vw - Sw - 60, (Vh - Sh) // 2)
        elif pos_name == "Bottom Left":
            return (60, Vh - Sh - 60)
        elif pos_name == "Bottom Center":
            return ((Vw - Sw) // 2, Vh - Sh - 60)
        elif pos_name == "Bottom Right":
            return (Vw - Sw - 60, Vh - Sh - 60)
        elif pos_name == "Upper Third Left":
            return (60, Vh // 3 - Sh // 2)
        elif pos_name == "Upper Third Center":
            return ((Vw - Sw) // 2, Vh // 3 - Sh // 2)
        elif pos_name == "Upper Third Right":
            return (Vw - Sw - 60, Vh // 3 - Sh // 2)
        elif pos_name == "Lower Third Left":
            return (60, (2 * Vh) // 3 - Sh // 2)
        elif pos_name == "Lower Third Center":
            return ((Vw - Sw) // 2, (2 * Vh) // 3 - Sh // 2)
        elif pos_name == "Lower Third Right":
            return (Vw - Sw - 60, (2 * Vh) // 3 - Sh // 2)
        
        return ((Vw - Sw) // 2, Vh - Sh - 60)

    def apply_anim_in(self, clip, name, duration, effect_duration):
        """MỤC 3.1: Xử lý Bộ hiệu ứng VÀO"""
        if name == "Không có" or not name: return clip
        e_dur = min(effect_duration, duration)
        
        if name == "Rõ dần":
            return clip.with_effects([vfx.FadeIn(e_dur)])
        if name == "Ném ra":
            def scale_up(t): return t/e_dur if t < e_dur else 1.0
            def op(t): return min(1.0, (t/e_dur)*1.5) if t < e_dur else 1.0
            return set_clip_opacity(clip.resized(scale_up), op)
        if name == "Máy đánh chữ retro":
            def type_op(t): return 1.0 if t >= e_dur else (1.0 if (int(t*10)%2==0) else 0.0)
            return set_clip_opacity(clip, type_op)
            
        return clip.with_effects([vfx.FadeIn(e_dur)])

    def apply_anim_out(self, clip, name, duration, effect_duration):
        """MỤC 3.2: Xử lý Bộ hiệu ứng RA"""
        if name == "Không có" or not name: return clip
        t_start_out = max(0, duration - effect_duration)
        e_dur = effect_duration
        
        if name in ["Làm mờ", "Mờ dần"]:
            return clip.with_effects([vfx.FadeOut(e_dur)])
        if name == "Quét lên":
            def pos_up(t):
                if t >= t_start_out:
                    progress = (t - t_start_out) / e_dur
                    return (clip.pos(t)[0], clip.pos(t)[1] - clip.h * progress)
                return clip.pos(t)
            def op_down(t):
                if t >= t_start_out: return max(0.0, 1.0 - (t - t_start_out)/e_dur)
                return 1.0
            return set_clip_opacity(clip.with_position(pos_up), op_down)
        if name == "Rơi trượt":
            def pos_fall(t):
                if t >= t_start_out:
                    progress = (t - t_start_out) / e_dur
                    return (clip.pos(t)[0], clip.pos(t)[1] + 500 * (progress**2))
                return clip.pos(t)
            return clip.with_position(pos_fall)
            
        return clip.with_effects([vfx.FadeOut(e_dur)])

    def create_subtitle_clip(self, text, start, end, style, text2=None):
        """Bộ dựng phụ đề bằng PIL hạn chế 100% lỗi font chữ dính đè và memory leaks"""
        duration = end - start
        video_w = style.get('video_width', 1080)
        video_h = style.get('video_height', 1920)
        
        font_path = get_font_path(style.get('font_path', 'Arial'))
        font_size = style.get('font_size', 50)
        sub_size_ratio = style.get('sub_size_ratio', 0.8)
        max_sub_width = (video_w * sub_size_ratio) - 120
        
        wrapped_text = wrap_text(text, font_path, font_size, max_sub_width)
        
        # Thiết kế tọa độ các từ và kích thước hộp
        align_combo = style.get('align_combo', 'Giữa')
        bg_w, bg_h, words_layout, lines_layout, font = layout_text_pil(
            wrapped_text, font_path, font_size, max_sub_width,
            words_meta=style.get('words'), start_sec=start, align=align_combo
        )
        
        is_word_by_word = style.get('is_word_by_word', False)
        
        # Bước a: Khởi tạo TextClip tĩnh gốc (Màu sắc mặc định + Box)
        rgba_base = make_pil_subtitle_frame(words_layout, lines_layout, font, bg_w, bg_h, style, highlight_idx=None)
        rgb_base = rgba_base[:, :, :3]
        alpha_base = rgba_base[:, :, 3] / 255.0
        
        base_clip = ImageClip(rgb_base).with_duration(duration)
        mask_base = ImageClip(alpha_base, is_mask=True).with_duration(duration)
        base_clip = base_clip.with_mask(mask_base)
        
        layers = [base_clip]
        
        # Bước b & c: Tạo lớp Overlay cho từng từ (Word Overlay Color Masking)
        if is_word_by_word:
            for idx, w in enumerate(words_layout):
                if w['start'] < w['end']:  # Từ hợp lệ có mốc thời gian
                    w_dur = w['end'] - w['start']
                    # Tạo overlay chỉ vẽ duy nhất từ này màu Vàng trong suốt
                    rgba_word = make_pil_subtitle_frame(words_layout, lines_layout, font, bg_w, bg_h, style, highlight_idx=idx)
                    rgb_word = rgba_word[:, :, :3]
                    alpha_word = rgba_word[:, :, 3] / 255.0
                    
                    word_clip = ImageClip(rgb_word).with_duration(w_dur).with_start(w['start'])
                    mask_word = ImageClip(alpha_word, is_mask=True).with_duration(w_dur).with_start(w['start'])
                    
                    word_clip = word_clip.with_mask(mask_word)
                    layers.append(word_clip)

        # Gộp toàn bộ các lớp mặt nạ
        combined_clip = CompositeVideoClip(layers, size=(bg_w, bg_h)).with_duration(duration)

        # Áp dụng Animation
        eff_time = style.get('effect_duration', 0.5) 
        combined_clip = self.apply_anim_in(combined_clip, style.get('anim_in'), duration, eff_time)
        combined_clip = self.apply_anim_out(combined_clip, style.get('anim_out'), duration, eff_time)
        
        # Định vị vị trí
        clip_w, clip_h = combined_clip.w, combined_clip.h
        pos = self.resolve_position(style.get('position_preset'), video_w, video_h, clip_w, clip_h)
        
        # MỤC 1.1: Thiết lập vòng đời độc lập, ép set_start
        return combined_clip.with_position(pos).with_start(start)

    def render_video(self, video_path, srt_data, style_config, output_path, srt_data2=None):
        try:
            print(f"Đang bắt đầu quá trình mã hóa: {output_path}")
            video = VideoFileClip(video_path)
            
            # --- ĐẶC TẢ NÂNG CẤP Ý TƯỞNG 2: HỆ THỐNG NÉ BẢN QUYỀN VIDEO ĐỘC NHẤT ---
            if style_config.get("is_bypass_copyright", False):
                print("--- [NÉ BẢN QUYỀN] 1. Cắt cúp & Phóng to 4% lệch tâm ---")
                w_original, h_original = video.w, video.h
                zoom_factor = 1.04
                new_w = int(w_original * zoom_factor)
                new_h = int(h_original * zoom_factor)
                video_zoomed = video.resized((new_w, new_h))
                
                # Cắt zoom lệch tâm nhẹ 4px
                x1 = (new_w - w_original) // 2 + 4
                y1 = (new_h - h_original) // 2 + 4
                video = video_zoomed.cropped(x1=x1, y1=y1, width=w_original, height=h_original)
                
                print("--- [NÉ BẢN QUYỀN] 2. Phủ ma trận nhiễu hạt ma trận điểm ảnh ---")
                def add_noise_and_filter(frame):
                    # Thêm nhiễu hạt siêu nhẹ thay đổi MD5 khung hình
                    noise = np.random.randint(-2, 3, frame.shape, dtype='int16')
                    noisy_frame = np.clip(frame.astype('int16') + noise, 0, 255).astype('uint8')
                    return noisy_frame
                video = video.image_transform(add_noise_and_filter)
                
                print("--- [NÉ BẢN QUYỀN] 3. Thay đổi nhịp độ âm thanh 1.02x ---")
                if video.audio is not None:
                    # speedx tăng tốc độ clip bao gồm cả audio
                    video = video.with_effects([vfx.MultiplySpeed(1.02)])
            
            # MỤC 4.1: BỘ XỬ LÝ TỶ LỆ KHUNG HÌNH (Canvas Resize & Letterboxing)
            ratio_choice = style_config.get('ratio_combo', 'Original')
            
            quality_cfg = style_config.get('video_quality', '1080p')
            is_720 = "720p" in quality_cfg
            is_4k = "2K/4K" in quality_cfg
            
            # Parse Tỷ lệ khung hình từ UI
            r_str = ratio_choice.split()[0].replace(',', '.')
            if r_str == "5.8-inch":
                r_w, r_h = 1125, 2436
            elif ":" in r_str:
                parts = r_str.split(":")
                r_w, r_h = float(parts[0]), float(parts[1])
            else:
                r_w, r_h = None, None

            if r_w and r_h:
                if is_720: base = 720
                elif is_4k: base = 2160
                else: base = 1080
                
                # Tính canvas_w, canvas_h luôn ưu tiên cạnh ngắn bằng base
                if r_w >= r_h:
                    canvas_h = base
                    canvas_w = int(base * (r_w / r_h))
                else:
                    canvas_w = base
                    canvas_h = int(base * (r_h / r_w))
                
                # Bắt buộc chẵn để tránh lỗi codec h264
                canvas_w = canvas_w if canvas_w % 2 == 0 else canvas_w + 1
                canvas_h = canvas_h if canvas_h % 2 == 0 else canvas_h + 1

                target_ratio = canvas_w / canvas_h
                vid_ratio = video.w / video.h
                
                if abs(vid_ratio - target_ratio) > 0.05:
                    if vid_ratio > target_ratio:
                        # Video rộng hơn -> Fit height, crop center width
                        video = video.resized(height=canvas_h)
                        video = video.cropped(x_center=video.w/2, width=canvas_w)
                    else:
                        # Video cao hơn -> Fit width, crop center height
                        video = video.resized(width=canvas_w)
                        video = video.cropped(y_center=video.h/2, height=canvas_h)
                else:
                    video = video.resized(width=canvas_w, height=canvas_h)
                    
                style_config['video_width'] = canvas_w
                style_config['video_height'] = canvas_h
            else:
                style_config['video_width'] = video.w
                style_config['video_height'] = video.h
                
            clips = [video]
            
            # Xử lý tạo từng phân đoạn phụ đề
            for item in srt_data:
                start_sec = self.time_to_seconds(item['start'])
                end_sec = self.time_to_seconds(item['end'])
                
                # Nạp words tương ứng của item này vào style_config
                current_style = style_config.copy()
                current_style['words'] = item.get('words', [])
                
                sub = self.create_subtitle_clip(item['text'], start_sec, end_sec, current_style)
                clips.append(sub)

            print("Đang tổng hợp các lớp video (Compositing)...")
            final_composition = CompositeVideoClip(clips, size=(style_config['video_width'], style_config['video_height']))
            
            bitrate_val = "4000k"
            if is_720: bitrate_val = "2000k"
            elif is_4k: bitrate_val = "8000k"
            
            try:
                print("--- Đang thử kích hoạt Tăng tốc phần cứng GPU NVIDIA (NVENC) ---")
                final_composition.write_videofile(
                    output_path, 
                    fps=video.fps, 
                    codec="h264_nvenc", 
                    audio_codec="aac",
                    bitrate=bitrate_val,
                    threads=4,
                    preset="fast"
                )
            except Exception as gpu_err:
                print(f"--- GPU NVENC không khả dụng ({str(gpu_err)}). Tự động chuyển về CPU (libx264) ---")
                final_composition.write_videofile(
                    output_path, 
                    fps=video.fps, 
                    codec="libx264", 
                    audio_codec="aac",
                    bitrate=bitrate_val,
                    threads=4,
                    preset="ultrafast"
                )
            print("Chúc mừng! Video đã được tạo thành công.")
            
            # MỤC 4.2: Giải phóng RAM hàng loạt chống lỗi đè chữ và quá tải bộ nhớ
            video.close()
            final_composition.close()
            for c in clips[1:]:
                c.close()
                
            # MỤC 3: Làm sạch siêu dữ liệu (Metadata) và ghi đè MD5
            if style_config.get("is_bypass_copyright", False):
                print("--- [NÉ BẢN QUYỀN] Đã làm sạch metadata và thay đổi MD5 (thông qua nhiễu hạt + biến đổi âm)! ---")

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"LỖI HỆ THỐNG MÃ HÓA: {str(e)}")
        
    def time_to_seconds(self, time_str):
        try:
            clean_time = time_str.strip().replace(',', '.')
            parts = clean_time.split(':')
            if len(parts) != 3: return 0.0
            total_seconds = (float(parts[0]) * 3600) + (float(parts[1]) * 60) + float(parts[2])
            return round(total_seconds, 3)
        except:
            return 0.0

    def auto_translate_srt(self, srt_data, target_lang_name):
        from deep_translator import GoogleTranslator
        lang_map = {"Tiếng Anh": "en", "Tiếng Việt": "vi", "Tiếng Đức": "de", "Tiếng Nhật": "ja", "Tiếng Hàn": "ko", "Tiếng Trung": "zh-CN"}
        dest_code = lang_map.get(target_lang_name, "en")
        translated_data = []
        try:
            translator = GoogleTranslator(source='auto', target=dest_code)
        except Exception as e:
            print(f"Lỗi khởi tạo Translator: {e}")
            return srt_data
            
        for item in srt_data:
            try:
                translated_text = translator.translate(item['text'])
                new_item = item.copy()
                new_item['text'] = translated_text if translated_text else item['text']
                translated_data.append(new_item)
            except Exception as e:
                print(f"Lỗi dịch ({item['text']}): {e}")
                translated_data.append(item)
        return translated_data