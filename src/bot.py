import time
import random
import os
from dotenv import load_dotenv
from src.adb_handler import ADBHandler
from src.vision import VisionEngine
from src.db_handler import DBHandler
from src.logger import log

load_dotenv()

class OKBot:
    def __init__(self):
        self.adb = ADBHandler(adb_path=os.getenv("ADB_PATH"))
        self.vision = VisionEngine()
        self.db = DBHandler()
        
        # [해상도 최적화] 실제 기기 해상도 측정
        self.width, self.height = self.adb.get_screen_size()
        log.info(f"Detected Resolution: {self.width}x{self.height}")
        
        raw_keys = os.getenv("TARGET_KEYWORDS", "").split(",")
        self.keywords = [k.strip() for k in raw_keys if k.strip()]
        
        # 메뉴형 키워드
        self.menu_keywords = ["쉽게", "돈되는", "쇼핑", "오락", "혜택", "이벤트"]
        self.clicked_history_temp = []

    def is_app_running(self):
        pkg = self.adb.get_current_package()
        return pkg and "com.skmc.okcashbag.home_google" in pkg

    def launch_app(self):
        log.info("Action: Attempting to recover app screen...")
        wait_time = random.uniform(3.0, 5.0)
        log.info(f"Action: Waiting {wait_time:.1f}s before recovery...")
        time.sleep(wait_time)
        
        log.info("Action: Pressing BACK 5 times to escape popups/menus...")
        for _ in range(5):
            self.adb.back()
            time.sleep(0.5)
            
        if not self.is_app_running():
            log.info("Action: App still stuck. Force Restarting...")
            self.adb.stop_app()
            time.sleep(1)
            self.adb.launch_app()
            time.sleep(6)
        
        # [초반 광고 돌파] 직선 스와이프 강화 (대각선 튐 방지)
        log.info("Action: Initial linear swipe sequence...")
        safe_x = int(self.width * 0.1)  # 좌측 10% (안전 여백)
        mid_x = self.width // 2
        mid_y = self.height // 2
        
        # 1단계: 수직 하강 (X값 완벽 고정)
        # 60% 지점에서 15% 지점으로 (아래로 내리기)
        start_y = int(self.height * 0.6)
        end_y = int(self.height * 0.15)
        log.info(f"Action: Straight DOWN Swipe at X={safe_x}")
        self.adb.swipe(safe_x, start_y, safe_x, end_y, duration=700)
        time.sleep(0.8)
        
        # 2단계: 수평 이동 (Y값 완벽 고정)
        # 우측 85%에서 좌측 15%로 (오른쪽 보기)
        side_start_x = int(self.width * 0.85)
        side_end_x = int(self.width * 0.15)
        log.info(f"Action: Straight LEFT Swipe at Y={mid_y}")
        self.adb.swipe(side_start_x, mid_y, side_end_x, mid_y, duration=700)
        time.sleep(0.8)
        
        # 3단계: 마무리 바닥 밀기 (X값 완벽 고정)
        self.adb.swipe(safe_x, int(self.height * 0.9), safe_x, int(self.height * 0.1), duration=700)
        time.sleep(1.0)

    def scan_and_click_burst(self):
        """현재 화면을 즉시 스캔하고 보이는 모든 타겟을 클릭 (초고속)"""
        screen_path = self.adb.screencap()
        if not screen_path: return False
        
        targets = self.vision.find_targets(screen_path, self.keywords)
        valid_targets = []
        for t in targets:
            cx, cy, label, ttype = t
            is_menu = any(m in label for m in self.menu_keywords)
            if is_menu and self.db.is_already_harvested_today(label): continue
            # [최적화] 중복 범위 50px로 축소 (폴드 대화면 정밀 클릭)
            if any(abs(h[0]-cx) < 50 and abs(h[1]-cy) < 50 for h in self.clicked_history_temp): continue
            valid_targets.append(t)

        if valid_targets:
            log.info(f"Action: Burst clicking {len(valid_targets)} targets found during patrol...")
            for target in valid_targets:
                cx, cy, label, ttype = target
                self.adb.tap(cx, cy)
                if any(m in label for m in self.menu_keywords):
                    self.db.record_harvest(label)
                self.clicked_history_temp.append((cx, cy))
                if len(self.clicked_history_temp) > 500: self.clicked_history_temp.pop(0)
                time.sleep(random.uniform(0.1, 0.3))
            return True
        return False

    def fast_patrol_move(self):
        """입체적 화면 탐색 (더 길고 강력한 스크롤)"""
        # 액션 유형 결정
        action = random.choices(
            ["STAY", "DOWN", "UP", "LEFT", "RIGHT", "COMPOUND"], 
            weights=[10, 30, 10, 10, 10, 30]
        )[0]
        
        safe_x = int(self.width * 0.08)
        ry = random.randint(int(self.height * 0.3), int(self.height * 0.7))
        
        if action == "STAY":
            self.scan_and_click_burst()
        elif action == "COMPOUND":
            log.info("Patrol: COMPOUND (Safe LEFT then DOWN)")
            # [더 길게] 가로 끝에서 끝까지
            self.adb.swipe(int(self.width * 0.95), ry, int(self.width * 0.05), ry, duration=400)
            self.scan_and_click_burst()
            # [더 길게] 세로 바닥까지
            y1 = random.randint(int(self.height * 0.85), int(self.height * 0.95))
            y2 = random.randint(int(self.height * 0.05), int(self.height * 0.15))
            self.adb.swipe(safe_x, y1, safe_x, y2, duration=400)
            self.scan_and_click_burst()
        elif action == "DOWN":
            # [더 길게] 화면 전체 훑기
            y1 = random.randint(int(self.height * 0.9), int(self.height * 0.98))
            y2 = random.randint(int(self.height * 0.02), int(self.height * 0.1))
            log.info(f"Patrol: Long DOWN from {y1} to {y2}")
            self.adb.swipe(safe_x, y1, safe_x, y2, duration=500)
            self.scan_and_click_burst()
        elif action == "LEFT":
            # 가로 끝까지
            self.adb.swipe(int(self.width * 0.95), ry, int(self.width * 0.05), ry, duration=500)
            self.scan_and_click_burst()
        elif action == "RIGHT":
            self.adb.swipe(int(self.width * 0.05), ry, int(self.width * 0.95), ry, duration=500)
            self.scan_and_click_burst()
        elif action == "UP":
            # 위로 끝까지
            self.adb.swipe(safe_x, int(self.height * 0.05), safe_x, int(self.height * 0.95), duration=500)
            self.scan_and_click_burst()
        
        time.sleep(random.uniform(0.3, 0.6))

    def run(self):
        log.info(">>> ULTRA BULLDOZER MODE (Active Patrol) STARTED <<<")
        # [수정] 최소 3번, 최대 5번 랜덤 주기
        cycle_limit = random.randint(3, 5)
        current_cycle = 0
        
        while True:
            if not self.is_app_running():
                self.launch_app()
                current_cycle = 0
                continue

            # 메인 루프에서도 쉼 없이 스캔 & 클릭
            clicked = self.scan_and_click_burst()
            
            if not clicked:
                current_cycle += 1
                log.info(f"Patrolling... ({current_cycle}/{cycle_limit})")
                self.fast_patrol_move()
                
                if current_cycle >= cycle_limit:
                    num_backs = random.randint(5, 7)
                    log.info(f"Action: Deep Escape! BACK {num_backs} times...")
                    for _ in range(num_backs):
                        self.adb.back()
                        time.sleep(random.uniform(0.2, 0.5))
                    
                    # [리셋] 탈출했으므로 좌표 기억 초기화
                    current_cycle = 0
                    cycle_limit = random.randint(3, 6);
                    self.clicked_history_temp = [] 
            else:
                # 무언가 클릭했다면 사이클 카운트 초기화 (여기 더 먹을 거 있다는 뜻)
                current_cycle = 0 
                time.sleep(0.5)

if __name__ == "__main__":
    OKBot().run()