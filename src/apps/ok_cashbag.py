import time
import random
import os
from src.base_bot import BaseBot
from src.logger import log

class OKCashbagAgent(BaseBot):
    def __init__(self):
        super().__init__()
        self.package_name = "com.skmc.okcashbag.home_google"
        self.app_name = "ok" # 이미지 폴더명 (assets/templates/ok)
        
        # .env에서 로드
        raw = os.getenv("KEYWORDS_OK", "")
        self.keywords = [k.strip() for k in raw.split(",") if k.strip()]
        
        # "전체보기"를 메뉴 목록에 추가하여 발견 시 진입 유도
        self.menu_keywords = ["쉽게", "돈되는", "쇼핑", "오락", "혜택", "이벤트", "전체보기"]
        
        # [추가] OK캐시백은 볼 게 많으므로 10바퀴 진득하게 돕니다.
        self.max_cycles = 10

    def launch_app(self):
        """OK캐시백 전용 실행 로직 (광고 없음 - 정지 스캔)"""
        log.info(f"Action: Launching {self.package_name}...")
        self.adb.stop_app(self.package_name)
        time.sleep(1)
        self.adb.launch_app(self.package_name)
        time.sleep(2) # [수정] 로딩 대기 단축 (6s -> 2s)
        
        # [수정] 광고 회피 동작 삭제 -> 즉시 스캔 시작
        log.info("App launched. Starting immediate scan...")
        self.scan_and_click_burst()

    def fast_patrol_move(self):
        """OK캐시백 전용: 입체적 화면 탐색 (중앙 집중 드래그)"""
        action = random.choices(
            ["STAY", "DOWN", "UP", "LEFT", "RIGHT", "COMPOUND"], 
            weights=[10, 30, 10, 10, 10, 30]
        )[0]
        
        mid_x, mid_y = self.width // 2, self.height // 2
        ry = random.randint(int(self.height * 0.3), int(self.height * 0.7))
        
        log.info(f"Patrol: [OK Spec] Executing {action}...")
        
        if action == "STAY":
            self.scan_and_click_burst()
        elif action == "COMPOUND":
            # [수정] 중앙을 잡고 시원하게 1초간 밀기
            log.info("Patrol: Wide RIGHT then Long DOWN")
            self.adb.swipe(int(self.width * 0.9), mid_y, int(self.width * 0.1), mid_y, duration=1000)
            time.sleep(1); self.scan_and_click_burst()
            
            self.adb.swipe(mid_x, int(self.height * 0.8), mid_x, int(self.height * 0.2), duration=1000)
            time.sleep(1.5); self.scan_and_click_burst()
        elif action == "DOWN":
            self.adb.swipe(mid_x, int(self.height * 0.8), mid_x, int(self.height * 0.2), duration=1000)
            time.sleep(1.5); self.scan_and_click_burst()
        elif action == "UP":
            self.adb.swipe(mid_x, int(self.height * 0.2), mid_x, int(self.height * 0.8), duration=1000)
            time.sleep(1.5); self.scan_and_click_burst()
        elif action == "LEFT":
            self.adb.swipe(int(self.width * 0.15), ry, int(self.width * 0.85), ry, duration=1000)
            time.sleep(1.5); self.scan_and_click_burst()
        elif action == "RIGHT":
            self.adb.swipe(int(self.width * 0.85), ry, int(self.width * 0.15), ry, duration=1000)
            time.sleep(1.5); self.scan_and_click_burst()
        
        time.sleep(1.0)
        self.scan_and_click_burst()
