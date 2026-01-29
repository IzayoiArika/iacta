import os
import shutil

from iacta.types.config import Config
from iacta.types.exceptions.general import UnreachableBranch
from iacta.types.exceptions.file import FolderNotEmptyError, PathNotFoundError


def clean_root():
	config = Config.instance
	root = config.paths.root

	if not os.path.exists(root):
		# if not exists
		strat = config.preparation.no_root_found
		if strat == 'create':
			os.makedirs(root)
			return
		elif strat == 'fail':
			raise PathNotFoundError(root)
		else:
			raise UnreachableBranch
	
	if not os.listdir(root):
		# already empty, do nothing
		return

	strat = config.preparation.cleaning_root
	if strat == 'ask':
		c = input(f'Root path is not empty. Sure to empty? (Y/*): ').lower().strip()
		strat = 'force' if c == 'y' else 'require_empty'

	if strat == 'force':
		pass
	elif strat == 'require_empty':
		raise FolderNotEmptyError(root)
	else:
		raise UnreachableBranch
	
	shutil.rmtree(root)
	os.makedirs(root)