from src.bot import OKBot

def main():
    """
    OK캐시백 자동 클릭 봇의 메인 실행 진입점입니다.
    """
    print("==========================================")
    print("   OK Cashbag 불도저 봇 가동 시작")
    print("==========================================")
    
    try:
        # 봇 인스턴스 생성
        bot = OKBot()
        
        # 무한 루프 모드로 봇 실행
        # 이 함수 내부에서 앱 생존 확인, 스캔, 클릭, 스크롤이 무한 반복됩니다.
        bot.run()
        
    except KeyboardInterrupt:
        # 사용자가 Ctrl+C를 눌렀을 때의 안전한 종료 처리
        print("\n[!] 사용자에 의해 프로그램이 중단되었습니다.")
        
    except Exception as e:
        # 실행 중 발생할 수 있는 예외 상황 출력
        print(f"\n[X] 예기치 않은 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    main()