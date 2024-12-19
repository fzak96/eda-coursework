from pyspark.sql import SparkSession
from pyspark.sql.functions import sum, col, mean, stddev
import sys
import os

def extract_pdldt_mean(file_tuple):

    # get file content from the tuple
    file_header = file_tuple[1]
    first_line = file_header.split("\n")[0]
    pdldt_value = first_line.split("mean plddt:")[1].strip()
    return float(pdldt_value)

def main():

    # Create Spark session with logging configs
    spark = SparkSession.builder \
        .appName("AggregateParsedResults") \
        .config("spark.hadoop.fs.defaultFS", "hdfs://mgmtnode:9000") \
        .master("local") \
        .getOrCreate()
    
    folder_name = sys.argv[1]
    hdfs_input_path = f"hdfs://mgmtnode:9000/parsed/{folder_name}/*.parsed"
    hdfs_output_path = f"hdfs://mgmtnode:9000/summaryOutputs/"
    

    parsed_files_rdd = spark.sparkContext.wholeTextFiles(hdfs_input_path)

    rdd_with_plddtmeans = parsed_files_rdd.map(extract_pdldt_mean)

    # Convert to DataFrame
    plddt_df = spark.createDataFrame(rdd_with_plddtmeans,"float").toDF("plddt")

    # Calculate statistics
    stats = plddt_df.select(
        mean("plddt").alias("mean_plddt"),
        stddev("plddt").alias("stddev_plddt")
    )

    stats.show()
    

    #need to modify this to run both human and ecoli folder paths, currently only running static path

    # Load the parsed results from HDFS
    parsed_files_df = spark.read.csv(hdfs_input_path, header=True, inferSchema=True, comment="#")

    # Aggregate the parsed results for the cound for each cath id
    aggregated_results = parsed_files_df.withColumn("count", col("count").cast("integer")) \
    .groupBy("cath_id").agg(sum("count").alias("count"))

    aggregated_results.show()

    #Save the aggregated results to HDFS
    aggregated_results.coalesce(1).write.mode("overwrite").csv(hdfs_output_path, header=True)
    stats.coalesce(1).write.mode("append").csv(hdfs_output_path, header=True)

    spark.stop()


if __name__ == "__main__":
    main()