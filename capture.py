import os
import time
import subprocess
from dotenv import load_dotenv

# 설정 로드
load_dotenv()
ADB_PATH = os.getenv("ADB_PATH", "adb")
DEVICE_ID = os.getenv("DEVICE_ID")
DISPLAY_ID = os.getenv("DISPLAY_ID")

def take_screenshot():
    # 1. 파일명 생성 (예: snap_20231226_123045.png)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"snap_{timestamp}.png"
    
    # ADB 기본 명령어 조합
    base_cmd = [ADB_PATH]
    if DEVICE_ID:
        base_cmd.extend(["-s", DEVICE_ID])
    
    print(f"[*] 화면 캡처 중 ({DEVICE_ID if DEVICE_ID else 'Default'}, Display {DISPLAY_ID if DISPLAY_ID else 'Auto'}): {filename}...")
    
    try:
        # 2. ADB 명령어로 캡처 및 가져오기
        d_opt = f"-d {DISPLAY_ID}" if DISPLAY_ID else ""
        subprocess.run(base_cmd + ["shell", "screencap", d_opt, "-p", "/sdcard/screen.png"], check=True)
        subprocess.run(base_cmd + ["pull", "/sdcard/screen.png", filename], check=True)
        
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
