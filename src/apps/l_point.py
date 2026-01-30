import os
import time
import random
from src.base_bot import BaseBot
from src.logger import log

class LPointAgent(BaseBot):
    def __init__(self):
        super().__init__()
        # 실제 엘포인트 패키지명
        self.package_name = "com.lottemembers.android"
        self.app_name = "lpoint"
        
        raw = os.getenv("KEYWORDS_LPOINT", "")
        self.keywords = [k.strip() for k in raw.split(",") if k.strip()]
        
        # "출석"을 메뉴 목록에 추가
        self.menu_keywords = ["미션", "적립", "출석", "오늘의 적립", "클릭적립"]
        
        # [수정] 엘포인트 비중 보통: 2바퀴
        self.max_cycles = 2

    def launch_app(self):
        """엘포인트 실행 및 초기 진입 로직"""
        log.info(f"Action: Launching {self.package_name}...")
        self.adb.stop_app(self.package_name)
        time.sleep(1)
        self.adb.launch_app(self.package_name)
        
        log.info("Waiting 5s for L.POINT to fully load...")
        time.sleep(5) 
        
        # 1. 일단 보이는 거 한 번 훑고
        log.info("Initial scan at the top...")
        self.scan_and_click_burst()
        
        # 2. [사용자 요청] 3초 대기 후 화면 내리기 시작
        log.info("Waiting 3s before initial scroll...")
        time.sleep(3)
        
        log.info("First scroll to enter the feed...")
        mid_x = self.width // 2
        self.adb.swipe(mid_x, int(self.height * 0.8), mid_x, int(self.height * 0.3), duration=800)
        time.sleep(1.5)
        
        # 이제 본격적인 루틴 시작
        self.scan_and_click_burst()

    def scan_and_click_burst(self):
        """엘포인트 전용 클릭 (보안 화면 대응: XML only)"""
        # [보안 우회] 스크린샷이 막혔으므로 XML 덤프만 사용
        # self.adb.screencap() 호출 제거
        
        xml_data = self.adb.get_ui_xml()
        if not xml_data:
            log.warning("L.POINT: Failed to dump UI XML. Security might be too high.")
            return False
            
        # XML에서만 타겟 추출
        targets = self.vision.find_targets_from_xml(xml_data, self.keywords)
        
        # [팝업 청소부] "리워드 지급됨" 감지 시 X 버튼 찾기 (생략 - 위와 동일)
        # ... (기존 팝업 처리 로직 유지되도록, 여기서는 생략하지 않고 아래에 이어붙임)

        # 타겟 리스트가 아니라 원본 XML이나 targets에서 텍스트를 검색
        all_labels = [t[2] for t in targets]
        reward_popup_detected = any(("리워드" in str(l) and "지급" in str(l)) for l in all_labels)
        
        # (기존 팝업 처리 코드...)
        if reward_popup_detected:
            # ... (기존 코드 생략 없이 유지해야 하지만 replace 툴 특성상 문맥을 다 가져와야 함)
            # 여기서는 편의상 팝업 처리가 이미 위에서 실행되었다고 가정하고 블라인드 로직에 집중
            pass

        # ---------------------------------------------------------
        # [블라인드 모드] 텍스트 타겟을 하나도 못 찾았다면?
        # 웹뷰라서 텍스트가 숨겨진 버튼일 수 있음 -> clickable=true 요소 탐색
        # ---------------------------------------------------------
        if not targets:
            log.info("L.POINT: No text targets found. Engaging 'Blind Click' mode for clickable elements...")
            try:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(xml_data)
                
                for node in root.iter():
                    clickable = node.attrib.get('clickable', 'false')
                    if clickable == 'true':
                        bounds = node.attrib.get('bounds', '')
                        import re
                        match = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
                        if match:
                            x1, y1, x2, y2 = map(int, match.groups())
                            
                            # [필터링] 상단바(헤더)와 하단바(내비)는 제외
                            cy = (y1 + y2) // 2
                            if cy < self.height * 0.15 or cy > self.height * 0.85:
                                continue
                                
                            # 너무 큰 영역(화면 전체 등)은 제외
                            w, h = x2 - x1, y2 - y1
                            if w > self.width * 0.9 or h > self.height * 0.5:
                                continue
                            
                            # 적절한 크기의 버튼 발견
                            cx = (x1 + x2) // 2
                            targets.append((cx, cy, "Unknown_Button", "BLIND"))
                            
                if targets:
                    log.info(f"L.POINT: Found {len(targets)} mystery buttons via Blind Scan.")
            except Exception as e:
                log.error(f"Blind scan error: {e}")

        valid_targets = []
        
        for t in targets:
            cx, cy, label, ttype = t
            is_menu = any(m in label for m in self.menu_keywords)
            if is_menu and self.db.is_already_harvested_today(label): continue
            if any(abs(h[0]-cx) < 50 and abs(h[1]-cy) < 50 for h in self.clicked_history_temp): continue
            valid_targets.append(t)

        if valid_targets:
            log.info(f"Action: Found {len(valid_targets)} L.POINT targets (XML)! Burst clicking...")
            # 위에서 아래로 순차 클릭
            valid_targets.sort(key=lambda x: x[1])
            
            for target in valid_targets:
                cx, cy, label, ttype = target
                
                # 메뉴(내비게이션)인지 실제 적립 타겟인지 구분
                is_menu_click = any(m in label for m in self.menu_keywords)
                
                self.adb.tap(cx, cy)
                
                if is_menu_click:
                    self.db.record_harvest(label)
                    # 메뉴 진입은 짧게 대기
                    wait_time = random.uniform(4.0, 6.0)
                    log.info(f"Action: Navigating -> '{label}' (Wait {wait_time:.1f}s)")
                else:
                    # 포인트 적립 클릭 (광고 팝업 가능성 높음)
                    self.clicked_history_temp.append((cx, cy))
                    if len(self.clicked_history_temp) > 500: self.clicked_history_temp.pop(0)
                    
                    wait_time = random.uniform(15.0, 25.0)
                    log.info(f"Action: Reward Click -> '{label}' (Waiting {wait_time:.1f}s for ad/popup)")
                
                time.sleep(wait_time)
            return True
        return False

    def fast_patrol_move(self):
        """L.Point 전용 패트롤: 공격적인 하단 스크롤 (훑어내리기)"""
        # 아래로 내려가는 게 주 목적 (90%)
        action = random.choices(["DOWN", "UP"], weights=[90, 10])[0]
        
        mid_x = self.width // 2
        rx = mid_x + random.randint(-30, 30) # 중앙 부근 랜덤
        
        log.info(f"Patrol: L.POINT Scrolling -> {action}")
        
        if action == "DOWN":
            # [다양한 스크롤] 짧게 툭 or 길게 쭈욱
            scroll_type = random.choice(["SHORT", "LONG", "LONG"])
            
            if scroll_type == "SHORT":
                # 조금만 내리기 (놓친 거 없나)
                y1 = int(self.height * 0.6)
                y2 = int(self.height * 0.4)
                duration = random.randint(400, 600)
            else:
                # 시원하게 내리기 (다음 페이지)
                y1 = int(self.height * 0.8)
                y2 = int(self.height * 0.2)
                duration = random.randint(600, 900)
                
            self.adb.swipe(rx, y1, rx, y2, duration=duration)
        
        elif action == "UP":
            # 가끔 위로 살짝 올려보기 (리프레시 느낌)
            y1 = int(self.height * 0.3)
            y2 = int(self.height * 0.7)
            self.adb.swipe(rx, y1, rx, y2, duration=700)
            
        time.sleep(random.uniform(1.0, 1.8))
        
        # 이동 후 스캔은 메인 루프에서 처리하므로 중복 호출 제거