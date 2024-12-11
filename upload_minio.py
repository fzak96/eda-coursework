from minio import Minio

client = Minio("ucabfz0-s3.comp0235.condenser.arc.ucl.ac.uk",
    access_key = "myminioadmin",
    secret_key = "/home/almalinux/.miniopass",
    secure = True, 
)

def put_file(bucket, file_name):
    try:
        # Create bucket if it doesn't exist
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
        
        # Upload file
        client.fput_object(bucket, file_name, file_name)
        print(f"Successfully uploaded {file_name} to bucket {bucket}")
    except Exception as e:
        print(f"Error: {e}")


def main():

    put_file("test", "test.txt")

if __name__ == "__main__":
    main()