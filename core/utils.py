import re

def parse_srt(srt_path):
    """
    Bộ giải mã và khớp thời gian (Parser & Sync) [cite: 31]
    Chuyển đổi file SRT UTF-8 sang danh sách dữ liệu [cite: 23]
    """
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Regex để tách các đoạn phụ đề dựa trên mốc thời gian [cite: 20]
    pattern = re.compile(r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n((?:.+\n?)+)')
    matches = pattern.findall(content)
    
    subtitles = []
    for match in matches:
        subtitles.append({
            'index': match[0],
            'start': match[1],
            'end': match[2],
            'text': match[3].strip()
        })
    return subtitles