from typing import final

from iacta.utils import indent


@final
class UnreachableBranch(BaseException):
	"""
	Use `raise UnreachableBranch` to tell the static checker that current code branch is unreachable (theoretically).
	- Usually this is used to avoid unexpected error reports regarding code branches.
	"""
	def __init__(self, *args: object) -> None:
		super().__init__(*args)

	def __repr__(self) -> str:
		return self.__class__.__name__

@final
class MultipleExceptions(ValueError):
	def __init__(self, exceptions: dict[str, str | Exception] | None = None):
		self.exceptions = exceptions if exceptions else {}
	
	def __str__(self) -> str:
		lines = ['MultipleExceptions occurred. ']

		for k, e in self.exceptions.items():
			if isinstance(e, str):
				lines.append(indent(k, 4))
				lines.append(indent(e, 8))

			elif isinstance(e, Exception):
				lines.append(indent(k, 4))
				lines.append(indent(type(e).__name__, 8))
				lines.append(indent(e, 8))
			
			else:
				raise UnreachableBranch
		
		return '\n'.join(lines)
	
	def __repr__(self) -> str:
		return f'MultipleExceptions({self.exceptions!r})'
	
	def add(self, k: str, e: str | Exception) -> None:
		self.exceptions[k] = e
	
	def __bool__(self) -> bool:
		return len(self.exceptions) != 0