import time
import random
import os
from src.adb_handler import ADBHandler
from src.vision import VisionEngine
from src.db_handler import DBHandler
from src.logger import log

class BaseBot:
    def __init__(self):
        self.adb = ADBHandler(adb_path=os.getenv("ADB_PATH"))
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
        # [조기 종료] 발견 시 해당 앱 세션을 즉시 종료할 키워드
        self.exit_keywords = []
        
        self.clicked_history_temp = []
        
        # [지루함 감지] 화면 정체 확인용 변수
        self.last_screen_texts = []
        self.stagnation_count = 0

    class SessionFinishedException(Exception): pass

    def is_app_running(self):
        pkg = self.adb.get_current_package()
        return pkg and self.package_name in pkg

    def launch_app(self):
        """기본 앱 실행 로직 (필요시 자식 클래스에서 수정)"""
        log.info(f"Action: Launching {self.package_name}...")
        self.adb.stop_app(self.package_name)
        time.sleep(1)
        self.adb.launch_app(self.package_name)
        time.sleep(2) # [수정] 로딩 대기 단축 (6s -> 2s)

    def scan_and_click_burst(self):
        """공통: 화면 스캔 및 광속 연타 (상세 로그 추가)"""
        screen_path = self.adb.screencap()
        if not screen_path: return False
        
        # 1. 화면의 모든 타겟 스캔
        targets = self.vision.find_targets(screen_path, self.keywords, app_name=self.app_name)
        
        # [생중계] 봇이 지금 보고 있는 모든 것들을 로그로 출력
        if targets:
            log.info(f"Vision: 현재 화면에서 발견된 목록 -> {[t[2] for t in targets]}")
        
        # [조기 종료 체크] 이미 다 턴 앱이면 세션 종료
        all_text = " ".join([str(t[2]) for t in targets])
        if any(ek in all_text for ek in self.exit_keywords):
            log.warning(f"Exit Trigger Found! ({self.exit_keywords}) -> Finishing Session early.")
            # 혹시 팝업이 있다면 닫고 종료
            close_btns = [t for t in targets if any(k in str(t[2]) for k in ["확인", "닫기"])]
            for btn in close_btns:
                self.adb.tap(btn[0], btn[1])
                time.sleep(0.5)
            raise self.SessionFinishedException()
        
        # [지루함 감지] 화면 내용이 3번 연속 똑같으면 탈출
        current_texts = sorted([str(t[2]) for t in targets])
        if current_texts == self.last_screen_texts and current_texts: # 빈 화면 제외
            self.stagnation_count += 1
            log.info(f"Stagnation Check: Screen is identical ({self.stagnation_count}/3)")
            if self.stagnation_count >= 3:
                log.warning("Screen frozen or stuck! Emergency escape: Pressing BACK 5 times...")
                for _ in range(5):
                    self.adb.back()
                    time.sleep(0.3)
                
                self.stagnation_count = 0
                self.last_screen_texts = []
                return False # 즉시 리턴하여 순찰 유도
        else:
            self.stagnation_count = 0
            self.last_screen_texts = current_texts
            
        # 2. 필터링
        valid_targets = []
        for t in targets:
            cx, cy, label, ttype = t
            # 메뉴는 DB 체크 (하루 1회)
            is_menu = any(m in str(label) for m in self.menu_keywords)
            if is_menu and self.db.is_already_harvested_today(label): continue
            
            # 좌표 중복 방지
            if any(abs(h[0]-cx) < 50 and abs(h[1]-cy) < 50 for h in self.clicked_history_temp): continue
            valid_targets.append(t)

        # 3. 클릭 실행 (한 번에 하나씩만! 화면 변화 대응)
        if valid_targets:
            # 우선순위 정렬 (이미지 > 텍스트)
            valid_targets.sort(key=lambda x: (0 if x[3] == "IMAGE" else 1, x[1]))
            
            # [수정] 가장 유력한 타겟 '딱 하나'만 골라 클릭
            target = valid_targets[0]
            cx, cy, label, ttype = target
            
            log.info(f"Action: Target identified -> '{label}' ({ttype}) at ({cx}, {cy})")
            self.adb.tap(cx, cy)
            
            if any(m in str(label) for m in self.menu_keywords):
                self.db.record_harvest(label)
            
            self.clicked_history_temp.append((cx, cy))
            if len(self.clicked_history_temp) > 500: self.clicked_history_temp.pop(0)
            
            # 클릭 후 화면 변화를 위해 짧게 대기 후 즉시 리턴 (다시 스캔하도록)
            wait_after_click = random.uniform(0.5, 1.0)
            log.info(f"Action: Waiting {wait_after_click:.1f}s for screen update...")
            time.sleep(wait_after_click)
            
            return True # 하나라도 클릭했으면 True 반환 -> 루프에서 다시 스캔됨
        
        return False # 클릭할 게 없으면 False -> 패트롤 실행

    def fast_patrol_move(self):
        """공통: 위아래 수직 탐색 (중앙 드래그 방식)"""
        action = random.choices(
            ["STAY", "DOWN", "UP"], 
            weights=[20, 60, 20]
        )[0]
        
        mid_x = self.width // 2
        mid_y = self.height // 2
        
        log.info(f"Patrol: Executing Vertical {action}...")
        
        if action == "STAY":
            self.scan_and_click_burst()
            
        elif action == "DOWN":
            y1, y2 = int(self.height * 0.8), int(self.height * 0.2)
            log.info("Patrol: Long Central DOWN Swipe...")
            self.adb.swipe(mid_x, y1, mid_x, y2, duration=1000)
            time.sleep(1.5)
            self.scan_and_click_burst()
            
        elif action == "UP":
            y1, y2 = int(self.height * 0.2), int(self.height * 0.8)
            log.info("Patrol: Long Central UP Swipe...")
            self.adb.swipe(mid_x, y1, mid_x, y2, duration=1000)
            time.sleep(1.5)
            self.scan_and_click_burst()
        
        # 마지막 확인 사격
        wait_time = random.uniform(1.5, 2.5)
        log.info(f"Patrol: Settle waiting {wait_time:.1f}s for final scan...")
        time.sleep(wait_time)
        self.scan_and_click_burst()

    def run_session(self, max_cycles=10):
        """한 앱을 일정 횟수(max_cycles)만큼 훑고 종료함"""
        log.info(f">>> [{self.package_name}] Session Started ({max_cycles} Cycles) <<<")
        
        cycle = 0
        current_sub_cycle = 0
        cycle_limit = random.randint(3, 5) # 탈출 주기
        
        self.launch_app() # 시작 시 앱 실행
        
        try:
            while cycle < max_cycles:
                if not self.is_app_running():
                    self.launch_app()
                    current_sub_cycle = 0
                    continue

                clicked = self.scan_and_click_burst()
                
                if not clicked:
                    current_sub_cycle += 1
                    log.info(f"Patrolling... (Sub: {current_sub_cycle}/{cycle_limit}, Total: {cycle}/{max_cycles})")
                    self.fast_patrol_move()
                    
                    if current_sub_cycle >= cycle_limit:
                        num_backs = random.randint(4, 6)
                        log.info(f"Action: Random Escape! BACK {num_backs} times...")
                        for _ in range(num_backs):
                            self.adb.back()
                            time.sleep(0.3)
                        current_sub_cycle = 0
                        cycle_limit = random.randint(3, 6)
                        self.clicked_history_temp = []
                        cycle += 1
                else:
                    current_sub_cycle = 0
                    time.sleep(0.5)
                    
        except self.SessionFinishedException:
            log.info(">>> Session Finished Early (Exit Trigger). <<<")
        
        log.info(f">>> [{self.package_name}] Session Finished. <<<")
        self.adb.stop_app(self.package_name)