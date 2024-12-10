from pyspark.sql import SparkSession
from pyspark.sql.functions import sum, col, mean, stddev, regexp_extract

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
        .master("yarn") \
        .getOrCreate()
    

    parsed_files_rdd = spark.sparkContext.wholeTextFiles("hdfs://mgmtnode:9000/parsed/*.parsed")

    rdd_with_plddtmeans = parsed_files_rdd.map(extract_pdldt_mean)

    # Convert to DataFrame
    plddt_df = spark.createDataFrame(rdd_with_plddtmeans,"float").toDF("plddt")

    # Calculate statistics
    stats = plddt_df.select(
        mean("plddt").alias("mean_plddt"),
        stddev("plddt").alias("stddev_plddt")
    ).show()
    

    #need to modify this to run both human and ecoli folder paths, currently only running static path

    # Load the parsed results from HDFS
    parsed_files_df = spark.read.csv("hdfs://mgmtnode:9000/parsed/*.parsed", header=True, inferSchema=True, comment="#")

    # Aggregate the parsed results for the cound for each cath id
    aggregated_results = parsed_files_df.withColumn("count", col("count").cast("integer")) \
    .groupBy("cath_id").agg(sum("count").alias("count"))

    #Save the aggregated results to HDFS
    aggregated_results.coalesce(1).write.mode("overwrite").csv("hdfs://mgmtnode:9000/summaryOutputs/", header=True)
    stats.coalesce(1).write.mode("append").csv("hdfs://mgmtnode:9000/summaryOutputs/", header=True)

    spark.stop()


if __name__ == "__main__":
    main()