import time
import argparse
import random
from dotenv import load_dotenv
from src.apps.ok_cashbag import OKCashbagAgent
from src.apps.naver_pay import NaverPayAgent
from src.apps.l_point import LPointAgent
from src.apps.syrup import SyrupAgent
from src.logger import log

def main():
    # 1. 환경 변수 로드 (.env)
    load_dotenv()
    
    # 2. 명령행 인자 설정
    parser = argparse.ArgumentParser(description="Android Vision Auto Clicker")
    parser.add_argument(
        "apps", 
        nargs="*", 
        help="실행할 앱 이름을 입력하세요 (예: ok naver lpoint syrup)."
    )
    args = parser.parse_args()

    # 3. 에이전트 매핑 테이블
    agent_map = {
        "ok": OKCashbagAgent,
        "naver": NaverPayAgent,
        "lpoint": LPointAgent,
        "syrup": SyrupAgent
    }
    
    # 4. 실행할 대원 선발
    if args.apps:
        selected_agents_classes = []
        for app_name in args.apps:
            app_name = app_name.lower()
            if app_name in agent_map:
                selected_agents_classes.append(agent_map[app_name])
    else:
        selected_agents_classes = list(agent_map.values())

    if not selected_agents_classes:
        return

    try:
        # [최적화] 시작 시 화면 밝기를 80으로 설정 (사용자 요청)
        initial_agent = OKCashbagAgent()
        initial_agent.adb.set_brightness(80)
        
        global_cycle = 1
        while True:
            # [수정] 랜덤 셔플 제거 -> 순차적으로 실행하여 한 앱에 몰리는 현상 방지
            # random.shuffle(selected_agents_classes)
            
            for i, agent_class in enumerate(selected_agents_classes):
                agent = agent_class()
                try:
                    # [추가] 기기 연결 확인 및 대기 로직 (꽂다 안 꽂다 대응)
                    if not agent.adb.connect(quiet=True):
                        log.warning("Device disconnected. Waiting for connection...")
                        while not agent.adb.connect(quiet=True):
                            time.sleep(5)
                        log.info("Device reconnected! Resuming...")
                        # 재연결 후 화면 밝기 다시 세팅
                        agent.adb.set_brightness(80)

                    # 현재 진행 상황 출력 (예: Cycle 1 [1/4] SYRUP)
                    log.info(f"Cycle {global_cycle} [{i+1}/{len(selected_agents_classes)}] -> {agent.app_name.upper()}")
                    
                    max_cycles = getattr(agent, 'max_cycles', 3)
                    agent.run_session(max_cycles=max_cycles)
                    
                    time.sleep(random.uniform(3.0, 8.0))
                    
                except Exception as e:
                    log.error(f"에이전트 {agent.app_name} 실행 중 오류: {e}")
                    time.sleep(5)
            
            global_cycle += 1
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n[!] 프로그램 종료")

if __name__ == "__main__":
    main()
