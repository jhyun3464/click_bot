import os
import time
import subprocess
from dotenv import load_dotenv

# 설정 로드
load_dotenv()
ADB_PATH = os.getenv("ADB_PATH", "adb")

def take_screenshot():
    # 1. 파일명 생성 (예: snap_20231226_123045.png)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"snap_{timestamp}.png"
    
    print(f"[*] 화면 캡처 중: {filename}...")
    
    try:
        # 2. ADB 명령어로 캡처 및 가져오기 (가장 안정적인 pull 방식 사용)
        subprocess.run([ADB_PATH, "shell", "screencap", "-p", "/sdcard/screen.png"], check=True)
        subprocess.run([ADB_PATH, "pull", "/sdcard/screen.png", filename], check=True)
        
        if os.path.exists(filename):
            print(f"[+] 성공! 파일이 저장되었습니다: {os.path.abspath(filename)}")
            # 윈도우라면 폴더를 열어줌 (선택 사항)
            if os.name == 'nt':
                os.startfile('.')
        else:
            print("[-] 실패: 파일을 가져오지 못했습니다.")
            
    except Exception as e:
        print(f"[-] 에러 발생: {e}")

if __name__ == "__main__":
    take_screenshot()
