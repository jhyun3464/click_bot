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
    def __init__(self, device_id=None, adb_path=None, display_id=None):
        self.device_id = device_id
        self.display_id = display_id
        # ADB 실행 파일 경로 설정
        self.adb_path = adb_path or os.environ.get("ADB_PATH", "adb")
        
        # [안정성] 연속 에러 카운터
        self.consecutive_errors = 0

    def _get_base_cmd(self):
        """ADB 기본 명령어를 생성합니다."""
        cmd = [self.adb_path]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        return cmd

    def _run_command(self, cmd_args_str, ignore_errors=False):
        """ADB 명령을 쉘에서 실행합니다. (에러 감지 및 자동 지연/복구 포함)"""
        
        # [에러 누적 시 지연 로직]
        if self.consecutive_errors >= 3:
            log.warning(f"ADB Unstable ({self.consecutive_errors} fails). Pausing 5s...")
            time.sleep(5)
            
        # [심각한 에러 시 ADB 서버 리셋]
        if self.consecutive_errors >= 5:
            log.error("ADB Critical Error. Restarting ADB Server...")
            try:
                subprocess.run([self.adb_path, "kill-server"])
                time.sleep(2)
                subprocess.run([self.adb_path, "start-server"])
                time.sleep(5)
                self.consecutive_errors = 0 # 리셋 후 재시도 기회 부여
            except:
                pass

        adb_cmd = self._get_base_cmd()
        adb_cmd.extend(cmd_args_str.split())
        try:
            result = subprocess.run(adb_cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            if result.returncode == 0:
                # [성공 시] 에러 카운터 초기화
                if self.consecutive_errors > 0:
                    log.info("ADB Connection Recovered.")
                self.consecutive_errors = 0
                return result.stdout.replace("\r", "").strip()
            else:
                # [실패 시]
                if not ignore_errors:
                    log.error(f"ADB 오류: {result.stderr.strip()}")
                self.consecutive_errors += 1
                return None
        except Exception as e:
            if not ignore_errors:
                log.error(f"ADB 실행 예외: {e}")
            self.consecutive_errors += 1
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
        # [수정] 다중 디스플레이 대응 (-d 옵션)
        d_opt = f"-d {self.display_id}" if self.display_id else ""
        self._run_command(f"shell screencap {d_opt} -p /sdcard/screen.png")
        
        pull_cmd = self._get_base_cmd() + ["pull", "/sdcard/screen.png", local_path]
        try:
            subprocess.run(pull_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                return local_path
            return None
        except Exception:
            return None

    def tap(self, x, y, offset=5):
        """특정 좌표를 사람처럼 자연스럽게 누릅니다 (클릭 씹힘 방지)."""
        import random
        # 1. 좌표 랜덤 오차 (Jitter) 적용
        rx = x + random.randint(-offset, offset)
        ry = y + random.randint(-offset, offset)
        
        # 2. 누르는 시간 (Duration) 랜덤화: 80ms ~ 250ms (가볍게 톡 ~ 지긋이 꾹)
        duration = random.randint(80, 250)
        
        # 3. 아주 미세한 드래그 효과 (사람은 완벽한 점을 클릭하지 않음)
        # 시작점과 끝점에 미세한 차이를 두어 터치 인식을 돕습니다.
        end_rx = rx + random.randint(-2, 2)
        end_ry = ry + random.randint(-2, 2)
        
        self._run_command(f"shell input swipe {rx} {ry} {end_rx} {end_ry} {duration}")
        
        # 4. 클릭 후 안정화 대기 (화면 반응 기다림)
        time.sleep(random.uniform(0.3, 0.6))

    def swipe(self, x1, y1, x2, y2, duration=300):
        """화면을 한 지점에서 다른 지점으로 밉니다."""
        self._run_command(f"shell input swipe {x1} {y1} {x2} {y2} {duration}")

    def back(self):
        """기기의 '뒤로가기' 버튼을 누릅니다."""
        self._run_command("shell input keyevent 4")

    def launch_app(self, package_name="com.skmc.okcashbag.home_google"):
        """특정 패키지명의 앱을 실행합니다. (Monkey -> am start 순차 시도)"""
        # 1. Monkey로 실행 시도 (Launcher 카테고리 명시 + 에러 무시)
        self._run_command(f"shell monkey -p {package_name} -c android.intent.category.LAUNCHER 1", ignore_errors=True)
        time.sleep(2)
        
        # 실행 확인
        if self.get_current_package() == package_name:
            time.sleep(4) # 추가 로딩 대기
            return

        log.warning(f"ADB: Monkey launch failed for {package_name}. Trying fallback...")

        # 2. 실패 시 Monkey 기본 모드 재시도
        self._run_command(f"shell monkey -p {package_name} 1", ignore_errors=True)
        time.sleep(2)
        
        if self.get_current_package() == package_name:
            time.sleep(4)
            return
            
        # 3. 그래도 안 되면 Main Activity 찾아서 am start 시도 (Android 7+)
        # cmd package resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.LAUNCHER <package>
        try:
            cmd = f"shell cmd package resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.LAUNCHER {package_name}"
            output = self._run_command(cmd, ignore_errors=True)
            
            if output and "/" in output:
                lines = output.strip().splitlines()
                # 마지막 줄이 보통 activity 경로임
                activity = lines[-1].strip()
                if "/" in activity and package_name in activity:
                    log.info(f"ADB: Launching via am start ({activity})")
                    self._run_command(f"shell am start -n {activity}", ignore_errors=True)
                    time.sleep(5)
                    return
        except:
            pass
            
        log.error(f"ADB: Failed to launch app {package_name} with all methods.")
        time.sleep(1)

    def stop_app(self, package_name="com.skmc.okcashbag.home_google"):
        """앱을 강제 종료합니다."""
        self._run_command(f"shell am force-stop {package_name}")
        time.sleep(1)

    def get_current_package(self):
        """현재 화면 전면에 떠 있는 앱의 패키지명을 가져옵니다."""
        output = self._run_command("shell dumpsys window displays")
        if output:
            match = re.search(r'mCurrentFocus.*\s([a-zA-Z0-9\._]+)/', output)
            if match: return match.group(1)
            match = re.search(r'mFocusedApp.*\s([a-zA-Z0-9\._]+)/', output)
            if match: return match.group(1)
        return None

    def get_screen_size(self):
        """기기의 실제 해상도(가로, 세로)를 조회합니다."""
        # [수정] 특정 디스플레이의 크기 조회
        d_opt = f"-d {self.display_id}" if self.display_id else ""
        output = self._run_command(f"shell wm size {d_opt}")
        if output:
            match = re.search(r'Physical size: (\d+)x(\d+)', output)
            if match:
                return int(match.group(1)), int(match.group(2))
        return 1080, 2400 # 기본값 (실패 시)

    def get_ui_xml(self):
        """화면의 UI 구조(XML)를 덤프하여 가져옵니다. (재시도 로직 포함)"""
        temp_file = "/sdcard/window_dump.xml"
        
        for attempt in range(3):
            # 0. UIAutomator 서비스 리셋 (교착 상태 방지)
            if attempt > 0:
                self._run_command("shell pkill uiautomator", ignore_errors=True)
                time.sleep(0.5)

            # 1. 기존 덤프 파일 삭제
            self._run_command(f"shell rm {temp_file}", ignore_errors=True)
            
            # 2. UI 덤프 시도
            dump_output = self._run_command(f"shell uiautomator dump {temp_file}", ignore_errors=True)
            
            # 덤프 명령 자체가 실패했거나 에러 메시지를 반환한 경우
            if dump_output and "ERROR" in dump_output:
                log.warning(f"ADB: UI dump attempt {attempt+1} failed: {dump_output}")
                continue

            # [안정화] 덤프 파일 생성 대기
            time.sleep(0.5 + (attempt * 0.5))
            
            # 3. 파일 내용 읽기 (파일이 없으면 에러 무시하고 None 반환됨)
            output = self._run_command(f"shell cat {temp_file}", ignore_errors=True)
            
            # 4. 결과 확인 및 반환
            if output and "<?xml" in output:
                return output
            
        log.warning("ADB: UI XML dump failed after 3 attempts.")
        return None

    def set_brightness(self, value):
        """화면 밝기를 조절합니다 (0~255)."""
        log.info(f"Action: Setting brightness to {value}")
        # 수동 모드로 변경
        self._run_command("shell settings put system screen_brightness_mode 0")
        # 밝기 값 적용
        self._run_command(f"shell settings put system screen_brightness {value}")
