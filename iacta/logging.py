import logging
import os

from tqdm import tqdm

class TqdmLoggingHandler(logging.Handler):
	def emit(self, record):
		try:
			msg = self.format(record)
			tqdm.write(msg, end='\n')
		except Exception:
			self.handleError(record)

class Logger:
	file_path: str
	formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
	stream_handler = TqdmLoggingHandler()

	@classmethod
	def _init(cls) -> None:
		cls.logger = logging.getLogger('general')
		cls.logger.setLevel(logging.INFO)
		cls.logger.addHandler(cls.stream_handler)

		cls.dbglogger = logging.getLogger('dbg')
		cls.dbglogger.setLevel(logging.DEBUG)

	@classmethod
	def _load_file_handler(cls, path: str) -> None:
		cls.file_handler = logging.FileHandler(path, encoding='utf-8')
		cls.file_handler.setFormatter(cls.formatter)

		cls.logger.addHandler(cls.file_handler)
		cls.dbglogger.addHandler(cls.file_handler)
	
	@classmethod
	def redirect_file(cls, path: str) -> None:
		cls.logger.handlers = [cls.stream_handler]
		cls.dbglogger.handlers = []
		cls._load_file_handler(path)

Logger._init()
logger = Logger.logger
dbglogger = Logger.dbglogger


def log_error(e: Exception, msg: str | None = None):
	if msg:
		logger.error(msg)
	logger.error(f'[{type(e).__name__}]')
	logger.error(f'{e}')

def log_sep() -> None:
	logger.info('=' * 50)