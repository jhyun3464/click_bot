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
        # ADB, 비전 엔진, DB 핸들러 초기화
        self.adb = ADBHandler(adb_path=os.getenv("ADB_PATH"))
        self.vision = VisionEngine()
        self.db = DBHandler()
        
        # [해상도 최적화] 폴더블 7 등 대화면 기기의 실제 크기 측정
        self.width, self.height = self.adb.get_screen_size()
        log.info(f"기기 해상도 감지 완료: {self.width}x{self.height}")
        
        # .env에서 타겟 키워드 읽어오기
        raw_keys = os.getenv("TARGET_KEYWORDS", "").split(",")
        self.keywords = [k.strip() for k in raw_keys if k.strip()]
        
        # 메뉴형 키워드 (하루 한 번만 방문하도록 관리)
        self.menu_keywords = ["쉽게", "돈되는", "쇼핑", "오락", "혜택", "이벤트"]
        
        # 최근 클릭한 좌표 저장 (중복 클릭 방지용)
        self.clicked_history_temp = []

    def is_app_running(self):
        """OK캐시백 앱이 화면 전면에 실행 중인지 확인"""
        pkg = self.adb.get_current_package()
        return pkg and "com.skmc.okcashbag.home_google" in pkg

    def launch_app(self):
        """앱 복구 및 초기 광고 돌파 로직"""
        log.info("액션: 앱 복구 및 메인 화면 진입 시도...")
        
        # 클릭 연타 후 안정화를 위해 3~5초 랜덤 대기
        wait_time = random.uniform(3.0, 5.0)
        log.info(f"안정화 대기 중... ({wait_time:.1f}초)")
        time.sleep(wait_time)
        
        # 뒤로가기 5번으로 팝업이나 메뉴 탈출 시도
        log.info("뒤로가기 5번 연타로 화면 정리...")
        for _ in range(5):
            self.adb.back()
            time.sleep(0.5)
            
        # 그래도 앱이 안 뜨면 강제 재시작
        if not self.is_app_running():
            log.info("앱이 응답하지 않음. 강제 재시작 중...")
            self.adb.stop_app()
            time.sleep(1)
            self.adb.launch_app()
            time.sleep(6) # 로딩 대기
        
        # [초반 광고 돌파] 사용자 피드백 반영: 광고 밑(60% 지점)을 잡고 직선 스와이프
        log.info("초반 광고 돌파 제스처 실행...")
        safe_x = int(self.width * 0.1)   # 좌측 여백
        start_y = int(self.height * 0.6) # 광고 살짝 밑
        end_y = int(self.height * 0.15)  # 위로 밀기
        
        # 1단계: 수직 하강 (아래로 내리기)
        self.adb.swipe(safe_x, start_y, safe_x, end_y, duration=700)
        time.sleep(0.8)
        
        # 2단계: 수평 이동 (오른쪽 보기)
        log.info("오른쪽 콘텐츠 노출 시도 (좌측 스와이프)...")
        self.adb.swipe(int(self.width * 0.85), start_y, int(self.width * 0.15), start_y, duration=700)
        time.sleep(0.8)
        
        # 3단계: 마무리 바닥 밀기
        self.adb.swipe(safe_x, int(self.height * 0.9), safe_x, int(self.height * 0.1), duration=700)
        time.sleep(1.0)

    def scan_and_click_burst(self):
        """현재 화면에서 보이는 모든 포인트를 즉시 연타"""
        screen_path = self.adb.screencap()
        if not screen_path: return False
        
        targets = self.vision.find_targets(screen_path, self.keywords)
        valid_targets = []
        
        for t in targets:
            cx, cy, label, ttype = t
            # 메뉴 중복 방문 체크
            is_menu = any(m in label for m in self.menu_keywords)
            if is_menu and self.db.is_already_harvested_today(label): continue
            
            # 좌표 중복 클릭 방지 (반경 50px)
            if any(abs(h[0]-cx) < 50 and abs(h[1]-cy) < 50 for h in self.clicked_history_temp): continue
            valid_targets.append(t)

        if valid_targets:
            log.info(f"사냥감 발견! {len(valid_targets)}개 타겟 연타 시작...")
            for target in valid_targets:
                cx, cy, label, ttype = target
                log.info(f"클릭 -> '{label}' ({ttype}) 지점: ({cx}, {cy})")
                self.adb.tap(cx, cy) # 150ms 꾹 누르기
                
                if any(m in label for m in self.menu_keywords):
                    self.db.record_harvest(label)
                
                self.clicked_history_temp.append((cx, cy))
                if len(self.clicked_history_temp) > 500: self.clicked_history_temp.pop(0)
                
                # [안전] 사람처럼 보이게 랜덤 간격 (0.1~0.3초)
                time.sleep(random.uniform(0.1, 0.3))
            return True
        return False

    def fast_patrol_move(self):
        """입체적 화면 탐색 (우측 이동 후 하강, 정지 스캔 등)"""
        action = random.choices(
            ["STAY", "DOWN", "UP", "LEFT", "RIGHT", "COMPOUND"], 
            weights=[10, 30, 10, 10, 10, 30]
        )[0]
        
        safe_x = int(self.width * 0.08) # 좌측 여백 손잡이
        ry = random.randint(int(self.height * 0.3), int(self.height * 0.7))
        
        if action == "STAY":
            log.info("정지 순찰: 현재 화면 정밀 스캔 중...")
            self.scan_and_click_burst()
        elif action == "COMPOUND":
            # [핵심] 우측으로 크게 밀고, 그 화면에서 다시 아래로 랜덤하게 밀기 (느슨한 연결)
            log.info("Patrol: COMPOUND (Wide RIGHT then Random Vertical)")
            
            # 1. 가로: 화면 끝에서 끝까지
            start_x = int(self.width * 0.95)
            end_x = int(self.width * 0.05)
            self.adb.swipe(start_x, ry, end_x, ry, duration=400) 
            self.scan_and_click_burst()
            time.sleep(random.uniform(0.3, 0.8)) # 랜덤 대기
            
            # 2. 세로: 90% 확률로 움직임 (10%는 멈춰서 스캔만)
            if random.random() < 0.9:
                # 거리 랜덤 (Short / Medium / Long)
                dist_factor = random.choice([0.2, 0.5, 0.8])
                y1 = random.randint(int(self.height * 0.7), int(self.height * 0.9))
                y2 = y1 - int(self.height * dist_factor)
                
                log.info(f"Patrol: Follow-up DOWN (Factor {dist_factor})")
                self.adb.swipe(safe_x, y1, safe_x, max(100, y2), duration=400)
                self.scan_and_click_burst()
            else:
                log.info("Patrol: Skip vertical move (Stay & Scan)")
        elif action == "DOWN":
            log.info("이동: 아래로 길게 훑기...")
            y1, y2 = random.randint(int(self.height * 0.9), int(self.height * 0.98)), random.randint(int(self.height * 0.02), int(self.height * 0.1))
            self.adb.swipe(safe_x, y1, safe_x, y2, duration=700)
            self.scan_and_click_burst()
        elif action == "LEFT":
            log.info("이동: 왼쪽 페이지 확인 후 살짝 내리기...")
            # 1. 왼쪽으로 밀기 (좌측 여백 활용)
            self.adb.swipe(int(self.width * 0.05), ry, int(self.width * 0.95), ry, duration=600)
            self.scan_and_click_burst()
            time.sleep(0.3)
            
            # 2. 이어서 아래로 살짝 툭 내리기 (Short Down)
            y1 = random.randint(int(self.height * 0.5), int(self.height * 0.6))
            y2 = y1 - random.randint(150, 350)
            log.info(f"Patrol: Short DOWN follow-up from {y1} to {y2}")
            self.adb.swipe(safe_x, y1, safe_x, y2, duration=400)
            self.scan_and_click_burst()
            
        elif action == "RIGHT":
            log.info("이동: 오른쪽 페이지 확인 후 살짝 내리기...")
            self.adb.swipe(int(self.width * 0.95), ry, int(self.width * 0.05), ry, duration=600)
            self.scan_and_click_burst()
            y1, y2 = random.randint(int(self.height * 0.5), int(self.height * 0.6)), random.randint(int(self.height * 0.2), int(self.height * 0.4))
            self.adb.swipe(safe_x, y1, safe_x, y2, duration=400)
            self.scan_and_click_burst()
        elif action == "UP":
            log.info("이동: 위로 다시 올라가기...")
            self.adb.swipe(safe_x, int(self.height * 0.05), safe_x, int(self.height * 0.95), duration=700)
            self.scan_and_click_burst()
        
        time.sleep(random.uniform(0.3, 0.6))

    def run(self):
        log.info(">>> 울트라 불도저 봇 가동 시작 <<<")
        cycle_limit = random.randint(3, 5) # 탈출 주기
        current_cycle = 0
        
        while True:
            if not self.is_app_running():
                self.launch_app()
                current_cycle = 0
                continue

            # 1. 쉼 없이 사냥 시도
            clicked = self.scan_and_click_burst()
            
            if not clicked:
                # 먹을 게 없으면 순찰 강화
                current_cycle += 1
                log.info(f"현재 구역 공략 완료. 다음 구역으로 이동 중... ({current_cycle}/{cycle_limit})")
                self.fast_patrol_move()
                
                # 2. 일정 주기마다 다른 메뉴로 탈출 (랜덤 뒤로가기)
                if current_cycle >= cycle_limit:
                    num_backs = random.randint(5, 7)
                    log.info(f"랜덤 탈출 발동! 뒤로가기 {num_backs}번 연타...")
                    for _ in range(num_backs):
                        self.adb.back()
                        time.sleep(random.uniform(0.2, 0.5))
                    
                    # 리셋 및 기억 정화
                    current_cycle = 0
                    cycle_limit = random.randint(3, 6)
                    self.clicked_history_temp = [] 
            else:
                # 무언가 사냥했다면 기분 좋게 잠시 대기
                current_cycle = 0 
                time.sleep(random.uniform(0.3, 0.6))

if __name__ == "__main__":
    OKBot().run()
