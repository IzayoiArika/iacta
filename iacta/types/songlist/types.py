from collections.abc import Callable
from typing import Annotated, Any

from pydantic import AfterValidator, NonNegativeInt

from iacta.types.config import Config


def ensure_no_newline(s: str) -> str:
	if '\n' in s:
		raise ValueError(f'String should be in a single line (contain no \'\\n\')')
	return s
SingleLineStr = Annotated[str, AfterValidator(ensure_no_newline)]


def ensure_matches_config(s: Any, field: str) -> Any:
	config = Config.instance
	attr = getattr(config.songlist.fixed_fields, field)
	if attr is None:
		return s
	
	if type(s) is not type(attr) or s != attr:
		raise ValueError(f'Value should be exactly {attr!r}')
	return s

def matches_config(field: str) -> Callable[[Any], Any]:
	return lambda s: ensure_matches_config(s, field)

PackStr = Annotated[str, AfterValidator(matches_config('pack'))]
PurchaseStr = Annotated[str, AfterValidator(matches_config('purchase'))]
DateTimestamp = Annotated[NonNegativeInt, AfterValidator(matches_config('date'))]
VersionStr = Annotated[str, AfterValidator(matches_config('version'))]

CommentStr = Annotated[str, AfterValidator(matches_config('comment'))]


def ensure_custom_str(s: str) -> str:
	config = Config.instance
	max_lines = config.songlist.custom_string_max_lines
	max_line_length = config.songlist.custom_string_max_line_length

	lines = s.split('\n')
	if max_lines is not None and len(lines) > max_lines:
		raise ValueError(f'Custom string could only contain at most {max_lines} rows')
	
	if max_line_length is not None:
		for ln, line in enumerate(lines):
			lenc = sum(1 if ch.isascii() else 2 for ch in line)
			if lenc > max_line_length:
				raise ValueError(f'Line #{ln} exceeds the line length limitis of length ({max_line_length}, got {lenc})')
	return s
CustomStr = Annotated[str, AfterValidator(ensure_custom_str)]