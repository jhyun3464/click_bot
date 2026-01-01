import subprocess
import os
import time
import re
from src.logger import log

class ADBHandler:
    """
    ADB(Android Debug Bridge)를 통해 기기를 제어하는 클래스입니다.
    터치, 스와이프, 스크린샷 등의 기본 액션을 수행합니다.
    """
    def __init__(self, device_id=None, adb_path=None):
        self.device_id = device_id
        # ADB 실행 파일 경로 설정
        self.adb_path = adb_path or os.environ.get("ADB_PATH", "adb")

    def _get_base_cmd(self):
        """ADB 기본 명령어를 생성합니다."""
        cmd = [self.adb_path]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        return cmd

    def _run_command(self, cmd_args_str):
        """ADB 명령을 쉘에서 실행합니다."""
        adb_cmd = self._get_base_cmd()
        adb_cmd.extend(cmd_args_str.split())
        try:
            result = subprocess.run(adb_cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            if result.returncode == 0:
                return result.stdout.replace("\r", "").strip()
            else:
                log.error(f"ADB 오류: {result.stderr.strip()}")
                return None
        except Exception as e:
            log.error(f"ADB 실행 예외: {e}")
            return None

    def connect(self, quiet=False):
        """연결된 기기가 있는지 확인하고 첫 번째 기기에 연결합니다."""
        output = self._run_command("devices")
        if output is None: return False
        lines = output.splitlines()
        devices = [line.split()[0] for line in lines if "device" in line and not line.startswith("List")]
        if devices:
            new_id = devices[0]
            if self.device_id != new_id and not quiet:
                log.info(f"기기에 연결됨: {new_id}")
            self.device_id = new_id
            return True
        self.device_id = None
        return False

    def screencap(self, local_path="screen.png"):
        """기기 화면을 캡처하여 로컬로 가져옵니다."""
        # [강제 갱신] 기존 파일을 삭제하여 "전 화면" 재탕 방지
        if os.path.exists(local_path):
            os.remove(local_path)
            
        # 폰 내부에 저장 후 가져오기 (가장 안정적인 방식)
        self._run_command("shell screencap -p /sdcard/screen.png")
        pull_cmd = self._get_base_cmd() + ["pull", "/sdcard/screen.png", local_path]
        try:
            subprocess.run(pull_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                return local_path
            return None
        except Exception:
            return None

    def tap(self, x, y, offset=3):
        """특정 좌표를 꾹 누릅니다 (클릭 씹힘 방지)."""
        import random
        # 오차 범위를 줄여서 타겟 중앙을 정밀 조준
        rx, ry = x + random.randint(-offset, offset), y + random.randint(-offset, offset)
        # 150ms 동안 swipe하여 지긋이 누르는 효과 (인간다운 클릭)
        self._run_command(f"shell input swipe {rx} {ry} {rx} {ry} 150")
        # 클릭 후 안정화를 위한 아주 짧은 대기
        time.sleep(random.uniform(0.05, 0.15))

    def swipe(self, x1, y1, x2, y2, duration=300):
        """화면을 한 지점에서 다른 지점으로 밉니다."""
        self._run_command(f"shell input swipe {x1} {y1} {x2} {y2} {duration}")

    def back(self):
        """기기의 '뒤로가기' 버튼을 누릅니다."""
        self._run_command("shell input keyevent 4")

    def launch_app(self, package_name="com.skmc.okcashbag.home_google"):
        """특정 패키지명의 앱을 실행합니다."""
        self._run_command(f"shell monkey -p {package_name} -c android.intent.category.LAUNCHER 1")
        time.sleep(7)

    def stop_app(self, package_name="com.skmc.okcashbag.home_google"):
        """앱을 강제 종료합니다."""
        self._run_command(f"shell am force-stop {package_name}")
        time.sleep(1)

    def get_current_package(self):
        """현재 화면 전면에 떠 있는 앱의 패키지명을 가져옵니다."""
        output = self._run_command("shell dumpsys window displays")
        if output:
            match = re.search(r'mCurrentFocus.*
    ([a-zA-Z0-9\._]+)/', output)
            if match: return match.group(1)
            match = re.search(r'mFocusedApp.*
    ([a-zA-Z0-9\._]+)/', output)
            if match: return match.group(1)
        return None

    def get_screen_size(self):
        """기기의 실제 해상도(가로, 세로)를 조회합니다."""
        output = self._run_command("shell wm size")
        if output:
            match = re.search(r'Physical size: (\d+)x(\d+)', output)
            if match:
                return int(match.group(1)), int(match.group(2))
        return 1080, 2400 # 기본값 (실패 시)
