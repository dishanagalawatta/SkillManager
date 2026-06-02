import logging

from skill_manager.app import main
from skill_manager.core.config import DATA_DIR


def setup_logging():
    log_file = DATA_DIR / "skill_manager.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding="utf-8")
        ]
    )

if __name__ == "__main__":
    setup_logging()
    main()
