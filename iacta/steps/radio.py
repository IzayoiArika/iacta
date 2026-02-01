import os
import shutil

from tqdm import tqdm
from mortis import SonglistItem

from iacta.types.chartpack import Chartpack
from iacta.types.config import Config
from iacta.types.exceptions.general import MultipleExceptions
from iacta.types.misc import ExtRatingClassEnum, RatingClassEnumExt
from iacta.utils import pick_biggest_image


def get_diff_title(songlist: SonglistItem, extcls: ExtRatingClassEnum) -> str:
	if extcls == RatingClassEnumExt.Base:
		return songlist.title_localized.en

	diff = songlist.difficulties[extcls]
	if diff and diff.title_localized and diff.title_localized.en:
		return diff.title_localized.en
	return songlist.title_localized.en

def get_diff_artist(songlist: SonglistItem, extcls: ExtRatingClassEnum) -> str:
	# similar to get_diff_title but for artist
	if extcls == RatingClassEnumExt.Base:
		return songlist.artist # type: ignore
		
	diff = songlist.difficulties[extcls]
	if diff and diff.artist:
		return diff.artist
	return songlist.artist # type: ignore

def sanitize_filename(name: str) -> str:
	return ''.join('_' if c in r'\/:*?"<>|' else c for c in name)

def collect_radio_files(chartpacks: list[Chartpack]) -> None:
	config = Config.instance
	errors = MultipleExceptions()

	radio_path = config.paths.radio
	try:
		if os.path.exists(radio_path):
			shutil.rmtree(radio_path)
		os.makedirs(radio_path, exist_ok=True)
	except Exception as e:
		errors.add(radio_path, e)

	with tqdm(chartpacks, leave=False) as bar:
		for chartpack in bar:
			bar.set_description(chartpack.id)

			assets: dict[str, str] = {}

			for extcls, name in chartpack.audio_names.items():
				title = get_diff_title(chartpack.songlist, extcls)
				src = os.path.join(chartpack.root, name)
				dst = os.path.join(radio_path, f'{sanitize_filename(title)} {name}')
				assets[src] = dst
			
			for extcls, names in chartpack.covers_names.items():
				src = pick_biggest_image(os.path.join(chartpack.root, name) for name in names)
				title = get_diff_title(chartpack.songlist, extcls)
				dst = os.path.join(radio_path, f'{sanitize_filename(title)} {extcls.value}.jpg')
				
				assets[src] = dst

			for src, dst in assets.items():
				try:
					shutil.copy2(src, dst)
				except Exception as e:
					errors.add(src, e)

	if errors:
		raise errors