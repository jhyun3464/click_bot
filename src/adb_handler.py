import subprocess
import os
import time
import re
from src.logger import log

class ADBHandler:
    def __init__(self, device_id=None, adb_path=None):
        self.device_id = device_id
        self.adb_path = adb_path or os.environ.get("ADB_PATH", "/mnt/c/platform-tools/adb.exe")

    def _get_base_cmd(self):
        cmd = [self.adb_path]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        return cmd

    def _run_command(self, cmd_args_str):
        adb_cmd = self._get_base_cmd()
        adb_cmd.extend(cmd_args_str.split())
        try:
            result = subprocess.run(adb_cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            if result.returncode == 0:
                return result.stdout.replace("\r", "").strip()
            else:
                log.error(f"ADB Error: {result.stderr.strip()}")
                return None
        except Exception as e:
            log.error(f"Exception running ADB: {e}")
            return None

    def connect(self, quiet=False):
        output = self._run_command("devices")
        if output is None: return False
        lines = output.splitlines()
        devices = [line.split()[0] for line in lines if "device" in line and not line.startswith("List")]
        if devices:
            new_id = devices[0]
            if self.device_id != new_id and not quiet:
                log.info(f"Connected to device: {new_id}")
            self.device_id = new_id
            return True
        if self.device_id is not None and not quiet:
            log.warning("Device disconnected.")
        self.device_id = None
        return False

    def screencap(self, local_path="screen.png"):
        # [강제 갱신] 기존 파일 삭제로 "전 화면(Old Screen)" 재탕 방지
        if os.path.exists(local_path):
            os.remove(local_path)
            
        self._run_command("shell screencap -p /sdcard/screen.png")
        pull_cmd = self._get_base_cmd() + ["pull", "/sdcard/screen.png", local_path]
        try:
            subprocess.run(pull_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                return local_path
            return None
        except:
            return None

    def tap(self, x, y, offset=3):
        import random
        # 오차 범위를 줄여서 글자 중앙을 더 정확히 조준
        rx, ry = x + random.randint(-offset, offset), y + random.randint(-offset, offset)
        # 150ms로 약간 여유를 줌 (너무 빠르면 기계로 오인)
        self._run_command(f"shell input swipe {rx} {ry} {rx} {ry} 150")
        time.sleep(random.uniform(0.05, 0.15)) # 터치 후 미세 대기

    def swipe(self, x1, y1, x2, y2, duration=300):
        log.info(f"Action: Swiping from ({x1}, {y1}) to ({x2}, {y2})")
        self._run_command(f"shell input swipe {x1} {y1} {x2} {y2} {duration}")

    def back(self):
        log.info("Action: Pressing BACK button")
        self._run_command("shell input keyevent 4")

    def launch_app(self, package_name="com.skmc.okcashbag.home_google"):
        log.info(f"Action: Launching app {package_name}")
        self._run_command(f"shell monkey -p {package_name} -c android.intent.category.LAUNCHER 1")
        time.sleep(7)

    def stop_app(self, package_name="com.skmc.okcashbag.home_google"):
        log.info(f"Action: Force stopping app {package_name}")
        self._run_command(f"shell am force-stop {package_name}")
        time.sleep(1)

    def get_current_package(self):
        """현재 전면에 떠 있는 앱의 패키지명을 가져옵니다."""
        output = self._run_command("shell dumpsys window displays")
        if output:
            # mCurrentFocus 파싱
            match = re.search(r'mCurrentFocus.*\s([a-zA-Z0-9\._]+)/', output)
            if match: return match.group(1)
            # mFocusedApp 파싱
            match = re.search(r'mFocusedApp.*\s([a-zA-Z0-9\._]+)/', output)
            if match: return match.group(1)
        
        # 최후의 수단
        output = self._run_command("shell dumpsys activity recents")
        if output:
            match = re.search(r'Recent #0:.*\{([a-zA-Z0-9\._]+)/', output)
            if match: return match.group(1)
        return None

    def get_screen_size(self):
        """기기의 실제 해상도(가로, 세로)를 가져옵니다."""
        output = self._run_command("shell wm size")
        if output:
            match = re.search(r'Physical size: (\d+)x(\d+)', output)
            if match:
                return int(match.group(1)), int(match.group(2))
        return 1080, 2400 # 기본값