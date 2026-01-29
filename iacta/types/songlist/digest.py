from iacta.types.config import Config


def get_digest(s: str) -> str:
	def djb2(s: str):
		hash_val = 5381
		for char in s:
			hash_val = ((hash_val << 5) + hash_val) + ord(char)
			hash_val &= 0xFFFFFFFF
		return format(hash_val, '08x')
	
	config = Config.instance
	block_size = 1024
	strlen = 32
	salts = config.technical.digest_salts

	parts = []
	total_blocks = (len(s) + block_size - 1) // block_size
	
	for i in range(total_blocks):
		start = i * block_size
		end = start + block_size
		block = s[start:end]
		
		data = salts[i % len(salts)] + block
		hash = djb2(data)
		parts.append(hash)
	
	checksum = ''.join(parts)
	while len(checksum) < strlen:
		checksum = checksum + djb2(checksum)
	
	return checksum[-strlen:]