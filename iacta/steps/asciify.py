import json
import os
from collections.abc import Callable
from math import ceil

from mortis import Difficulty, SonglistItem

from iacta.types.chartpack import Chartpack
from iacta.types.config import Config
from iacta.types.misc import ExtRatingClassEnum, RatingClassEnumExt
from iacta.logging import dbglogger
from iacta.utils import random_distribute


type owo = dict[str, dict[ExtRatingClassEnum, str]]

def collect_all_items(
	chartpacks: list[Chartpack],
	picker: Callable[[SonglistItem | Difficulty], str]
) -> owo:
	
	result: owo = {}
	for chartpack in chartpacks:
		result[chartpack.id] = {}
		result[chartpack.id][RatingClassEnumExt.Base] = picker(chartpack.songlist)
		for diff in chartpack.songlist.difficulties.all_activated:
			if diff.title_localized:
				result[chartpack.id][diff.rating_class] = picker(diff)
	
	return result

def asciify_str(s: str, item_name: str) -> str:
	if s.isascii():
		return s
	
	new = input(f'{s!r} 含有非 ASCII 字符，请输入对应的 ASCII 字符串: ')
	while not new.isascii():
		new = input(f'输入仍含有非 ASCII 字符，请重新输入: ')
	return new

def general_asciify(
	chartpacks: list[Chartpack],
	picker: Callable[[SonglistItem | Difficulty], str],
	item_name: str
) -> owo:
	
	items = collect_all_items(chartpacks, picker)
	for id, diffs in items.items():
		for extcls, title in diffs.items():
			name = f'{id}.{extcls.value} 的 {item_name}'
			new_title = asciify_str(title, name)
			diffs[extcls] = new_title

			if new_title == title:
				continue
			dbglogger.info(f'将 {name} 从 {title!r} 修改为纯 ASCII: {new_title!r}')

	return items

def asciify_titles(chartpacks: list[Chartpack]) -> owo:
	return general_asciify(
		chartpacks,
		lambda item: item.title_localized.en, # type: ignore
		'标题'
	)

def asciify_artists(chartpacks: list[Chartpack]) -> owo:
	return general_asciify(
		chartpacks,
		lambda item: item.artist, # type: ignore
		'曲师'
	)

def export_guessletter_dicts(titles: owo, artists: owo) -> None:
	config = Config.instance

	all_titles = []
	all_artists = []

	for id, id_titles in titles.items():
		id_artists = artists[id]
		all_titles.extend(id_titles.values())
		all_artists.extend(id_artists.values())
	
	group_count = ceil(len(all_titles) / config.guessletter.max_per_dict)
	distributed_titles = random_distribute(all_titles, group_count)
	distributed_artists = random_distribute(all_artists, group_count)

	dict_path = os.path.join(config.paths.root, 'guessletter_dicts.json')
	with open(dict_path, 'w', encoding='utf-8') as f:
		json.dump({
			'titles': distributed_titles,
			'artists': distributed_artists,
		}, f, ensure_ascii=False, indent=4)


def export_guessletter_titles(chartpacks: list[Chartpack]) -> None:
	titles = asciify_titles(chartpacks)
	artists = asciify_artists(chartpacks)
	export_guessletter_dicts(titles, artists)