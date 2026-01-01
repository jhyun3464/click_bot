import sqlite3
from datetime import datetime
from src.logger import log

class DBHandler:
    def __init__(self, db_path="harvest_history.db"):
        self.db_path = db_path
        self._init_db()
        self._cleanup_old_data() # 시작할 때 어제 이전 데이터 삭제

    def _cleanup_old_data(self):
        """데이터 정리"""
        with sqlite3.connect(self.db_path) as conn:
            # 1. 지난 포인트 적립 기록 삭제 (하루만 유지)
            conn.execute("DELETE FROM harvest_history WHERE date(clicked_at) < date('now')")
            
            # 2. [수정] 메뉴 방문 기록은 봇 실행 시마다 초기화 (재방문 허용)
            conn.execute("DELETE FROM menu_history")
            
            conn.commit()
            conn.execute("VACUUM")
            log.info("DB Cleanup: Point history pruned, Menu history reset.")

    def _init_db(self):
        """DB 테이블 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS harvest_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    label TEXT NOT NULL,
                    clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_label_time ON harvest_history (label, clicked_at)")
            
            # [New] 메뉴 완료 기록 테이블
            conn.execute("""
                CREATE TABLE IF NOT EXISTS menu_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    menu_name TEXT NOT NULL,
                    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def is_already_harvested_today(self, label):
        """오늘 이미 해당 라벨을 클릭했는지 확인"""
        query = """
            SELECT 1 FROM harvest_history 
            WHERE label = ? AND date(clicked_at) = date('now')
            LIMIT 1
        """
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(query, (label,))
            return cur.fetchone() is not None

    def record_harvest(self, label):
        """클릭 기록 저장"""
        if not label: return
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO harvest_history (label) VALUES (?)", (label,))

    def is_menu_completed_today(self, menu_name):
        """오늘 해당 메뉴를 이미 순회했는지 확인"""
        query = """
            SELECT 1 FROM menu_history 
            WHERE menu_name = ? AND date(completed_at) = date('now')
            LIMIT 1
        """
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(query, (menu_name,))
            return cur.fetchone() is not None

    def record_menu_completion(self, menu_name):
        """메뉴 완료 기록 저장"""
        if not menu_name: return
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO menu_history (menu_name) VALUES (?)", (menu_name,))
