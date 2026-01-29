from iacta.logging import log_error
from iacta.steps.clean_root import clean_root
from iacta.steps.pack import pack_zipfiles
from iacta.steps.radio import collect_radio_files
from iacta.steps.stream_info import process_chartpacks_info
from iacta.steps.unzip import unzip_chartpacks
from iacta.steps.chartpack import deduplicate_ids, get_chartpacks
from iacta.types.config import Config


def main():
	"""主程序入口，负责调用各个步骤的函数完成整体流程。勿修改。仅当前一步骤无异常时继续执行下一步骤。"""

	Config.load_from('config-example.json')
	clean_root()

	unzipped, errors = unzip_chartpacks()
	if errors:
		raise errors
	
	chartpacks, errors = get_chartpacks(unzipped)
	if errors:
		raise errors
	
	chartpacks, errors = deduplicate_ids(chartpacks)
	if errors:
		raise errors
	
	process_chartpacks_info(chartpacks)
	collect_radio_files(chartpacks)
	pack_zipfiles(chartpacks)

if __name__ == '__main__':
	try:
		main()
	except Exception as e:
		log_error(e)