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

    print("==========================================")
    print("   통합 포인트 수집기 (BULLDOZER SQUAD)")
    print("==========================================")
    
    # 3. 에이전트 매핑 테이블
    agent_map = {
        "ok": OKCashbagAgent,
        "naver": NaverPayAgent,
        "lpoint": LPointAgent,
        "syrup": SyrupAgent
    }
    
    # 4. 실행할 대원 선발
    selected_agents = []
    if args.apps:
        for app_name in args.apps:
            app_name = app_name.lower()
            if app_name in agent_map:
                selected_agents.append(agent_map[app_name]())
            else:
                log.error(f"알 수 없는 앱 이름입니다: {app_name}")
    else:
        # [수정] 인자가 없으면 도움말 출력 후 랜덤 순서로 가동
        print("\n[TIP] 특정 앱만 실행하려면: python3 main.py [ok|naver|lpoint|syrup]")
        print("[!] 인자가 없어 모든 대원을 랜덤 순서로 투입합니다.\n")
        
        # 모든 클래스 목록을 가져와서 섞기
        app_classes = list(agent_map.values())
        random.shuffle(app_classes)
        selected_agents = [cls() for cls in app_classes]

    if not selected_agents:
        log.error("실행할 수 있는 대원이 없습니다. 프로그램을 종료합니다.")
        return

    log.info("비율 기반 랜덤 로테이션 가동 시작 (OK: 50%, 엘포: 30%, 네이버: 10%, 시럽: 10%)")
    
    try:
        while True:
            # [사용자 요청 비율 적용]
            # OK(50), LPoint(30), Naver(10), Syrup(10)
            agent_class = random.choices(
                [OKCashbagAgent, LPointAgent, NaverPayAgent, SyrupAgent],
                weights=[50, 30, 10, 10],
                k=1
            )[0]
            
            agent = agent_class()
            
            try:
                log.info(f"====== [Selected: {agent.app_name.upper()}] ======")
                # 앱별 전용 사이클 수 적용
                max_cycles = getattr(agent, 'max_cycles', 3)
                agent.run_session(max_cycles=max_cycles)
                log.info(f"====== [Turn End: {agent.app_name.upper()}] ======")
                
                # 다음 앱으로 넘어가기 전 잠시 휴식
                wait_time = random.uniform(3.0, 7.0)
                log.info(f"Taking a short break ({wait_time:.1f}s) before next dispatch...")
                time.sleep(wait_time)
                
            except Exception as e:
                log.error(f"에이전트 {agent.app_name} 실행 중 오류: {e}")
                time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n[!] 프로그램 종료")

if __name__ == "__main__":
    main()

