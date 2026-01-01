import cv2
import pytesseract
import numpy as np
import re
from src.logger import log

class VisionEngine:
    def __init__(self):
        pass

    def find_targets(self, image_path, target_keywords):
        """
        [1P Hunter Mode]
        이미지(템플릿) 매칭을 최우선으로 하여 보라색 원(1P)을 찾습니다.
        """
        targets = []
        img = cv2.imread(image_path)
        if img is None: return []

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 1. 템플릿(이미지) 매칭 (핵심!)
        import os
        template_dir = "assets/templates"
        if os.path.exists(template_dir):
            for filename in os.listdir(template_dir):
                if not filename.endswith(".png"): continue
                
                path = os.path.join(template_dir, filename)
                template = cv2.imread(path, 0)
                if template is None: continue
                # [최종 복구] 사용자 캡처 이미지 최적화 (민감도 0.75)
                for scale in np.linspace(0.7, 1.3, 10)[::-1]:
                    try:
                        resized = cv2.resize(template, None, fx=scale, fy=scale)
                        if resized.shape[0] > gray.shape[0] or resized.shape[1] > gray.shape[1]: continue
                        
                        res = cv2.matchTemplate(gray, resized, cv2.TM_CCOEFF_NORMED)
                        loc = np.where(res >= 0.75) 
                        
                        rw, rh = resized.shape[::-1]
                        for pt in zip(*loc[::-1]):
                            cx, cy = pt[0] + rw // 2, pt[1] + rh // 2
                            if not any(abs(t[0]-cx) < 30 and abs(t[1]-cy) < 30 for t in targets):
                                targets.append((cx, cy, filename, "IMAGE"))
                    except: pass

        # 2. 텍스트(OCR) 매칭 (보조)
        try:
            # 원본 크기에서 스캔 (전처리 최소화)
            custom_config = r'--oem 3 --psm 11'
            data = pytesseract.image_to_data(gray, lang='kor+eng', config=custom_config, output_type=pytesseract.Output.DICT)
            for i in range(len(data['text'])):
                text = data['text'][i].strip()
                if not text: continue
                
                clean_text = re.sub(r'[^a-zA-Z0-9가-힣P]', '', text).lower()
                if not clean_text: continue
                
                matched = False
                # 1) 숫자+P 패턴 (예: 10P)
                if re.search(r'\d+p', clean_text):
                    matched = True
                # 2) 단독 P (포인트)
                elif clean_text == 'p':
                    matched = True
                # 3) 키워드 매칭
                else:
                    for key in target_keywords:
                        ck = re.sub(r'[^a-zA-Z0-9가-힣P]', '', key).lower()
                        if not ck: continue
                        
                        # [망상 방지] 한 글자 노이즈 필터링
                        if len(clean_text) == 1:
                            # 한 글자는 키워드와 '정확히' 일치할 때만 허용
                            if clean_text == ck:
                                matched = True; break
                        # 2글자 이상일 때 부분 일치 허용
                        elif len(clean_text) >= 2:
                            # [중요] 키워드가 'p'인 경우, 부분 일치는 금지하고 숫자+p 패턴만 허용
                            if ck == 'p':
                                if re.search(r'\d+p', clean_text):
                                    matched = True; break
                            # 그 외 키워드(이벤트 등)는 부분 일치 허용
                            elif ck in clean_text or clean_text in ck:
                                matched = True; break
                
                if matched:
                    x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                    cx, cy = x + w // 2, y + h // 2
                    if not any(abs(t[0]-cx) < 30 and abs(t[1]-cy) < 30 for t in targets):
                        targets.append((cx, cy, text, "TEXT"))
        except: pass

        if targets:
            log.info(f"Vision: Found {len(targets)} targets -> {[t[2] for t in targets]}")
        
        return targets
