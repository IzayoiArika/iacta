import json
from typing import Literal, Self

from pydantic import Field, NonNegativeInt as uint, PositiveFloat as posfloat, PositiveInt as posint, ValidationError, model_validator

from mortis import LowerAsciiId, RatingClassEnum, RatingInt, SideEnum, SingleLineStr
from mortis.utils import classproperty

from iacta.logging import Logger
from iacta.types.exceptions.config import ConfigNotFoundError, ImmutableError, InvalidConfigError
from iacta.types.misc import DurationMs, ProjectBaseModel, TemplateStr


class PathsConfig(ProjectBaseModel):
	root: str
	zipfiles: str
	foolish_pics: str
	log_file: str

	radio: str
	chartpacks: str

	@model_validator(mode='after')
	def _after_validation(self) -> Self:
		Logger.redirect_file(self.log_file)
		return self


class FixedFieldsConfig(ProjectBaseModel):
	pack: LowerAsciiId = Field(alias='set')
	purchase: LowerAsciiId
	date: uint
	version: SingleLineStr

	comment: str

	def __getattr__(self, name):
		if name == 'set':
			return self.pack
		return super().__getattribute__(name)
	
class SonglistConfig(ProjectBaseModel):
	accepts: list[str]
	normalize_to: str

	choosing: Literal['by_priority', 'forbid', 'take_first', 'ask']
	tail_comma: Literal['require', 'allow', 'forbid']

	do_digest_check: bool = True

	fixed_fields: FixedFieldsConfig
	sides: set[SideEnum]

	ratings: tuple[RatingInt, ...]
	ratings_with_plus: tuple[RatingInt, ...]
	rating_classes: tuple[RatingClassEnum, ...]

	custom_string_max_lines: posint
	custom_string_max_line_length: posint


class CoverConfig(ProjectBaseModel):
	accepts: list[TemplateStr]
	normalize_to: dict[TemplateStr, tuple[uint, uint]]
	preset_foolish_pics: dict[LowerAsciiId, str]

class AudioConfig(ProjectBaseModel):
	sampling_rate: uint
	time_range: tuple[DurationMs, DurationMs]
	fade_in_duration: DurationMs
	fade_out_duration: DurationMs

	@model_validator(mode='after')
	def _after_validation(self) -> Self:
		minlen, maxlen = self.time_range
		if minlen > maxlen:
			raise ValueError(
				f'Invalid \'time_range\' {self.time_range}: ' + 
				'maximum length (latter) must be no smaller than minimum length (former)'
			)
		return self

class AFFChartpackConfig(ProjectBaseModel):
	tpdf_range: tuple[posfloat, posfloat]

	@model_validator(mode='after')
	def _after_validation(self) -> Self:
		mintpdf, maxtpdf = self.tpdf_range
		if mintpdf > maxtpdf:
			raise ValueError(
				f'Invalid \'tpdf_range\' {self.tpdf_range}: ' + 
				'maximum tpdf (latter) must be no smaller than minimum tpdf (former)'
			)
		return self

class BackgroundsConfig(ProjectBaseModel):
	size: tuple[uint, uint]

class HitsoundsConfig(ProjectBaseModel):
	sampling_rate: uint

class MaskingConfig(ProjectBaseModel):
	artist: str
	bpm: str
	song_title: TemplateStr

class SonglistPackConfig(ProjectBaseModel):
	masking: MaskingConfig

class ChartpackConfig(ProjectBaseModel):
	covers: CoverConfig
	audio: AudioConfig
	aff: AFFChartpackConfig
	bgs: BackgroundsConfig
	hitsounds: HitsoundsConfig
	songlist: SonglistPackConfig


class TechnicalConfig(ProjectBaseModel):
	digest_salts: tuple[str, ...]
	file_edit_time: posint


class PreparationConfig(ProjectBaseModel):
	no_root_found: Literal['create', 'fail']
	cleaning_root: Literal['force', 'require_empty', 'ask']
	nonzip_items: Literal['remove', 'forbid', 'ignore', 'ask']


class LivestreamConfig(ProjectBaseModel):
	sessions: uint


class GuessletterConfig(ProjectBaseModel):
	max_per_dict: posint


class _Config(ProjectBaseModel):
	event_name: str

	paths: PathsConfig
	preparation: PreparationConfig
	songlist: SonglistConfig
	chartpack: ChartpackConfig
	livestream: LivestreamConfig
	guessletter: GuessletterConfig

	technical: TechnicalConfig


class Config:
	__instance__ = None

	def __new__(cls) -> Self:
		raise NotImplementedError
	
	@classmethod
	def load_from(cls, path) -> _Config:
		if cls.__instance__ is not None:
			raise ImmutableError(f'Configurations should be only loaded once')
		
		try:
			with open(path, 'r', encoding='utf-8') as f:
				cfg = json.load(f)
		except json.JSONDecodeError as e:
			raise InvalidConfigError('Configurations are not in a valid JSON format') from e
			
		try:
			cls.__instance__ = _Config.model_validate(cfg)
		except ValidationError as e:
			raise InvalidConfigError(f'Errors occurred when validating configurations: \n{e}') from e

		return cls.__instance__
	
	@classproperty
	@classmethod
	def instance(cls) -> _Config:
		if cls.__instance__ is not None:
			return cls.__instance__
		
		raise ConfigNotFoundError(f'No loaded configurations found')