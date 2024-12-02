import argparse
from pathlib import Path
import math
from typing import List

class FileCombiner:
    def __init__(self, source_dir: str, output_dir: str, block_size_mb: int = 128):
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.block_size_mb = block_size_mb

    def analyze_directory(self) -> dict:
        total_size_bytes = 0
        file_count = 0

        for file in self.source_dir.rglob('*'):
            total_size_bytes = total_size_bytes + file.stat().st_size
            file_count= file_count + 1
        
        total_size_mb = total_size_bytes / (1024 * 1024)
        number_of_partitions = math.ceil(total_size_mb/ self.block_size_mb)
        
        return {
            'total_size_mb': total_size_mb,
            'file_count': file_count,
            'number_of_partitions ': number_of_partitions ,
            'files_per_partition': math.ceil(file_count / number_of_partitions )
        }

    def combine_files(self) -> List[str]:

        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get all files and calculate distribution
        all_files = []
        for file in self.source_dir.rglob('*'):
            all_files.append(file)

        stats = self.analyze_directory()
        files_per_bucket = stats['files_per_partition']
        
        # Process each bucket
        for bucket_num in range(stats['number_of_partitions ']):
        # Get files for this bucket
         start = bucket_num * files_per_bucket
         bucket_files = all_files[start:start + files_per_bucket]
         
         output_file = self.output_dir / f"combined_file_{bucket_num}.txt"
        
        # Combine files in bucket
        with output_file.open('wb') as outfile:
            for file in bucket_files:
                outfile.write(file.read_bytes())
                outfile.write(b'\n')


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument('source_dir', type=str, help="The input file")
    parser.add_argument('output_dir', type=str, help="The output directory")

    args = parser.parse_args()
    
    
    combiner = FileCombiner(args.source_dir, args.output_dir)
    combiner.combine_files()

if __name__ == "__main__":
    main()