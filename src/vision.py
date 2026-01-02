import cv2
import pytesseract
import numpy as np
import re
from src.logger import log

class VisionEngine:
    """
    화면 분석 및 텍스트/이미지 인식을 담당하는 엔진 클래스입니다.
    """
    def __init__(self):
        pass

    def find_targets(self, image_path, target_keywords, app_name=None):
        """
        [1P Hunter Mode]
        화면 캡처본에서 이미지(템플릿)와 텍스트(OCR)를 분석하여 클릭 대상을 찾습니다.
        app_name이 있으면 해당 앱 전용 폴더의 이미지만 검색합니다.
        """
        targets = []
        img = cv2.imread(image_path)
        if img is None:
            log.error(f"Vision: 이미지를 읽을 수 없습니다: {image_path}")
            return []

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 1. 템플릿(이미지) 매칭 (핵심!)
        import os
        # 앱별 전용 폴더 우선 탐색
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
                
                # [최적화] 사용자 캡처 이미지 대응: 멀티 스케일 매칭 (0.7 ~ 1.3배)
                for scale in np.linspace(0.7, 1.3, 10)[::-1]:
                    try:
                        resized = cv2.resize(template, None, fx=scale, fy=scale)
                        if resized.shape[0] > gray.shape[0] or resized.shape[1] > gray.shape[1]: 
                            continue
                        
                        # 템플릿 매칭 수행 (민감도 0.75)
                        res = cv2.matchTemplate(gray, resized, cv2.TM_CCOEFF_NORMED)
                        loc = np.where(res >= 0.75) 
                        
                        rw, rh = resized.shape[::-1]
                        for pt in zip(*loc[::-1]):
                            cx, cy = pt[0] + rw // 2, pt[1] + rh // 2
                            # 중복 좌표 제거 (반경 30px 이내)
                            if not any(abs(t[0]-cx) < 30 and abs(t[1]-cy) < 30 for t in targets):
                                targets.append((cx, cy, filename, "IMAGE"))
                    except Exception:
                        pass

        # 2. 텍스트(OCR) 매칭 (보조)
        # 이미지 매칭으로 못 잡은 텍스트 버튼들을 찾습니다.
        try:
            # Tesseract OCR 설정 (낱글자 및 한 줄 인식 최적화)
            custom_config = r'--oem 3 --psm 11'
            data = pytesseract.image_to_data(gray, lang='kor+eng', config=custom_config, output_type=pytesseract.Output.DICT)
            
            for i in range(len(data['text'])):
                text = data['text'][i].strip()
                if not text: continue
                
                # 특수문자 제거 및 소문자화 (정밀 비교용)
                clean_text = re.sub(r'[^a-zA-Z0-9가-힣P]', '', text).lower()
                if not clean_text: continue
                
                matched = False
                # 1) 숫자+P 또는 숫자+금 패턴 (예: 10P, 30금)
                if re.search(r'\d+p', clean_text) or re.search(r'\d+금', clean_text):
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
                            # 'P' 또는 '금' 관련어는 부분 일치 금지 (숫자가 없으면 무시)
                            if ck in ['p', '금']:
                                if re.search(r'\d+p', clean_text) or re.search(r'\d+금', clean_text):
                                    matched = True; break
                            elif ck in clean_text or clean_text in ck:
                                matched = True; break
                
                if matched:
                    # 중심 좌표 계산
                    x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                    cx, cy = x + w // 2, y + h // 2
                    # 중복 제거
                    if not any(abs(t[0]-cx) < 30 and abs(t[1]-cy) < 30 for t in targets):
                        targets.append((cx, cy, text, "TEXT"))
        except Exception as e:
            log.error(f"Vision: OCR 처리 중 오류 발생: {e}")

        # 결과 로그 출력
        if targets:
            log.info(f"Vision: {len(targets)}개의 타겟 발견 -> {[t[2] for t in targets]}")
        
        return targets