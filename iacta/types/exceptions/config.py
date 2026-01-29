class ImmutableError(RuntimeError):
	pass

class InvalidConfigError(ValueError):
	pass

class ConfigNotFoundError(RuntimeError):
	pass