import os

try:
	from tqdm import tqdm
except ImportError:
	tqdm = lambda x, /, *_, **__: x

from iacta.types.chartpack import Chartpack
from iacta.types.exceptions.general import MultipleExceptions
from iacta.utils import generate_random_str, truncate


def get_chartpacks(entries: list[str]) -> tuple[list[Chartpack], MultipleExceptions]:
	errors = MultipleExceptions()
	chartpacks: list[Chartpack] = []

	with tqdm(entries, leave=False) as bar:
		for entry in bar:
			basename = os.path.basename(entry)
			bar.set_description(truncate(basename, 20))
			
			try:
				chartpack = Chartpack(entry)
				chartpacks.append(chartpack)
			except Exception as e:
				errors.add(basename, e)
	
	return chartpacks, errors

def deduplicate_ids(chartpacks: list[Chartpack]) -> tuple[list[Chartpack], MultipleExceptions]:
	errors = MultipleExceptions()

	raw: dict[str, list[Chartpack]] = {}
	deduplicated: dict[str, Chartpack] = {}

	for chartpack in chartpacks:
		id = chartpack.id
		if id not in raw:
			raw[id] = []
		
		raw[id].append(chartpack)
	
	for id, packs in raw.items():
		pack_cnt = len(packs)
		if pack_cnt == 1:
			deduplicated[id] = packs[0]
			continue

		for pack in packs:
			while True:
				new_id = f'{id}_{generate_random_str(pack_cnt)}'
				if new_id not in deduplicated:
					break
			
			pack.reassign_id(new_id)
			deduplicated[new_id] = pack

	unique: list[Chartpack] = list(deduplicated.values())
	for pack in unique:
		try:
			pack.reset_root(pack.id)
		except Exception as e:
			errors.add(pack.id, e)

	return list(deduplicated.values()), errors