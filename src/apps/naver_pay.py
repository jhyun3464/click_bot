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
        
        # [추가] 네이버 페이는 핵심만 슥 보고 2바퀴 만에 교대합니다.
        self.max_cycles = 2
