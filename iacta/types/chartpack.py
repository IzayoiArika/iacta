import os
from os import DirEntry
from typing import Literal

from tqdm import tqdm

from mortis import AFF, Arc, ArcType, Backgrounds, HitsoundStr, RatingClassEnum as Rtcls, SonglistItem
from pydub import AudioSegment
from PIL import Image

from iacta.types.config import Config
from iacta.types.event_info import EventInfoItem
from iacta.types.exceptions.general import MultipleExceptions, UnreachableBranch
from iacta.types.exceptions.file import AmbiguousSonglistError, BadChartpackError, MissingSonglistError, PathNotFoundError
from iacta.types.misc import DurationMs, ExtRatingClassEnum as ExtRtcls, RatingClassEnumExt
from iacta.types.songlist.extmodel import SpSonglistItem
from iacta.utils import pick_biggest_image


class Chartpack:
	def __init__(self, path: str) -> None:
		self.reset(path)
	
	@property
	def id(self) -> str:
		return self.songlist.id
	
	def reassign_id(self, new_id: str) -> None:
		if self.id == new_id:
			return
		self.songlist.id = new_id
	
	def reset_root(self, new_root_name: str) -> None:
		current = os.path.basename(self.root)
		if current == new_root_name:
			return
		
		parent = os.path.dirname(self.root)
		new_root = os.path.join(parent, new_root_name)
		os.rename(self.root, new_root)
		self.root = new_root
	
	def reset(self, path: str) -> None:
		self.root: str = path
		self.errors = MultipleExceptions()
		
		self.songlist_name: str
		self.songlist: SonglistItem
		self.event_info: EventInfoItem

		self.aff_names: dict[Rtcls, str] = {}
		self._affs_temp: dict[Rtcls, AFF] = {}

		self.hitsounds: set[HitsoundStr] = set()
		self._hitsound_audios_temp: dict[HitsoundStr, AudioSegment] = {}
		
		self.audio_names: dict[ExtRtcls, str] = {}
		self._audios_temp: dict[ExtRtcls, AudioSegment] = {}
		self.preview_names: dict[ExtRtcls, str] = {}

		self.covers_names: dict[ExtRtcls, list[str]] = {}
		self._covers_temp: dict[ExtRtcls, Image.Image] = {}

		self.background_names: dict[str, str] = {}
		self._backgrounds_temp: dict[str, Image.Image] = {}

		self.process()
		
	################################################################################################################

	def process(self) -> None:
		try:
			self.process_all()
			if self.errors:
				raise self.errors
			self.solve_category()
		except Exception as e:
			raise BadChartpackError(self.root, e)

	@property
	def is_bonus(self) -> bool:
		if self.event_info:
			return self.event_info.is_bonus
		raise ValueError(f'No event info is provided')

	@property
	def category(self) -> Literal['A', 'B', 'C']:
		if self.event_info and self.event_info.category:
			return self.event_info.category
		raise ValueError(f'No category info is provided')

	@property
	def assets(self) -> list[str]:
		return list(map(lambda x: os.path.join(self.root, x), self.asset_names))
	
	@property
	def assets_woimgs(self) -> list[str]:
		return list(map(lambda x:  os.path.join(self.root, x), self.assets_names_woimgs))
	
	@property
	def assets_names_woimgs(self) -> list[str]:
		result = [self.songlist_name]
		result.extend(self.aff_names.values())
		result.extend(unwrapped for hitsound in self.hitsounds if (unwrapped := hitsound.unwrap()) is not None)
		
		result.extend(self.audio_names.values())
		result.extend(self.preview_names.values())
		return result

	@property
	def asset_names(self) -> list[str]:
		result = self.assets_names_woimgs
		result.extend(self.background_names.values())
		for covers in self.covers_names.values():
			result.extend(covers)
		return result

	################################################################################################################

	def process_all(self) -> None:
		steps = {
			'songlist': self.process_songlist,
			'AFF / 特殊音频': self.process_affs,
			'曲绘': self.process_covers,
			'音源': self.process_audios,
			'背景': self.process_backgrounds,
			'清理冗余文件': self.remove_redundant,
		}

		with tqdm(total=len(steps), unit='step', leave=False) as bar:
			for step_name, step in steps.items():
				bar.set_description(step_name)
				step()
				bar.update()

	def solve_category(self) -> None:
		self.event_info.category = 'B' if self.is_bonus else ('C' if len(self.event_info.charters) >= 2 else 'A')

	################################################################################################################

	def process_songlist(self) -> None:
		self.reset_songlist()
		self.find_songlist()
		self.load_songlist()
		# self.check_songlist()  # auto-checked by Pydantic models
		self.normalize_songlist()
	
	def reset_songlist(self) -> None:
		for attr in ['songlist_path', 'songlist', 'event_info']:
			try:
				delattr(self, attr)
			except AttributeError:
				pass

	def find_songlist(self) -> None:
		config = Config.instance

		self.songlist_name: str

		entries: list[DirEntry[str]] = []
		for entry in os.scandir(self.root):
			if not entry.is_file():
				continue

			if entry.name in config.songlist.accepts:
				entries.append(entry)
			
		entry_count = len(entries)
		if entry_count == 0:
			raise MissingSonglistError(self.root)
		if entry_count == 1:
			self.songlist_name = entries[0].name
			return
		
		choice = 0
		strat = config.songlist.choosing

		if strat == 'ask':
			print('Multiple songlist files found: ')
			for i, entry in enumerate(entries):
				print(f'[{i:2d}] {entry}')
			choice = input('Please choose one: ')
			while True:
				try:
					choice = int(choice)
					self.songlist_name = entries[choice].name
					break
				except (ValueError, TypeError, IndexError):
					choice = input(f'Value must be an integer in range [0, {entry_count-1}]')

		elif strat == 'by_priority':
			for name in config.songlist.accepts:
				for i, entry in enumerate(entries):
					if entry.name == name:
						self.songlist_name = entry.name
						return
			raise UnreachableBranch
		
		elif strat == 'forbid':
			raise AmbiguousSonglistError(self.root, entries)
		elif strat == 'take_first':
			self.songlist_name = entries[0].name
		else:
			raise UnreachableBranch
	
	def load_songlist(self) -> None:
		config = Config.instance

		self.songlist: SonglistItem
		self.event_info: EventInfoItem
	
		songlist_path = os.path.join(self.root, self.songlist_name)
		with open(songlist_path, 'r', encoding='utf-8') as f:
			raw = f.read()

		raw = raw.strip()
		strat = config.songlist.tail_comma
		if strat == 'allow':
			if raw.endswith(','):
				raw = raw[:-1]
		elif strat == 'forbid':
			pass
		elif strat == 'require':
			if not raw.endswith(','):
				raise ValueError(f'Songlist must end with a comma')
			raw = raw[:-1]
		else:
			raise UnreachableBranch

		sp_songlist = SpSonglistItem.loads(raw)
		self.songlist = sp_songlist.norm_songlist()
		self.event_info = sp_songlist.event_info

	def normalize_songlist(self) -> None:
		config = Config.instance
		dst_name = config.songlist.normalize_to

		src = os.path.join(self.root, self.songlist_name)
		dst = os.path.join(self.root, dst_name)
		try:
			os.remove(src)
			self.songlist.dump_to_path(dst, indent=4)
			self.songlist_name = dst_name
		except Exception as e:
			basename = os.path.basename(dst)
			self.errors.add(basename, e)

	################################################################################################################

	def process_affs(self) -> None:
		self.reset_affs()
		self.find_affs()
		self.load_affs()
		self.process_hitsounds()
		self.check_affs()
		self.check_nonbonus_affs()
		self.normalize_affs()
		self.free_affs()

	def reset_affs(self) -> None:
		self.aff_names: dict[Rtcls, str] = {}
		self._affs_temp: dict[Rtcls, AFF] = {}

	def find_affs(self) -> None:
		self.aff_names: dict[Rtcls, str]

		for diff in self.songlist.difficulties.all_activated:
			rtcls = diff.rating_class
			basename = f'{rtcls.value}.aff'
			path = os.path.join(self.root, basename)

			if os.path.exists(path):
				self.aff_names[rtcls] = basename
				continue
			self.errors.add(basename, PathNotFoundError(path))
				
	def load_affs(self) -> None:
		self._affs_temp: dict[Rtcls, AFF]

		for rtcls, basename in self.aff_names.items():
			aff_path = os.path.join(self.root, basename)
			try:
				aff = AFF.load_from_path(aff_path)
				self._affs_temp[rtcls] = aff
			except Exception as e:
				self.errors.add(basename, e)
	
	def check_affs(self) -> None: 
		for rtcls, aff in self._affs_temp.items():
			aff_name = self.aff_names[rtcls]

			for i, group in enumerate(aff.iter_groups()):
				group_name = aff_name + f' [tg #{i}]'
				if group.anglex is not None:
					self.errors.add(group_name, 'Parameter \'anglex\' is banned')
				if group.angley is not None:
					self.errors.add(group_name, 'Parameter \'angley\' is banned')
				
				for j, event in enumerate(group.iter_events()):
					event_name = group_name + f' [event #{j}] ({type(event).__name__})'
					if isinstance(event, Arc):
						if event.type_ == ArcType.Designant:
							self.errors.add(event_name, f'Parameter value \'{ArcType.Designant}\' for \'type_\' is banned')
						if event.smoothness is not None:
							self.errors.add(event_name, f'Parameter \'smoothness\' is banned')
	
	def check_nonbonus_affs(self) -> None:
		if self.event_info.is_bonus:
			return
		
		config = Config.instance
		for rtcls, aff in self._affs_temp.items():
			tpdf = aff.unwrap_tpdf()
			mintpdf, maxtpdf = config.chartpack.aff.tpdf_range
			if tpdf <= maxtpdf and tpdf >= mintpdf:
				continue

			if tpdf < mintpdf:
				msg = f'TPDF falls under minimum {mintpdf} (got {tpdf})'
			else:
				msg = f'TPDF exceeds maximum {maxtpdf} (got {tpdf})'
			
			aff_name = self.aff_names[rtcls]
			self.errors.add(aff_name, msg)

	def normalize_affs(self) -> None:
		for rtcls, aff in self._affs_temp.items():
			dst_name = f'{rtcls.value}.aff'
			dst = os.path.join(self.root, dst_name)
			try:
				aff.dump_to_path(dst)
			except Exception as e:
				self.errors.add(dst_name, e)
				continue
			self.aff_names[rtcls] = dst_name
	
	def free_affs(self) -> None:
		del self._affs_temp


	def process_hitsounds(self) -> None:
		self.reset_hitsounds()
		self.find_hitsounds()
		self.rename_hitsounds()
		self.load_hitsounds()
		self.normalize_hitsounds()
		self.free_hitsounds()

	def reset_hitsounds(self) -> None:
		self.hitsounds: set[HitsoundStr] = set()
		self._hitsound_audios_temp: dict[HitsoundStr, AudioSegment] = {}

	def find_hitsounds(self) -> None:
		self.hitsounds: set[HitsoundStr]

		hitsounds: set[HitsoundStr] = set()
		for aff in self._affs_temp.values():
			hitsounds |= aff.required_hitsounds
		
		for hitsound in hitsounds:
			basename = hitsound.unwrap()
			assert basename is not None
			path = os.path.join(self.root, basename)
			if os.path.exists(path):
				self.hitsounds.add(hitsound)
				continue
			self.errors.add(basename, PathNotFoundError(path))

	def rename_hitsounds(self) -> None:
		to_modify: dict[HitsoundStr, HitsoundStr] = {}
		for hitsound in self.hitsounds:
			basename = hitsound.unwrap()
			assert basename is not None
			
			name, ext = os.path.splitext(basename)
			dst_name = f'{name}.wav'
			new_hitsound = HitsoundStr(dst_name)
			
			if ext == '.wav':
				# No need to rename
				continue

			if new_hitsound in self.hitsounds:
				self.errors.add(basename, f'Failed to rename to {dst_name}: already exists')
				continue
			
			src = os.path.join(self.root, basename)
			dst = os.path.join(self.root, dst_name)
			try:
				os.rename(src, dst)
				to_modify[hitsound] = new_hitsound
				self.hitsounds.remove(hitsound)
				self.hitsounds.add(new_hitsound)
				
			except Exception as e:
				self.errors.add(basename, e)
		
		for aff in self._affs_temp.values():
			for event in aff.iter_events():
				if not isinstance(event, Arc) or event.hitsound not in to_modify:
					continue
				event.hitsound = to_modify[event.hitsound]
	
	def load_hitsounds(self) -> None:
		self._hitsound_audios_temp: dict[HitsoundStr, AudioSegment]

		for hitsound in self.hitsounds:
			basename = hitsound.unwrap()
			assert basename is not None
			path = os.path.join(self.root, basename)
			try:
				hitsound_audio = AudioSegment.from_file(path)
				self._hitsound_audios_temp[hitsound] = hitsound_audio
			except Exception as e:
				self.errors.add(hitsound, e)

	def normalize_hitsounds(self) -> None:
		config = Config.instance

		for hitsound, hitsound_audio in self._hitsound_audios_temp.items():
			dst_name = hitsound.unwrap()
			assert dst_name is not None
			try:
				hitsound_audio.set_frame_rate(config.chartpack.hitsounds.sampling_rate)
				dst = os.path.join(self.root, dst_name)
				hitsound_audio.export(dst, format='wav')
			except Exception as e:
				self.errors.add(dst_name, e)

	def free_hitsounds(self) -> None:
		del self._hitsound_audios_temp
	
	################################################################################################################

	def process_covers(self) -> None:
		self.reset_covers()
		self.find_covers()
		self.load_covers()
		self.normalize_covers()
		self.free_covers()
	
	def reset_covers(self) -> None:
		self.covers_names: dict[ExtRtcls, list[str]] = {}
		self._covers_temp: dict[ExtRtcls, Image.Image] = {}
	
	def find_covers(self) -> None:
		config = Config.instance
		self.covers_names: dict[ExtRtcls, list[str]]

		extclses: list[ExtRtcls] = []
		for diff in self.songlist.difficulties.iter_difficulty():
			if not diff.jacket_override:
				continue
			rtcls = diff.rating_class
			extclses.append(rtcls)
		
		if len(self.songlist.difficulties) != len(extclses):
			extclses.append(RatingClassEnumExt.Base)
		
		for extcls in extclses:
			value = extcls.value
			templates = config.chartpack.covers.accepts
			cover_names = []
			alternative_paths = []
			for template in templates:
				basename = template.build(value)
				path = os.path.join(self.root, basename)
				alternative_paths.append(path)

				if os.path.exists(path):
					cover_names.append(basename)
			
			if cover_names:
				self.covers_names[extcls] = cover_names
				continue
			self.errors.add(f'covers for diff {extcls.name}', PathNotFoundError(alternative_paths))
	
	def load_covers(self) -> None:
		self._covers_temp: dict[ExtRtcls, Image.Image]

		for extcls, cover_names in self.covers_names.items():
			try:
				best_src = pick_biggest_image(os.path.join(self.root, basename) for basename in cover_names)
				cover = Image.open(best_src)
				self._covers_temp[extcls] = cover
			except Exception as e:
				self.errors.add(f'covers for diff {extcls.name}', 'No valid cover image found')


	def normalize_covers(self) -> None:
		config = Config.instance
		
		covers_names: dict[ExtRtcls, list[str]] = self.covers_names

		for extcls, cover in self._covers_temp.items():
			names: list[str] = []

			norm_to = config.chartpack.covers.normalize_to
			for template, size in norm_to.items():
				basename = template.build(extcls.value)
				dst = os.path.join(self.root, basename)
				try:
					cover_rgb = cover.convert('RGB')
					cover_resized = cover_rgb.resize(size, Image.Resampling.LANCZOS)
					cover_resized.save(dst, format='JPEG')
					names.append(basename)
				except Exception as e:
					self.errors.add(basename, e)
			
			if not names:
				self.errors.add(f'covers for diff {extcls.name}', 'No normalized cover image saved')
				continue
			covers_names[extcls] = names
		
		self.reset_covers()
		self.covers_names = covers_names
		self.load_covers()

	def free_covers(self) -> None:
		del self._covers_temp

	################################################################################################################

	def process_audios(self) -> None:
		self.reset_audios()
		self.find_audios()
		self.load_audios()
		self.check_audios()
		self.normalize_audios()
		self.clip_preview()
		self.free_audios()
	
	def reset_audios(self) -> None:
		self.audio_names: dict[ExtRtcls, str] = {}
		self._audios_temp: dict[ExtRtcls, AudioSegment] = {}
		self.preview_names: dict[ExtRtcls, str] = {}

	def find_audios(self) -> None:
		self.audio_names: dict[ExtRtcls, str]

		extclses: list[ExtRtcls] = []
		for diff in self.songlist.difficulties.iter_difficulty():
			if not diff.audio_override:
				continue
			rtcls = diff.rating_class
			extclses.append(rtcls)
		
		if len(self.songlist.difficulties) != len(extclses):
			extclses.append(RatingClassEnumExt.Base)
		
		for extcls in extclses:
			value = extcls.value
			basename = f'{value}.ogg'
			path = os.path.join(self.root, basename)

			if os.path.exists(path):
				self.audio_names[extcls] = basename
				continue
			self.errors.add(basename, PathNotFoundError(path))
	
	def load_audios(self) -> None:
		self._audios_temp: dict[ExtRtcls, AudioSegment]

		for extcls, basename in self.audio_names.items():
			try:
				audio_path = os.path.join(self.root, basename)
				audio = AudioSegment.from_file(audio_path)
				self._audios_temp[extcls] = audio
			except Exception as e:
				self.errors.add(basename, e)
		
	def check_audios(self) -> None:
		if self.event_info.is_bonus:
			return
		
		config = Config.instance
		minlen, maxlen = config.chartpack.audio.time_range
		for rtcls, audio in self._audios_temp.items():
			audio_len = len(audio)
			if audio_len <= maxlen and audio_len >= minlen:
				continue

			basename = self.audio_names[rtcls]
			if audio_len < minlen:
				msg = f'Audio too short: minimum length is {minlen}, got {DurationMs(audio_len)}'
			else:
				msg = f'Audio too long: maximum length is {maxlen}, got {DurationMs(audio_len)}'
			self.errors.add(basename, msg)
	
	def normalize_audios(self) -> None:
		config = Config.instance

		for extcls, audio in self._audios_temp.items():
			basename = self.audio_names[extcls]
			dst = os.path.join(self.root, basename)
			try:
				audio.set_frame_rate(config.chartpack.audio.sampling_rate)
				audio.export(dst, format='ogg')
			except Exception as e:
				basename = os.path.basename(dst)
				self.errors.add(basename, e)

	def clip_preview(self) -> None:
		config = Config.instance

		for extcls, audio in self._audios_temp.items():
			
			dst_name = 'preview.ogg'
			begin = self.songlist.audio_preview
			end = self.songlist.audio_preview_end

			if extcls is not RatingClassEnumExt.Base:
				dst_name = f'{extcls.value}_preview.ogg'
				try:
					diff = self.songlist.difficulties[extcls]
					if diff is None:
						raise ValueError(f'Failed to find corresponding songlist difficulty')
					if diff.audio_preview is not None and diff.audio_preview_end is not None:
						begin = diff.audio_preview
						end = diff.audio_preview_end
				except Exception as e:
					self.errors.add(dst_name, e)
			
			if end > len(audio):
				self.errors.add(dst_name, f'Invalid \'audioPreviewEnd\': out of audio length range')
			
			dst = os.path.join(self.root, dst_name)

			fade_in = config.chartpack.audio.fade_in_duration
			fade_out = config.chartpack.audio.fade_out_duration

			duration = len(audio)
			clip_begin = max(begin - fade_in, 0)
			clip_end = min(end + fade_out, duration)
			
			clip = audio[clip_begin : clip_end]
			assert isinstance(clip, AudioSegment)
			clip = clip.fade_in(fade_in).fade_out(fade_out)

			try:
				clip.export(dst, format='ogg')
				self.preview_names[extcls] = dst_name
			except Exception as e:
				self.errors.add(dst_name, e)

	def free_audios(self) -> None:
		del self._audios_temp

	################################################################################################################

	def process_backgrounds(self) -> None:
		self.reset_backgrounds()
		self.find_backgrounds()
		self.load_backgrounds()
		self.normalize_backgrounds()
		self.free_backgrounds()
	
	def reset_backgrounds(self) -> None:
		self.background_names: dict[str, str] = {}
		self._backgrounds_temp: dict[str, Image.Image] = {}
	
	def find_backgrounds(self) -> None:
		self.background_names: dict[str, str]

		bgs: set[str] = set()
		for diff in self.songlist.difficulties.iter_difficulty():
			if diff.bg is None:
				continue
			bgs.add(diff.bg)
		
		if len(self.songlist.difficulties) != len(bgs):
			bgs.add(self.songlist.bg)
		
		for bg in bgs:
			if Backgrounds.is_official_bg(bg):
				continue
			
			basename = f'{bg}.jpg'
			path = os.path.join(self.root, basename)

			if os.path.exists(path):
				self.background_names[bg] = basename
				continue
			self.errors.add(basename, PathNotFoundError(path))
	
	def load_backgrounds(self) -> None:
		for bg, basename in self.background_names.items():
			try:
				path = os.path.join(self.root, basename)
				image = Image.open(path)
				self._backgrounds_temp[bg] = image
			except Exception as e:
				self.errors.add(basename, e)
	
	def normalize_backgrounds(self) -> None:
		config = Config.instance
		size = config.chartpack.bgs.size

		for bg, image in self._backgrounds_temp.items():
			basename = f'{bg}.jpg'
			path = os.path.join(self.root, basename)
			try:
				image_rgb = image.convert('RGB')
				image_resized = image_rgb.resize(size, Image.Resampling.LANCZOS)
				image_resized.save(path, format='JPEG')
			except Exception as e:
				self.errors.add(basename, e)
	
	def free_backgrounds(self) -> None:
		del self._backgrounds_temp

	################################################################################################################

	def remove_redundant(self) -> None:
		asset_names = self.asset_names
		for entry in os.scandir(self.root):
			if entry.name not in asset_names:
				try:
					os.remove(entry)
				except Exception as e:
					self.errors.add(entry.name, e)

	
