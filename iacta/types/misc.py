from enum import Enum
from math import isfinite
from typing import Any, Self, overload

from mortis import RatingClassEnum, UnreachableBranch
from pydantic import BaseModel, ConfigDict
from pydantic_core.core_schema import CoreSchema, str_schema, no_info_plain_validator_function, plain_serializer_function_ser_schema


class ProjectBaseModel(BaseModel):
	model_config = ConfigDict(
		extra='ignore',
		allow_inf_nan=False,
		validate_by_alias=True,
		serialize_by_alias=True,
		validate_default=True,
		validate_assignment=True,
		json_encoders={
			Enum: lambda e: e.value
		}
	)

	def to_dict(self) -> dict:
		return self.model_dump(exclude_defaults=True, by_alias=True, mode='json')


class RatingClassEnumExt(Enum):
	Base = 'base'

type ExtRatingClassEnum = RatingClassEnumExt | RatingClassEnum


class TemplateStr:
	def __init__(self, template: str) -> None:
		if not isinstance(template, str):
			raise TypeError(f'Value must be a str')
		
		segs = []
		vars: list[str] = []

		rest = template
		while True:
			try:
				content_seg, rest = self._take_until(rest, '{')
				segs.append(content_seg)
			except ValueError:
				segs.append(rest)
				break
				
			try:
				varname, rest = self._take_until(rest, '}')
				vars.append(varname)
			except ValueError:
				raise ValueError(f'Unclosed varname declaration')
		
		self.segs = segs
		self.vars = vars

		varset = set(vars)
		self.is_simple = (len(varset) == 1 and vars[0] == '')
		self.template = template
	
	def _take_until(self, s: str, sep: str) -> tuple[str, str]:
		segs = s.split(sep, 1)
		if len(segs) == 1:
			raise ValueError(f'Failed to split string {s!r} with separator {sep!r}')
		return segs[0], segs[1]
	
	@overload
	def build(self, value: Any | None=None, /) -> str: ...
	@overload
	def build(self, /, **kwargs: Any) -> str: ...
	def build(self, value=None, /, **kwargs) -> str:
		if self.is_simple:
			if value is None:
				raise ValueError(f'Missing variable')
			return self.template.replace(r'{}', str(value))
		
		segs = self.segs.copy()
		vars = self.vars.copy()
		segs.reverse()
		vars.reverse()

		missing: set[str] = set()
		
		for var in vars:
			if var not in kwargs:
				missing.add(var)
		if missing:
			missing_str = ', '.join(missing)
			raise ValueError(f'Missing variables: {missing_str}')
		
		strsegs = [segs.pop()]
		while segs:
			strsegs.append(str(kwargs[vars.pop()]) + segs.pop())
		return ''.join(strsegs)
	
	def __str__(self) -> str:
		return self.template

	def __repr__(self) -> str:
		return f'{self.__class__.__name__}(template={self.template!r})'
	
	@classmethod
	def __get_pydantic_core_schema__(cls, source_type, handler) -> CoreSchema:
		def validate(value):
			if isinstance(value, cls):
				return value
			try:
				return cls(value)
			except TypeError as e:
				raise ValueError(e) from e

		return no_info_plain_validator_function(
			validate, serialization=plain_serializer_function_ser_schema(str,return_schema=str_schema())
		)

class DurationMs(int):
	def __new__(cls, x) -> Self:
		if not isinstance(x, str):
			duration = x

		else:
			segs = x.split(':')
			if len(segs) == 1:
				hrs = mins = 0
				secs = segs[0]
			elif len(segs) == 2:
				hrs = 0
				[mins, secs] = segs
			elif len(segs) == 3:
				[hrs, mins, secs] = segs
			elif len(segs) >= 4:
				raise ValueError(f'Invalid time format')
			else:
				raise UnreachableBranch
			
			hrs = int(hrs)
			if hrs < 0:
				raise ValueError(f'Hours should be nonnegative')
			
			mins = int(mins)
			if mins < 0:
				raise ValueError(f'Minutes should be nonnegative')
			
			secs = float(secs)
			if secs < 0 or not isfinite(secs):
				raise ValueError(f'Seconds should be finite and nonnegative')
			duration = hrs * 360_0000 + mins * 6_0000 + int(secs * 1000)
		
		if duration <= 0:
			raise ValueError(f'Value must be positive')
		
		return super().__new__(cls, duration)
	
	@classmethod
	def __get_pydantic_core_schema__(cls, source_type, handler) -> CoreSchema:
		def validate(value):
			if isinstance(value, cls):
				return value
			try:
				return cls(value)
			except TypeError as e:
				raise ValueError(e) from e

		return no_info_plain_validator_function(
			validate, serialization=plain_serializer_function_ser_schema(str,return_schema=str_schema())
		)

	def __str__(self) -> str:
		secs, millisecs = divmod(self, 1000)
		mins, secs = divmod(secs, 60)
		hrs, mins = divmod(mins, 60)

		if hrs:
			return f'{hrs}:{mins:02d}:{secs:02d}.{millisecs:03d}'
		else:
			return f'{mins}:{secs:02d}.{millisecs:03d}'
	
	def __repr__(self) -> str:
		return f'{self.__class__.__name__}({int(self)})'
	
	def unwrap(self) -> int:
		return int(self)