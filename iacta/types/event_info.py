from typing import Literal, Self, get_args

from pydantic import model_validator
from mortis.songlist.base import SonglistPartModel


type ChartCategory = Literal['A', 'B', 'C']
CHART_CATEGORIES: tuple[ChartCategory, ...] = get_args(ChartCategory.__value__)

class EventInfoItem(SonglistPartModel):
	charters: tuple[str, ...]
	digest: str

	live_session: int | None = None
	category: ChartCategory | None = None
	category_idx: int | None = None

	@model_validator(mode='after')
	def _after_validation(self) -> Self:
		if not self.charters:
			raise ValueError(f'谱师是滚木？')
		return self

	@property
	def live_id(self) -> str:
		return f'{self.category}{self.category_idx:02d}'

	@property
	def is_bonus(self) -> bool:
		return self.category == 'B'

	@property
	def is_collaboration(self) -> bool:
		return self.category == 'C'



class SubmitInfoItem(SonglistPartModel):
	isBonus: bool
	isCollaboration: bool
	charters: tuple[str, ...]
	songlistDigest: str