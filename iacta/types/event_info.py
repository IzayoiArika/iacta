from typing import Literal, Self

from pydantic import model_validator
from mortis.songlist.base import SonglistPartModel


class EventInfoItem(SonglistPartModel):
	is_bonus: bool
	charters: tuple[str, ...]

	@model_validator(mode='after')
	def _after_validation(self) -> Self:
		if not self.charters:
			raise ValueError(f'谱师是滚木？')
		return self

	live_session: int | None = None
	category: Literal['A', 'B'] | None = None
	category_idx: int | None = None

	@property
	def live_id(self) -> str:
		return f'{self.category}{self.category_idx:02d}'