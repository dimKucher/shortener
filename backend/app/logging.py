from loguru import logger
import sys


class LoggerConfig:
    """Синглтон класс для конфигурации loguru"""

    _instance = None
    _formats = {
        "DEBUG": "<blue>{level: ^10}</blue> "
                 "| <blue>{name}:{function}:{line}</blue> - <blue>{message}</blue> \n",

        "INFO": "<white>{level: ^10}</white> "
                "| <white>{message}</white>\n",

        "SUCCESS": "<black><bg green><bold>{level: ^10}</bold></bg green></black> "
                   "| <green>{message}</green>\n",

        "WARNING": "<yellow><bold>{level: ^10}</bold></yellow> "
                   "| <yellow>{name}:{function}:{line}</yellow> - "
                   "<yellow>{message}</yellow>\n",

        "ERROR": "<white><bg red><bold>{level: ^10}</bold></bg red></white> "
                 "| <red><bold>{name}:{function}:{line}</bold></red> - "
                 "<red>{message}</red>\n",

        "CRITICAL": "<white><bg magenta><bold>{level: ^10}</bold></bg magenta></white> "
                    "| <magenta>{name}:{file}:{line}</magenta> - "
                    "<bold><red>{message}</red></bold>\n",
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._setup()
        return cls._instance

    def _setup(self):
        logger.remove()
        logger.add(
            sys.stdout,
            format=lambda r: self._formats.get(r["level"].name, self._formats["INFO"]),
            colorize=True
        )

    @property
    def logger(self):
        return logger


def get_logger():
    """Возвращает настроенный логгер"""
    return logger
