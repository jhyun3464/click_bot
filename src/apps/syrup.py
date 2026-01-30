import os
import time
import random
from src.base_bot import BaseBot
from src.logger import log

class SyrupAgent(BaseBot):
    def __init__(self):
        super().__init__()
        # [수정] 실제 기기에서 확인된 정확한 시럽 패키지명 적용
        self.package_name = "com.skt.skaf.OA00026910"
        self.app_name = "syrup"
        
        # .env에서 시럽 전용 키워드 로드
        raw = os.getenv("KEYWORDS_SYRUP", "")
        self.keywords = [k.strip() for k in raw.split(",") if k.strip()]
        
        # 메뉴형 키워드
        self.menu_keywords = ["야금야금", "모으기", "출석", "혜택"]
        
        # [설정] 시럽(Syrup)도 텍스트가 많으므로 독서 모드(Stay Mode) 비활성화
        self.stay_keywords = []
        self.reading_mode_threshold = 2000
        
        # [추가] 클릭 후 15~30초 랜덤 대기 후 자동 복귀 (적립 확인용)
        self.click_wait_range = (15, 30)
        self.auto_back_after_click = True
        
        # [수정] 시럽 비중 확대: 3바퀴
        self.max_cycles = 3

    def launch_app(self):
        """시럽 실행 및 초기 광고 스킵 스크롤"""
        log.info(f"Action: Launching {self.package_name}...")
        self.adb.stop_app(self.package_name)
        time.sleep(1)
        self.adb.launch_app(self.package_name)
        
        # 시럽 로딩 대기
        log.info("Waiting 2s for Syrup to load...")
        time.sleep(2) 
        
        # [수정] 시작 후 화면 50% 내리기 (포커스 후 스크롤)
        log.info("Action: Initial 50% scroll down for Syrup content...")
        mid_x, mid_y = self.width // 2, self.height // 2
        safe_x = int(self.width * 0.08)
        
        self.adb.tap(mid_x, mid_y) # 포커스
        time.sleep(0.5)
        
        start_y = int(self.height * 0.8)
        end_y = int(self.height * 0.3)
        self.adb.swipe(safe_x, start_y, safe_x, end_y, duration=600)
        time.sleep(1.0)
        
        # 사냥 시작
        log.info("Syrup ready. Starting scan...")
        self.scan_and_click_burst()
