import time
import random
import os
from src.adb_handler import ADBHandler
from src.vision import VisionEngine
from src.db_handler import DBHandler
from src.logger import log

class BaseBot:
    def __init__(self):
        # [수정] 기기 ID 및 디스플레이 ID 설정을 추가하여 폴더블 폰 대응
        device_id = os.getenv("DEVICE_ID")
        display_id = os.getenv("DISPLAY_ID")
        self.adb = ADBHandler(device_id=device_id, adb_path=os.getenv("ADB_PATH"), display_id=display_id)
        self.vision = VisionEngine()
        self.db = DBHandler()
        
        # 실제 기기 해상도
        self.width, self.height = self.adb.get_screen_size()
        
        # 앱별 설정을 위한 변수 (자식 클래스에서 오버라이딩)
        self.package_name = ""
        self.app_name = None # 비전 엔진에 전달할 앱 식별자 (폴더명)
        self.keywords = []
        # [공통] 발견 시 최우선으로 진입할 메뉴 (모든 앱 적용)
        self.menu_keywords = ["출석", "체크"]
        # [독서 모드] 이 글자가 포함된 버튼을 클릭할 때만 독서 모드 발동
        self.reading_trigger_keywords = ["뉴스보기", "뉴스 보기", "기사보기", "기사 보기", "뉴스 읽기"]
        
        # [조기 종료] 발견 시 해당 앱 세션을 즉시 종료할 키워드
        self.exit_keywords = []
        
        # [설정] XML 스캔 사용 여부 (앱별로 오동작 시 끌 수 있음)
        self.use_xml = True

        self.clicked_history_temp = []
        
        # [수정] 클릭 후 동작 커스터마이징 (기본값: 15~30초 랜덤)
        self.click_wait_range = (15, 30) 
        self.auto_back_after_click = False # 클릭 후 자동 뒤로가기 여부

        # [지루함 감지] 화면 정체 확인용 변수
        self.last_screen_texts = []
        self.stagnation_count = 0

    class SessionFinishedException(Exception): pass
    class RestartAppException(Exception): pass

    def is_app_running(self):
        pkg = self.adb.get_current_package()
        return pkg and self.package_name in pkg

    def launch_app(self):
        """기본 앱 실행 로직 (필요시 자식 클래스에서 수정)"""
        self.adb.stop_app(self.package_name)
        time.sleep(1)
        self.adb.launch_app(self.package_name)
        time.sleep(2) # 로딩 대기

    def _execute_stay_mode(self):
        """뉴스/기사 화면에서 사람처럼 스크롤하며 머무릅니다."""
        log.info("Action: Entering Stay Mode (Reading content...)")
        # 30초 너무 김 -> 3회 스크롤 (약 10초)로 단축
        for i in range(3):
            mid_x = self.width // 2
            # 스크롤: 0.8->0.4 (40%)로 시원하게 변경
            self.adb.swipe(mid_x, int(self.height * 0.8), mid_x, int(self.height * 0.4), duration=500)
            # 읽는 척 대기 시간 랜덤 (2~4초)
            time.sleep(random.uniform(2.0, 4.0))
        
        log.info("Action: Reading finished. Returning...")
        self.adb.back()
        time.sleep(1)

    def scan_and_click_burst(self):
        """공통: 화면 스캔 및 광속 연타 (XML + Vision 하이브리드)"""
        # [무적의 투시] 1. UI XML 데이터에서 글자 타겟 추출 (보안 무시)
        xml_targets = []
        if self.use_xml:
            xml_data = self.adb.get_ui_xml()
            xml_targets = self.vision.find_targets_from_xml(xml_data, self.keywords)
        
        # 2. 이미지 기반 타겟 추출 (기존 방식 유지)
        screen_path = self.adb.screencap()
        vision_targets = []
        if screen_path:
            vision_targets = self.vision.find_targets(screen_path, self.keywords, app_name=self.app_name)
        
        # 3. 모든 타겟 통합 (XML 우선)
        targets = xml_targets + vision_targets
        
        # [광고 대기] 비전 엔진에서 광고로 판명하고, 타겟이 없을 경우
        if self.vision.is_last_screen_ad and not targets:
            log.info("Action: AD Screen Detected. Waiting 30 seconds for it to finish...")
            time.sleep(30)
            self.adb.back() # 광고 종료 후 닫기 시도
            time.sleep(1)
            return True

        # [생중계] 발견된 타겟 목록 출력 (디버깅용)
        if targets:
            log.info(f"Vision: Detected -> {[t[2] for t in targets]}")
        
        all_text = " ".join([str(t[2]) for t in targets])
        
        # [조기 종료 체크] 
        if any(ek in all_text for ek in self.exit_keywords):
            log.warning(f"Action: Exit Trigger Detected ({self.exit_keywords})")
            # 팝업 정리
            close_btns = [t for t in targets if any(k in str(t[2]) for k in ["확인", "닫기"])]
            for btn in close_btns:
                self.adb.tap(btn[0], btn[1])
                time.sleep(0.5)
            raise self.SessionFinishedException()
        
        # [지루함 감지]
        current_texts = sorted([str(t[2]) for t in targets])
        if current_texts == self.last_screen_texts and current_texts:
            self.stagnation_count += 1
            
            # [1단계] 5회 이상 정체 시: 강제 스와이프 시도 (화면 흔들기)
            if self.stagnation_count == 5:
                log.info("Action: Screen Stagnant (x5). Trying Wake-Up Swipe.")
                self.adb.swipe(self.width // 2, int(self.height * 0.7), self.width // 2, int(self.height * 0.3), duration=400)
                time.sleep(1)
                return False

            # [2단계] 10회 이상 정체 시: 비상 탈출 (뒤로가기)
            if self.stagnation_count >= 10:
                log.warning("Action: Screen Stuck (x10). Emergency Back x2")
                for _ in range(2):
                    self.adb.back()
                    time.sleep(0.3)
                
                # [3단계] 15회 이상 정체 시: 앱 강제 재시작 (뒤로가기도 안 먹힐 때)
                if self.stagnation_count >= 15:
                    log.error("Action: Screen Stuck (x15). Force Restart Triggered.")
                    raise self.RestartAppException()

                # (주의: 뒤로가기 직후 stagnation_count 초기화 안 함. 다음 루프에서 재검사)
                return False 
        else:
            self.stagnation_count = 0
            self.last_screen_texts = current_texts
            
        # 2. 필터링
        valid_targets = []
        for t in targets:
            cx, cy, label, ttype = t
            is_menu = any(m in str(label) for m in self.menu_keywords)
            if is_menu and self.db.is_already_harvested_today(label): continue
            if any(abs(h[0]-cx) < 50 and abs(h[1]-cy) < 50 for h in self.clicked_history_temp): continue
            valid_targets.append(t)

        # 3. 클릭 실행
        if valid_targets:
            # [우선순위 정렬]
            # 1순위: 메뉴 키워드 (가장 먼저 진입해야 함)
            # 2순위: 이미지 타겟 (정확도 높음)
            # 3순위: 상단에 있는 것 우선
            valid_targets.sort(key=lambda x: (
                0 if any(m in str(x[2]) for m in self.menu_keywords) else 1,
                0 if x[3] == "IMAGE" else 1,
                x[1]
            ))
            
            target = valid_targets[0]
            cx, cy, label, ttype = target
            
            # [독서 모드 판별]
            is_reading = any(rk in str(label) for rk in self.reading_trigger_keywords)
            
            log.info(f"Action: CLICK -> '{label}' at ({cx}, {cy})")
            self.adb.tap(cx, cy)
            
            is_menu = any(m in str(label) for m in self.menu_keywords)
            if is_menu:
                self.db.record_harvest(label)
            
            self.clicked_history_temp.append((cx, cy))
            if len(self.clicked_history_temp) > 500: self.clicked_history_temp.pop(0)
            
            # [수정] 클릭 후 대기 및 자동 복귀 로직
            if is_reading:
                # 뉴스/기사 클릭 시: 로딩 후 독서 모드 진입
                time.sleep(3)
                self._execute_stay_mode()
            elif not is_menu and self.auto_back_after_click:
                wait_time = random.uniform(self.click_wait_range[0], self.click_wait_range[1])
                log.info(f"Action: Waiting {wait_time:.1f}s for reward and returning...")
                time.sleep(wait_time)
                self.adb.back()
                time.sleep(1.5) # 뒤로가기 후 안정화
            else:
                time.sleep(random.uniform(0.1, 0.4))
                
            return True 
        
        return False

    def fast_patrol_move(self):
        """공통: 공격적 패트롤 (제자리 스캔 금지, 무조건 이동)"""
        # STAY 삭제 -> 멍때리기 방지
        action = random.choices(["DOWN", "UP"], weights=[70, 30])[0]
        
        mid_x = self.width // 2
        # 좌우 랜덤 오차 추가
        rx = mid_x + random.randint(-40, 40)
        
        log.info(f"Patrol: Active Move -> {action}")
        
        if action == "DOWN":
            # [다양성] 짧게 내리기 vs 길게 내리기
            if random.random() < 0.4:
                # Short (조금만)
                y1, y2 = int(self.height * 0.6), int(self.height * 0.4)
                duration = random.randint(400, 600)
            else:
                # Long (시원하게)
                y1, y2 = int(self.height * 0.8), int(self.height * 0.25)
                duration = random.randint(600, 900)
                
            self.adb.swipe(rx, y1, rx, y2, duration=duration)
            
        elif action == "UP":
            # 위로 다시 확인
            y1, y2 = int(self.height * 0.3), int(self.height * 0.7)
            self.adb.swipe(rx, y1, rx, y2, duration=700)
        
        # 이동 후 스캔 로딩 대기
        time.sleep(random.uniform(1.0, 1.5))

    def run_session(self, max_cycles=10):
        """한 앱을 일정 횟수(max_cycles)만큼 훑고 종료함"""
        cycle = 0
        current_sub_cycle = 0
        cycle_limit = random.randint(10, 15) # [수정] 끈질기게 머무르기 (10~15번)
        
        self.launch_app() # 시작 시 앱 실행
        
        try:
            while cycle < max_cycles:
                try:
                    # [앱 실행 상태 확인 및 복구 로직]
                    if not self.is_app_running():
                        log.warning("App not in foreground. Attempting Soft Recovery (Back)...")
                        # 1차 시도: 뒤로가기로 광고/브라우저 닫기
                        self.adb.back()
                        time.sleep(1.5)
                        
                        if not self.is_app_running():
                            log.warning("Soft Recovery failed. Hard Restarting App...")
                            self.launch_app()
                            current_sub_cycle = 0
                        else:
                            log.info("Soft Recovery successful. Resuming session.")
                        
                        continue

                    clicked = self.scan_and_click_burst()
                    
                    if not clicked:
                        current_sub_cycle += 1
                        self.fast_patrol_move()
                        
                        if current_sub_cycle >= cycle_limit:
                            num_backs = random.randint(5, 8) # 조금 더 확실한 탈출
                            for _ in range(num_backs):
                                self.adb.back()
                                time.sleep(0.3)
                            current_sub_cycle = 0
                            cycle_limit = random.randint(10, 15)
                            self.clicked_history_temp = []
                            cycle += 1
                    else:
                        current_sub_cycle = 0
                        time.sleep(0.5)
                        
                except self.RestartAppException:
                    log.warning("Action: Force Restarting App due to stuck screen...")
                    self.launch_app()
                    current_sub_cycle = 0
                    self.stagnation_count = 0
                    self.last_screen_texts = []
                    
        except self.SessionFinishedException:
            pass # 조기 종료
        
        self.adb.stop_app(self.package_name)
