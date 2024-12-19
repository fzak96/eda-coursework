from pyspark.sql import SparkSession
from minio import Minio
import re


def transfer_to_minio(folder_name, bucket_name, spark, minio_client):
    """
    Transfer files from HDFS to Minio using Spark
    """

    # Define source and destination paths
    hdfs_path = f"hdfs://mgmtnode:9000/{folder_name}/*"
    minio_path = f"s3a://{bucket_name}"

    try:
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)
            print(f"Created new bucket: {bucket_name}")
        else:
            print(f"Bucket {bucket_name} already exists")
    except Exception as e:
        print(f"Error handling bucket: {e}")
        raise
    
    try:
        print(f"Starting transfer from {hdfs_path} to {minio_path}")
        
        # Read all files from HDFS
        df = spark.read.text(hdfs_path)
        
        # Write to Minio in the desired format
        df.write.mode("append").text(minio_path)
        
        print("Transfer completed successfully")
        
    except Exception as e:
        print(f"Error during transfer: {e}")
        raise
    finally:
        # Clean up Spark session
        spark.stop()

def main():


    spark= SparkSession.builder \
            .appName("HDFS to Minio Transfer") \
            .config("spark.hadoop.fs.s3a.endpoint", "ucabfz0-s3.comp0235.condenser.arc.ucl.ac.uk") \
            .config("spark.hadoop.fs.s3a.access.key", "myminioadmin") \
            .config("spark.hadoop.fs.s3a.secret.key", "/home/almalinux/.miniopass") \
            .config("spark.hadoop.fs.s3a.path.style.access", "true") \
            .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
            .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "true") \
            .getOrCreate()
    
    minio_client = Minio(
        "ucabfz0-s3.comp0235.condenser.arc.ucl.ac.uk",
        access_key="myminioadmin",
        secret_key="/home/almalinux/.miniopass",
        secure=True)


    folder_paths=['parsed/ecoli','parsed/human','data/ecoli','data/human', 'summaryOutputs']
    pattern = r'/'
    replacement = '-'


    for folder_path in folder_paths:
        bucket_name = re.sub(pattern, replacement, folder_path)
        transfer_to_minio(folder_path, bucket_name, spark, minio_client)

if __name__ == "__main__":
    main()