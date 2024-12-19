import sys
from minio import Minio
from pathlib import Path
import re
from hdfs import InsecureClient
from minio import Minio
from pathlib import Path
import re

def transfer_to_minio(folder_name, bucket_name, minio_client, hdfs_client):
    try:
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)
            print(f"Created new bucket: {bucket_name}")
        else:
            print(f"Bucket {bucket_name} already exists")

        hdfs_path = f"/{folder_name}"
        files = hdfs_client.list(hdfs_path)

        for filename in files:
            hdfs_file = f"{hdfs_path}/{filename}"
            object_name = f"data/{filename}"

            
            # Open file in hdfs as stream and get its size
            with hdfs_client.read(hdfs_file) as hdfs_stream:
                file_size = hdfs_client.status(hdfs_file)['length']
                
                # Stream to MinIO
                minio_client.put_object(
                    bucket_name,
                    object_name,
                    hdfs_stream,
                    file_size
                )
        
    except Exception as e:
        print(f"Error during transfer: {e}")
        raise

def main():
    # Read secret key
    with open('/home/almalinux/.miniopass', 'r') as f:
        secret_key = f.read().strip() 
    
    # Create MinIO client
    minio_client = Minio(
        "ucabfz0-s3.comp0235.condenser.arc.ucl.ac.uk",
        access_key="myminioadmin",
        secret_key=secret_key,
        secure=True
    )

    hdfs_client = InsecureClient('http://mgmtnode:9870')  # WebHDFS port

    folder_path = sys.argv[1]
    pattern = r'/'
    replacement = '-'
    bucket_name = re.sub(pattern, replacement, folder_path).lower()
    transfer_to_minio(folder_path, bucket_name, minio_client,hdfs_client)

if __name__ == "__main__":
    main()