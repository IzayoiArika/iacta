import os
import shutil
from zipfile import ZipFile

from iacta.types.config import Config
from iacta.types.exceptions.general import MultipleExceptions
from iacta.types.exceptions.file import NotAZipError


def _unzip_chartpack(entry: os.DirEntry[str]) -> str | None:
	config = Config.instance
	root = config.paths.root

	if not entry.is_file():
		entry_name = entry.name
		is_zip = False
	else:
		entry_name, ext = os.path.splitext(entry.name)
		ext = ext.lower().strip()
		is_zip = (ext == '.zip')

	if not is_zip:
		strat = config.preparation.nonzip_items
		if strat == 'ask':
			c = input(f'Path ({entry.path}) is not a zip file. What to do? (remove/ignore/*=halt): ').lower().strip()
			strat = c if c == 'remove' or c == 'ignore' else 'forbid'
		
		if strat == 'forbid':
			raise NotAZipError(entry.path)
		elif strat == 'ignore':
			pass
		elif strat == 'remove':
			os.remove(entry) if entry.is_file() else shutil.rmtree(entry)
		return None
	
	dst = os.path.join(root, entry_name)
	with ZipFile(entry, 'r') as zip:
		zip.extractall(dst)
	return dst


def unzip_chartpacks() -> tuple[list[str], MultipleExceptions]:
	config = Config.instance
	zipfiles = config.paths.zipfiles

	errors = MultipleExceptions()

	unzipped: list[str] = []
	for entry in os.scandir(zipfiles):
		try:
			dst = _unzip_chartpack(entry)
			if dst:
				unzipped.append(dst)
		except Exception as e:
			errors.add(entry.name, e)
	
	return unzipped, errors