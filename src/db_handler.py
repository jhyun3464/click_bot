from src.logger import log

class DBHandler:
    """
    SQLite DB 대신 메모리(Set)를 사용하는 더미 핸들러입니다.
    DB 잠금 문제 및 복잡성을 피하기 위해 수정되었습니다.
    """
    def __init__(self, db_path=None):
        self.harvested_today = set()
        self.menu_completed = set()
        log.info("DB: SQLite disabled. Using In-Memory storage for this session.")

    def is_already_harvested_today(self, label):
        """이 세션에서 이미 클릭했는지 확인"""
        return label in self.harvested_today

    def record_harvest(self, label):
        """클릭 기록 저장"""
        if label:
            self.harvested_today.add(label)

    def is_menu_completed_today(self, menu_name):
        """이 세션에서 메뉴를 완료했는지 확인"""
        return menu_name in self.menu_completed

    def record_menu_completion(self, menu_name):
        """메뉴 완료 기록 저장"""
        if menu_name:
            self.menu_completed.add(menu_name)