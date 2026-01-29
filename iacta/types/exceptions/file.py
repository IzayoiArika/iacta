import os
from os import DirEntry


class _PathError(OSError):
	def __init__(self, path) -> None:
		self.path = path
	
	def __str__(self) -> str:
		return f'Path error: {self.path}'

class PathNotFoundError(_PathError):
	def __str__(self) -> str:
		return f'Path does not exist: {self.path}'

class FolderNotEmptyError(_PathError):
	def __str__(self) -> str:
		return f'Path is not empty: {self.path}'


class NotAZipError(_PathError):
	def __str__(self) -> str:
		return f'Path is not a zip file: {self.path}'


class MissingSonglistError(FileNotFoundError):
	def __init__(self, folder: str) -> None:
		self.folder = folder
	
	def __str__(self) -> str:
		return f'No songlist file found in folder {self.folder}'

class AmbiguousSonglistError(OSError):
	def __init__(self, folder: str, entries: list[DirEntry[str]]) -> None:
		self.folder = folder
		self.entries = entries
	
	def __str__(self) -> str:
		entries = ', '.join(os.path.basename(entry) for entry in self.entries)
		return f'Too many songlist files found in folder {self.folder}: {entries}'


class AudioLengthError(RuntimeError):
	pass


class BadChartpackError(OSError):
	def __init__(self, path: str, e: Exception) -> None:
		self.path = path
		self.e = e
	
	def __str__(self) -> str:
		return f'{self.path}: Bad chartpack; primary error is [{type(self.e).__name__}] {self.e}'
	
	def __repr__(self) -> str:
		return f'{self.__class__.__name__}({self.path!r}, {self.e!r})'