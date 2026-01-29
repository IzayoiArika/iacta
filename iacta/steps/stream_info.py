import json
import os
import random
from typing import Any, Literal

from iacta.logging import dbglogger
from iacta.steps.asciify import export_guessletter_titles
from iacta.types.chartpack import Chartpack
from iacta.types.config import Config
from iacta.types.misc import ExtRatingClassEnum, RatingClassEnumExt
from iacta.utils import random_distribute


def save_event_info(chartpacks: list[Chartpack]) -> None:
	config = Config.instance
	path = os.path.join(config.paths.root, 'stream_info.json')
	with open(path, 'w', encoding='utf-8') as f:
		json.dump({
			chartpack.id: chartpack.event_info.to_dict()
			for chartpack in chartpacks
		}, f, ensure_ascii=False, indent=4)


def get_csv_title_params() -> list[Any]:
	return [
		'编号',
		'曲名',
		'曲师',
		'谱师名义',
		'难度',
	]

def get_csv_lines_params(chartpack: Chartpack) -> list[list[Any]]:
	all_params = []
	for diff in chartpack.songlist.difficulties.all_activated:
		params = []


		all_params.append(params)
	return all_params


def export_info_csv(chartpacks: list[Chartpack]) -> None:
	config = Config.instance

	params = []
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

	categorized: dict[Literal['A', 'B', 'C'], list[Chartpack]] = {k: [] for k in ('A', 'B', 'C')}
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