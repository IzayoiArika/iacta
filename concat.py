import os
import sys

def main():
	libname = 'iacta'
	path = os.path.join(os.path.dirname(__file__), *libname.split('.'))
	output = f'{libname}.txt'
	target_dir = os.path.abspath(path)
	output_file = os.path.join(os.path.dirname(__file__), output)

	if not os.path.isdir(target_dir):
		print(f"Error: Directory not found - {target_dir}")
		sys.exit(1)

	try:
		with open(output_file, 'w', encoding='utf-8') as outfile:
			file_count = 0
			
			for root, _, files in os.walk(target_dir):
				for filename in files:
					_, ext = os.path.splitext(filename)
					if ext.lower() not in ['.py', '.plc']:
						continue
					
					file_path = os.path.join(root, filename)
					full_path = os.path.join(os.path.abspath(root), filename)
					
					try:
						with open(file_path, 'r', encoding='utf-8') as infile:
							content = infile.read()
					except UnicodeDecodeError:
						continue
					except Exception as e:
						print(f"Error reading {full_path}: {str(e)}")
						continue
					
					if not content:
						continue
					
					outfile.write(f"## {full_path}\n")
					outfile.write(content)
					
					# Add separator if content doesn't end with newline
					if content and content[-1] != '\n':
						outfile.write('\n')
					
					outfile.write('\n')
					file_count += 1
			
			print(f"Successfully concatenated {file_count} files to {output_file}")
	
	except Exception as e:
		print(f"Error writing output: {str(e)}")

if __name__ == "__main__":
	main()