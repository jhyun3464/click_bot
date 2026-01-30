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
        
        # [수정] OK캐시백은 XML 데이터가 부정확하므로 이미지/OCR만 사용
        self.use_xml = False
        
        # [추가] 광고/브라우저 팝업 대응: 클릭 후 15~30초 랜덤 대기 후 자동 뒤로가기
        self.click_wait_range = (15, 30)
        self.auto_back_after_click = True

        # [수정] OK캐시백 비중 확대: 3바퀴
        self.max_cycles = 3

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
        """OK캐시백 전용: 공격적 입체 탐색 (제자리 스캔 제거)"""
        action = random.choices(
            ["DOWN", "UP", "LEFT", "RIGHT", "COMPOUND"], 
            weights=[40, 10, 15, 15, 20]
        )[0]
        
        mid_x, mid_y = self.width // 2, self.height // 2
        ry = random.randint(int(self.height * 0.3), int(self.height * 0.7))
        
        log.info(f"Patrol: [OK Active] Executing {action}...")
        
        if action == "COMPOUND":
            # [복합] 우측으로 크게 밀고 + 아래로 내리기
            log.info("Patrol: Wide RIGHT then Long DOWN")
            self.adb.swipe(int(self.width * 0.9), mid_y, int(self.width * 0.1), mid_y, duration=800)
            time.sleep(1.2)
            
            self.adb.swipe(mid_x, int(self.height * 0.8), mid_x, int(self.height * 0.25), duration=900)
            time.sleep(1.2)
            
        elif action == "DOWN":
            # 시원하게 내리기
            self.adb.swipe(mid_x, int(self.height * 0.8), mid_x, int(self.height * 0.2), duration=800)
            time.sleep(1.5)
            
        elif action == "UP":
            self.adb.swipe(mid_x, int(self.height * 0.2), mid_x, int(self.height * 0.8), duration=800)
            time.sleep(1.5)
            
        elif action == "LEFT":
            self.adb.swipe(int(self.width * 0.15), ry, int(self.width * 0.85), ry, duration=800)
            time.sleep(1.5)
            
        elif action == "RIGHT":
            self.adb.swipe(int(self.width * 0.85), ry, int(self.width * 0.15), ry, duration=800)
            time.sleep(1.5)
        
        # 동작 후 추가 대기 (로딩)
        time.sleep(0.5)
