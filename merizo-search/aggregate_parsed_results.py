from pyspark.sql import SparkSession


def main():

    # Create Spark session with logging configs
    spark = SparkSession.builder \
        .appName("AggregateParsedResults") \
        .config("spark.hadoop.fs.defaultFS", "hdfs://mgmtnode:9000") \
        .master("yarn") \
        .getOrCreate()
    

    #need to modify this to run both human and ecoli folder paths, currently only running static path

    # Load the parsed results from HDFS
    pdb_files_df = spark.read.text("hdfs://mgmtnode:9000/parsed/*.pdb", header=True, inferSchema=True)

    pdb_files_df.printSchema()

    # Aggregate the parsed results
    #aggregated_results = parsed_results.groupBy("pdb_id").agg({"score": "mean"})

    # Save the aggregated results to HDFS
    #aggregated_results.write.csv("hdfs:///user/almalinux/aggregated_results.csv", header=True)

    spark.stop()


if __name__ == "__main__":
    main()