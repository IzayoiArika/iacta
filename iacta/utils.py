import random
from collections.abc import Callable, Iterable
from math import ceil
from typing import Any, Generic, TypeVar

from PIL import Image


MT = TypeVar('MT', bound=Any)
RT = TypeVar('RT')
class classproperty(Generic[MT, RT]):
	"""
	Convert a classmethod into a classproperty.
	- **Required to use with `@classmethod`.**
	- Example::

		@classproperty
		@classmethod
		def func(cls, *args, **kwargs) -> Any:
			...
	
	"""
	def __init__(self, fget: Callable[[type[MT]], RT], /) -> None:
		self.fget = fget

	def __get__(self, instance: MT | None, objtype: type[MT], /) -> RT:
		return self.fget.__get__(instance, objtype)()


def indent(line: Any, n: int = 2) -> str:
	return ' ' * n + str(line).replace('\n', '\n' + ' ' * n)


def generate_random_str(n: int) -> str:
	alphabet = 'abcdefghijklmnopqrstuvwxyz'
	letter_cnt = ceil(n / len(alphabet)) + 1
	letters = random.choices(alphabet, k=letter_cnt)
	return ''.join(letters)

T = TypeVar('T')
def random_distribute(arr: list[T], n: int) -> list[list[T]]:
	if n <= 0:
		raise ValueError('n must be greater than 0')

	shuffled = arr[:]
	random.shuffle(shuffled)
	distributed: list[list[Any]] = [[] for _ in range(n)]

	q, r = divmod(len(arr), n)
	counts: list[int] = [q for _ in range(n)]
	for i in range(r):
		counts[i] += 1
	
	l = 0
	for i in range(n):
		distributed[i] = shuffled[l:l + counts[i]]
		l += counts[i]
	
	return distributed


def pick_biggest_image(image_paths: Iterable[str]) -> str:
	image_paths = list(image_paths)
	if not image_paths:
		raise ValueError('image_paths cannot be empty')
	
	best_path = None
	max_area = 0
	for path in image_paths:
		with Image.open(path) as img:
			w, h = img.size
			area = w * h
			if area > max_area:
				max_area = area
				best_path = path
	
	assert best_path is not None
	return best_path


def truncate(s: str, maxlen: int) -> str:
	if maxlen <= 3:
		raise NotImplementedError
	return s if len(s) <= maxlen else s[:maxlen - 3] + '...'