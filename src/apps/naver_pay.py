import os
from src.base_bot import BaseBot

class NaverPayAgent(BaseBot):
    def __init__(self):
        super().__init__()
        # [수정] 실제 기기에서 확인된 정확한 패키지명 적용
        self.package_name = "com.naverfin.payapp"
        self.app_name = "naver"
        
        raw = os.getenv("KEYWORDS_NAVER", "")
        self.keywords = [k.strip() for k in raw.split(",") if k.strip()]
        
        self.menu_keywords = ["혜택", "이벤트", "적립"]
        
        # [조기 종료] 줄바꿈 고려하여 핵심 키워드만 등록
        self.exit_keywords = ["캠페인 당", "캠페인당"]
        
        # [설정] 네이버 페이는 이미지 클릭 위주이므로 '독서 모드(Stay Mode)' 비활성화
        self.stay_keywords = [] 
        self.reading_mode_threshold = 2000
        
        # [최적화] 네이버는 클릭 후 15~30초 랜덤 대기 후 자동으로 돌아와서 다음 항목 클릭
        self.click_wait_range = (15, 30)
        self.auto_back_after_click = True
        
        # [추가] 네이버 페이는 핵심만 슥 보고 2바퀴 만에 교대합니다.
        self.max_cycles = 1

    def launch_app(self):
        """네이버페이 실행 및 초기 포인트 진입 강제"""
        import time
        from src.logger import log
        
        log.info(f"Action: Launching {self.package_name}...")
        self.adb.stop_app(self.package_name)
        time.sleep(1)
        self.adb.launch_app(self.package_name)
        
        log.info("Waiting for Naver Pay to load...")
        time.sleep(6) # 로딩 대기
        
        # [강제 진입] "포인트" 메뉴를 찾아 무조건 클릭
        log.info("Force Entry: Searching for '포인트' button to start...")
        
        # 1. XML 덤프로 확실하게 찾기 시도
        xml_data = self.adb.get_ui_xml()
        if xml_data:
            targets = self.vision.find_targets_from_xml(xml_data, ["포인트", "혜택"])
            if targets:
                # 하단에 있는 버튼을 클릭해야 하므로 Y좌표 기준 내림차순 정렬
                targets.sort(key=lambda t: t[1], reverse=True) 
                t = targets[0]
                log.info(f"Force Entry: Clicking '{t[2]}' at ({t[0]}, {t[1]}) (Bottom button)")
                self.adb.tap(t[0], t[1])
                time.sleep(3) # 화면 전환 대기
                return

        # 2. 못 찾았으면 좌표 기반 클릭 (하단 탭 바 추정)
        log.warning("Force Entry: '포인트' text not found. Trying bottom tab coordinates...")
        # 하단 탭 바 위치 추정: 화면 너비의 80%, 높이의 95% 지점
        w, h = self.width, self.height
        self.adb.tap(int(w * 0.8), int(h * 0.95)) 
        time.sleep(3)
