import json
import os
import random
from typing import Any, Literal

from mortis import Difficulty, RatingClassEnum

from iacta.steps.asciify import export_guessletter_titles
from iacta.steps.radio import get_diff_artist, get_diff_title
from iacta.types.chartpack import Chartpack
from iacta.types.config import Config
from iacta.utils import random_distribute


def save_event_info(chartpacks: list[Chartpack]) -> None:
	config = Config.instance
	path = os.path.join(config.paths.root, 'stream_info.json')
	with open(path, 'w', encoding='utf-8') as f:
		json.dump({
			chartpack.id: chartpack.event_info.to_dict()
			for chartpack in chartpacks
		}, f, ensure_ascii=False, indent=4)

def get_diff_abbrev(rtcls: RatingClassEnum) -> str:
	return {
		RatingClassEnum.Past: 'PST',
		RatingClassEnum.Present: 'PRS',
		RatingClassEnum.Future: 'FTR',
		RatingClassEnum.Beyond: 'BYD',
		RatingClassEnum.Eternal: 'ETR'
	}[rtcls]

def get_diff_str(diff: Difficulty) -> str:
	return f'[{get_diff_abbrev(diff.rating_class)}] {diff.rating}' + ('+' if diff.rating_plus else '')


def get_csv_title_params() -> list[Any]:
	return [
		'编号',
		'曲名',
		'曲师',
		'难度',
		'谱师名义',
		'参赛谱师',
	]

def get_csv_lines_params(chartpack: Chartpack) -> list[list[Any]]:
	all_params = []
	songlist = chartpack.songlist
	event_info = chartpack.event_info
	last_title = ''
	last_artist = ''
	for i, diff in enumerate(songlist.difficulties.all_activated):
		live_id = '' if i else event_info.live_id

		title = get_diff_title(songlist, diff.rating_class)
		if title == last_title:
			title = ''
		else:
			last_title = title

		artist = get_diff_artist(songlist, diff.rating_class)
		if artist == last_artist:
			artist = ''
		else:
			last_artist = artist

		difficulty = get_diff_str(diff)
		chart_designer = diff.chart_designer
		actual_charter = '+'.join(event_info.charters)

		params = [
			live_id, title, artist, difficulty,
			chart_designer, actual_charter, 
		]
		
		all_params.append(params)
	return all_params


def export_info_csv(chartpacks: list[Chartpack]) -> None:
	config = Config.instance

	params = []
	chartpacks.sort(key=lambda cp: cp.event_info.live_id)
	for chartpack in chartpacks:
		params.extend(get_csv_lines_params(chartpack))

	csv_path = os.path.join(config.paths.root, 'answersheet_template.csv')
	with open(csv_path, 'w', encoding='utf-8') as f:
		title_params = get_csv_title_params()
		lines: list[str] = [','.join(title_params)]
		for line_params in params:
			line = ','.join(map(str, line_params))
			lines.append(line)
		f.write('\n'.join(lines))


def process_chartpacks_info(chartpacks: list[Chartpack]) -> None:
	config = Config.instance

	copied = chartpacks[:]
	random.shuffle(copied)

	categorized: dict[Literal['A', 'B'], list[Chartpack]] = {k: [] for k in ('A', 'B')}
	for chartpack in copied:
		categorized[chartpack.category].append(chartpack)
	
	for v in categorized.values():
		for category_idx, chartpack in enumerate(v, start=1):
			chartpack.event_info.category_idx = category_idx

	distributed = random_distribute(copied, config.livestream.sessions)
	for session, group in enumerate(distributed, start=1):
		for chartpack in group:
			chartpack.event_info.live_session = session
	
	save_event_info(chartpacks)
	export_info_csv(chartpacks)
	export_guessletter_titles(chartpacks)