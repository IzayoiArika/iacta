import json
import os
import random
import shutil

from PIL import Image

from mortis import SonglistItem
from iacta.types.chartpack import Chartpack
from iacta.types.config import Config
from iacta.types.misc import RatingClassEnumExt


def distribute_into_sessions(chartpacks: list[Chartpack]) -> dict[int, list[Chartpack]]:
	session_packs: dict[int, list[Chartpack]] = {}
	for chartpack in chartpacks:
		session = chartpack.event_info.live_session
		assert session
		if session not in session_packs:
			session_packs[session] = []
		session_packs[session].append(chartpack)
	return session_packs

def create_session_dirs(n: int) -> None:
	config = Config.instance
	for i in range(1, n + 1):
		session_str = f'第 {i} 场谱包'
		path = os.path.join(config.paths.chartpacks, session_str)
		if os.path.exists(path):
			shutil.rmtree(path)
		os.makedirs(path, exist_ok=True)

		for subdir in ('img/bg', 'songs', 'covers'):
			if os.path.exists(os.path.join(path, subdir)):
				shutil.rmtree(os.path.join(path, subdir))
			os.makedirs(os.path.join(path, subdir), exist_ok=True)

def backup_covers_to(chartpack: Chartpack, dst_path: str) -> None:
	if os.path.exists(dst_path):
		shutil.rmtree(dst_path)
	os.makedirs(dst_path, exist_ok=True)

	for src_list in chartpack.covers_names.values():
		for src_name in src_list:
			src = os.path.join(chartpack.root, src_name)
			dst = os.path.join(dst_path, src_name)
			shutil.copy2(src, dst)

def copy_assets_to(chartpack: Chartpack, dst_path: str) -> None:
	if os.path.exists(dst_path):
		shutil.rmtree(dst_path)
	os.makedirs(dst_path, exist_ok=True)

	for src in chartpack.assets_woimgs:
		dst = os.path.join(dst_path, os.path.basename(src))
		shutil.copy2(src, dst)

def copy_backgrounds_to(chartpack: Chartpack, dst_path: str) -> None:
	if os.path.exists(dst_path):
		shutil.rmtree(dst_path)
	os.makedirs(dst_path, exist_ok=True)

	for src_name in chartpack.background_names.values():
		src = os.path.join(chartpack.root, src_name)
		dst = os.path.join(dst_path, src_name)
		shutil.copy2(src, dst)
	
def assign_random_cover(chartpack: Chartpack, dst_path: str, choices: list[str]) -> None:
	config = Config.instance
	presets = config.chartpack.covers.preset_foolish_pics

	id = chartpack.id
	src = presets[id] if id in presets else random.choice(choices)

	with Image.open(src) as img:
		
		for template, size in config.chartpack.covers.normalize_to.items():
			resized = img.resize(size, Image.Resampling.LANCZOS)

			dst_name = template.build(RatingClassEnumExt.Base.value)
			dst = os.path.join(dst_path, dst_name)

			resized.save(dst, format='JPEG')

def mask_songlist(chartpack: Chartpack) -> SonglistItem:
	config = Config.instance
	masking = config.chartpack.songlist.masking

	copied = chartpack.songlist.model_copy()

	copied.artist = masking.artist
	copied.bpm = masking.bpm
	copied.title_localized.en = masking.song_title.build(
		event_name=config.event_name,
		live_id = chartpack.event_info.live_id
	)

	for diff in copied.difficulties.all_activated:
		for field in ('artist', 'title_localized', 'bpm'):
			if hasattr(diff, field):
				setattr(diff, field, None)
		diff.jacket_override = False

	return copied


def pack_zipfiles(chartpacks: list[Chartpack]) -> None:
	config = Config.instance
	session_packs = distribute_into_sessions(chartpacks)
	create_session_dirs(len(session_packs))

	foolish_pics: list[str] = [entry.path for entry in os.scandir(config.paths.foolish_pics) if entry.is_file()]

	for i, packs in session_packs.items():
		session_str = f'第 {i} 场谱包'
		session_dir = os.path.join(config.paths.chartpacks, session_str)
		bg_dir = os.path.join(session_dir, 'img/bg')
		
		original_songlists: list[dict] = []
		masked_songlists: list[dict] = []

		for pack in packs:
			pack_dir = os.path.join(session_dir, 'songs', pack.id)
			pack_cover_dir = os.path.join(session_dir, 'covers', pack.id)

			backup_covers_to(pack, pack_cover_dir)
			copy_backgrounds_to(pack, bg_dir)
			copy_assets_to(pack, pack_dir)
			assign_random_cover(pack, pack_dir, foolish_pics)

			original_songlists.append(pack.songlist.to_dict())
			masked_songlists.append(mask_songlist(pack).to_dict())
		
		original_songlist_path = os.path.join(session_dir, 'songs/songlist_original')
		with open(original_songlist_path, 'w', encoding='utf-8') as f:
			json.dump({'songs': original_songlists}, f, ensure_ascii=False, indent=4)
			
		masked_songlist_path = os.path.join(session_dir, 'songs/songlist')
		with open(masked_songlist_path, 'w', encoding='utf-8') as f:
			json.dump({'songs': masked_songlists}, f, ensure_ascii=False, indent=4)
		
		# make all files have the same modification time
		time = config.technical.file_edit_time
		for root, _, files in os.walk(session_dir):
			os.utime(root, (time, time))
			for filename in files:
				file_path = os.path.join(root, filename)
				os.utime(file_path, (time, time))
		
		shutil.make_archive(session_dir, 'zip', session_dir)
		shutil.rmtree(session_dir)