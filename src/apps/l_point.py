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
        
        # [추가] 엘포인트도 광고가 많고 볼 게 많으므로 10바퀴!
        self.max_cycles = 10

    def launch_app(self):
        """엘포인트 실행 및 정지 스캔 (사용자 요청: 시작 스크롤 제거)"""
        log.info(f"Action: Launching {self.package_name}...")
        self.adb.stop_app(self.package_name)
        time.sleep(1)
        self.adb.launch_app(self.package_name)
        
        # [수정] 대기 시간 단축 (10s -> 2s)
        log.info("Waiting 2s for L.POINT to load...")
        time.sleep(2) 
        
        # [수정] 광고 회피 동작 삭제 -> 즉시 스캔 시작
        log.info("L.POINT loaded. Starting immediate scan from the top...")
        self.scan_and_click_burst()

    def scan_and_click_burst(self):
        """엘포인트 전용 클릭 (광고 시청을 위해 길게 대기)"""
        screen_path = self.adb.screencap()
        if not screen_path: return False
        
        targets = self.vision.find_targets(screen_path, self.keywords, app_name=self.app_name)
        valid_targets = []
        
        for t in targets:
            cx, cy, label, ttype = t
            is_menu = any(m in label for m in self.menu_keywords)
            if is_menu and self.db.is_already_harvested_today(label): continue
            if any(abs(h[0]-cx) < 50 and abs(h[1]-cy) < 50 for h in self.clicked_history_temp): continue
            valid_targets.append(t)

        if valid_targets:
            log.info(f"Action: Found {len(valid_targets)} L.POINT targets! Burst clicking...")
            valid_targets.sort(key=lambda x: (0 if x[3] == "IMAGE" else 1, x[1]))
            
            for target in valid_targets:
                cx, cy, label, ttype = target
                self.adb.tap(cx, cy)
                
                if any(m in label for m in self.menu_keywords):
                    self.db.record_harvest(label)
                
                self.clicked_history_temp.append((cx, cy))
                if len(self.clicked_history_temp) > 500: self.clicked_history_temp.pop(0)
                
                # [광고 시청 모드] 광고 다 봐야 하니까 15~35초 랜덤 대기
                wait_time = random.uniform(15.0, 35.0)
                log.info(f"Action: Ad detected! Waiting {wait_time:.1f}s until finish...")
                time.sleep(wait_time)
            return True
        return False