import cv2
import pytesseract
import numpy as np
import re
import xml.etree.ElementTree as ET
from src.logger import log

class VisionEngine:
    def __init__(self):
        self.is_last_screen_ad = False

    def find_targets_from_xml(self, xml_data, target_keywords):
        """
        [Invincible XML Mode]
        UI XML 데이터를 분석하여 키워드에 맞는 엘리먼트의 좌표를 반환합니다.
        """
        if not xml_data: return []
        targets = []
        try:
            # XML 파싱 (가끔 인코딩 이슈가 있어 처리가 필요할 수 있음)
            root = ET.fromstring(xml_data)
            
            all_found_labels = [] # 디버깅용: 발견된 모든 텍스트 저장

            for node in root.iter():
                text = node.attrib.get('text', '')
                desc = node.attrib.get('content-desc', '')
                # 글자나 설명 중 하나라도 있으면 검사
                label = text if text else desc
                if not label: continue
                
                # [필터링] 유효한 문자(한글/영문/숫자/기호)가 적어도 하나는 있어야 함
                # 외계어(알 수 없는 유니코드)만 있는 경우 무시
                if not re.search(r'[a-zA-Z0-9가-힣]', label):
                    continue

                # [수정] 생략 없이 모든 텍스트 원본 저장
                all_found_labels.append(label)

                # 특수문자 제거 후 비교
                clean_label = re.sub(r'[^a-zA-Z0-9가-힣P]', '', label).lower()
                
                matched = False
                # P, 금 패턴 매칭
                if re.search(r'\d+p', clean_label) or re.search(r'\d+금', clean_label) or clean_label in ['p', '금']:
                    matched = True
                else:
                    for kw in target_keywords:
                        ck = re.sub(r'[^a-zA-Z0-9가-힣P]', '', kw).lower()
                        if ck and ck in clean_label:
                            matched = True; break
                
                if matched:
                    # bounds="[x1,y1][x2,y2]" 파싱
                    bounds = node.attrib.get('bounds', '')
                    match = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
                    if match:
                        x1, y1, x2, y2 = map(int, match.groups())
                        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                        targets.append((cx, cy, label, "XML"))
            
            # [디버그] 화면에서 읽은 모든 텍스트 출력 (생략 없음)
            if all_found_labels:
                log.info(f"[XML View] Raw Text Dump ({len(all_found_labels)} items): {all_found_labels}")
                
        except Exception as e:
            log.error(f"Vision: XML Parsing Error -> {e}")
            
        return targets

    def find_targets(self, image_path, target_keywords, app_name=None):
        """
        [Smart Line Merging Mode]
        Tesseract의 Line 정보를 활용하여 쪼개진 글자들을 정확하게 합칩니다.
        """
        targets = []
        img = cv2.imread(image_path)
        if img is None: return []

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape[:2]

        # 1. 템플릿(이미지) 매칭 (생략 없이 유지)
        import os
        template_dir = "assets/templates"
        if app_name:
            app_dir = os.path.join(template_dir, app_name)
            if os.path.exists(app_dir):
                template_dir = app_dir
        
        if os.path.exists(template_dir):
            for filename in os.listdir(template_dir):
                if not filename.endswith(".png"): continue
                path = os.path.join(template_dir, filename)
                template = cv2.imread(path, 0)
                if template is None: continue
                
                for scale in np.linspace(0.7, 1.3, 10)[::-1]:
                    try:
                        resized = cv2.resize(template, None, fx=scale, fy=scale)
                        if resized.shape[0] > h or resized.shape[1] > w: continue
                        res = cv2.matchTemplate(gray, resized, cv2.TM_CCOEFF_NORMED)
                        loc = np.where(res >= 0.75) 
                        rw, rh = resized.shape[::-1]
                        for pt in zip(*loc[::-1]):
                            cx, cy = pt[0] + rw // 2, pt[1] + rh // 2
                            if not any(abs(t[0]-cx) < 30 and abs(t[1]-cy) < 30 for t in targets):
                                targets.append((cx, cy, filename, "IMAGE"))
                    except: pass

        # 2. OCR 및 지능형 줄 단위 병합
        def get_merged_ocr(input_img, area_scale=1.0, offset_x=0, offset_y=0):
            custom_config = r'--oem 3 --psm 11'
            try:
                data = pytesseract.image_to_data(input_img, lang='kor+eng', config=custom_config, output_type=pytesseract.Output.DICT)
                
                # 줄(Line) 단위로 묶기 위한 딕셔너리
                # 키: (block_num, par_num, line_num)
                lines = {}
                
                for i in range(len(data['text'])):
                    text = data['text'][i].strip()
                    conf = int(data['conf'][i])
                    if not text or conf < 30: continue
                    
                    key = (data['block_num'][i], data['par_num'][i], data['line_num'][i])
                    if key not in lines:
                        lines[key] = []
                    
                    lines[key].append({
                        "text": text,
                        "left": data['left'][i],
                        "top": data['top'][i],
                        "width": data['width'][i],
                        "height": data['height'][i]
                    })
                
                # 각 줄별로 병합 수행
                all_ocr_lines = []
                for key, words in lines.items():
                    # X좌표 순서대로 정렬
                    words.sort(key=lambda x: x['left'])
                    
                    # 단어들을 하나로 합침
                    full_line_text = ""
                    min_l = words[0]['left']
                    max_r = words[-1]['left'] + words[-1]['width']
                    min_t = min(w['top'] for w in words)
                    max_b = max(w['top'] + w['height'] for w in words)
                    
                    for i, w in enumerate(words):
                        if i > 0:
                            prev_r = words[i-1]['left'] + words[i-1]['width']
                            if (w['left'] - prev_r) > 15:
                                full_line_text += " "
                        full_line_text += w['text']
                    
                    all_ocr_lines.append(full_line_text)
                    
                    # 매칭 검사
                    clean_text = re.sub(r'[^a-zA-Z0-9가-힣P]', '', full_line_text).lower()
                    if not clean_text: continue
                    
                    matched = False
                    if re.search(r'\d+p', clean_text) or re.search(r'\d+금', clean_text): matched = True
                    elif clean_text in ['p', '금']: matched = True
                    else:
                        for kw in target_keywords:
                            ck = re.sub(r'[^a-zA-Z0-9가-힣P]', '', kw).lower()
                            if ck and ck in clean_text:
                                matched = True; break
                    
                    if matched:
                        cx = int((min_l + (max_r - min_l) // 2) / area_scale) + offset_x
                        cy = int((min_t + (max_b - min_t) // 2) / area_scale) + offset_y
                        if not any(abs(t[0]-cx) < 35 and abs(t[1]-cy) < 35 for t in targets):
                            targets.append((cx, cy, full_line_text, "TEXT"))
                
                # [디버그] OCR로 읽은 모든 텍스트 출력
                if all_ocr_lines:
                    # 외계어 필터링하여 로그 출력
                    clean_ocr = [line for line in all_ocr_lines if re.search(r'[a-zA-Z0-9가-힣]', line)]
                    if clean_ocr:
                        log.info(f"[OCR View] Clean Text Dump ({len(clean_ocr)} lines): {clean_ocr}")
                    
                    # [광고 감지] 외계어(정크) 비율이 70% 이상이면 광고로 의심
                    junk_count = len(all_ocr_lines) - len(clean_ocr)
                    if len(all_ocr_lines) >= 5 and (junk_count / len(all_ocr_lines)) > 0.7:
                        log.warning(f"Vision: High junk density detected ({junk_count}/{len(all_ocr_lines)}). Possible AD.")
                        self.is_last_screen_ad = True
                    else:
                        self.is_last_screen_ad = False
                else:
                    self.is_last_screen_ad = False
                    
            except Exception as e:
                log.error(f"OCR Error: {e}")
                self.is_last_screen_ad = False

        # [최적화 1] 원본 전체 스캔 (1.0x) - 기본 수행
        get_merged_ocr(gray, area_scale=1.0)

        # [최적화 2] 아무것도 못 찾았을 때만 추가 정밀 수색 진행
        if not targets:
            # 0.3배 축소 스캔 (큰 글씨용)
            gray_small = cv2.resize(gray, None, fx=0.3, fy=0.3, interpolation=cv2.INTER_AREA)
            get_merged_ocr(gray_small, area_scale=0.3)
            
            # 그래도 없으면 4등분 스캔
            if not targets:
                mid_h, mid_w = h // 2, w // 2
                tiles = [
                    (gray[0:mid_h, 0:mid_w], 0, 0),
                    (gray[0:mid_h, mid_w:w], mid_w, 0),
                    (gray[mid_h:h, 0:mid_w], 0, mid_h),
                    (gray[mid_h:h, mid_w:w], mid_w, mid_h)
                ]
                for tile_img, off_x, off_y in tiles:
                    get_merged_ocr(tile_img, offset_x=off_x, offset_y=off_y, area_scale=1.0)
        
        if targets:
            log.info(f"Vision: Targets identified -> {len(targets)}")
        
        return targets
