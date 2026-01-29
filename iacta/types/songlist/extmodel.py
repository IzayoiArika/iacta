import json
from typing import ClassVar, Self

from pydantic import Field, model_validator
from mortis import SonglistItem

from iacta.types.config import Config
from iacta.types.event_info import EventInfoItem
from iacta.types.exceptions.general import MultipleExceptions
from iacta.types.songlist.digest import get_digest
from iacta.types.songlist.types import CommentStr, DateTimestamp, PackStr, PurchaseStr, VersionStr, ensure_custom_str
from iacta.logging import dbglogger

class SpSonglistItem(SonglistItem):
	pack: PackStr = Field(alias='set')
	purchase: PurchaseStr
	date: DateTimestamp
	version: VersionStr

	comment: CommentStr = Field(alias='_comment')
	just_kidding: bool
	event_info: EventInfoItem
	digest: str

	_unofficial_fields: ClassVar[tuple[str, ...]] = '_comment', 'just_kidding', 'event_info', 'digest'

	@model_validator(mode='after')
	def _after_validation(self) -> Self:
		config = Config.instance

		super()._after_validation
		errors = MultipleExceptions()

		for diff in self.difficulties.iter_difficulty():
			name = diff.rating_class.name
			try:
				ensure_custom_str(diff.chart_designer)
			except ValueError as e:
				errors.add(name, e)
			try:
				ensure_custom_str(diff.jacket_designer)
			except ValueError as e:
				errors.add(name, e)

			if self.event_info.is_bonus:
				continue
				
			rts = config.songlist.ratings_with_plus if diff.rating_plus else config.songlist.ratings
			if diff.rating not in rts:
				errors.add(name, ValueError(f'\'rating\' must be one of {rts} if \'ratingPlus\' is {diff.rating_plus}'))
				
		if errors:
			raise errors
		
		if config.songlist.do_digest_check:
			expected = self.get_digest()
			if self.digest != expected:
				dbglogger.error(f'Digest verification failed; should be {expected}')
				raise ValueError(f'Digest verification failed')

		return self
	
	def norm_songlist(self) -> SonglistItem:
		data = self.to_dict()
		for k in self.__class__._unofficial_fields:
			if k in data:
				del data[k]
		return SonglistItem.model_validate(data)

	def get_digest(self) -> str:
		data = self.model_dump(by_alias=True)
		del data['digest']
		raw_str = json.dumps(data, indent=5, ensure_ascii=False)
		return get_digest(raw_str)