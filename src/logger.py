import logging
import sys

def setup_logger():
    logger = logging.getLogger("OKBot")
    logger.setLevel(logging.INFO)

    # 포맷 설정: [시간] [로그레벨] 메시지
    formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )

    # 터미널 출력용 핸들러
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    
    if not logger.handlers:
        logger.addHandler(stream_handler)
    
    return logger

log = setup_logger()
