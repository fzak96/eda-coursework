import subprocess
from pathlib import Path
import sys

def upload_pdb_files_to_hdfs(local_directory,hdfs_directory):

    local_directory_path = Path(local_directory)
    hfds_directory_path = Path(hdfs_directory)

    pdb_files = list(local_directory_path.glob("*.pdb"))
    BATCH_SIZE = 50
    
    for i in range(0, len(pdb_files), BATCH_SIZE):

        batch = pdb_files[i:i + BATCH_SIZE]
        
        # Create the hdfs command with all files in the current batch
        hdfs_command = ["hdfs", "dfs", "-put"]
        
        # Add all files in the batch to the command
        for file_path in batch:
            hdfs_command.append(str(file_path))
            
        hdfs_command.append(hfds_directory_path)
        
        try:
            # Execute the HDFS command
            subprocess.run(hdfs_command, check=True)
            print(f"Successfully uploaded batch {i//BATCH_SIZE + 1} " 
                  f"({len(batch)} files)")
            
        except subprocess.CalledProcessError as e:
            print(f"Error uploading batch {i//BATCH_SIZE + 1}: {e}")
            continue

if __name__ == "__main__":
        
    local_directory = sys.argv[1]
    hfds_directory = sys.argv[2]
    
    upload_pdb_files_to_hdfs(local_directory,hfds_directory)