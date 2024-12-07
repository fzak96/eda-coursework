from pyspark.sql import SparkSession
from subprocess import Popen, PIPE
import tempfile
import os
from typing import Tuple
import logging
import sys
from pyspark.accumulators import AccumulatorParam

# Setup basic logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger('MerizoSearch')

# Define custom accumulator for string concatenation
class StringAccumulatorParam(AccumulatorParam):
    def zero(self, initialValue):
        return ""

    def addInPlace(self, v1, v2):
        return v1 + str(v2)

def run_merizo_search(pdb_file_path: str, output_prefix: str, base_id: str):


    # List files in current directory after command execution
    current_dir = os.getcwd()
    log_accumulator.add(f"\nCurrent working directory: {current_dir}")
    files_after = os.listdir(current_dir)
    log_accumulator.add(f"\nFiles in directory before execution: {files_after}")


    cmd = ['python',
           '/home/almalinux/merizo-search/merizo-search/merizo.py',
           'easy-search',
           pdb_file_path,
           '/home/almalinux/merizo-search/database/cath-4.3-foldclassdb',
           output_prefix,
           'tmp',
           '--iterate',
           '--output_headers',
           ]
    
    log_accumulator.add(f"\nExecuting Merizo command: {' '.join(cmd)}")
    p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()

    # List files in current directory after command execution
    files_after = os.listdir(current_dir)
    log_accumulator.add(f"\nFiles in directory after execution: {files_after}")
    
    if out:
        log_accumulator.add(f"\nMerizo output: {out.decode('utf-8')}")
    if err:
        log_accumulator.add(f"\nMerizo stderr: {err.decode('utf-8')}")

    # log_accumulator.add(f"\nStarting Parser for {base_id}")
    run_parser(base_id,current_dir)

def run_parser(file_name_without_extension, output_dir):
    """
    Run the results_parser.py over the hhr file to produce the output summary
    """
    search_file = file_name_without_extension+"_search.tsv"
    
    cmd = ['python', 'results_parser.py', output_dir, search_file]
    log_accumulator.add(f"\nExecuting Parser command: {' '.join(cmd)}")
    
    p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    
    if out:
        log_accumulator.add(f"\nParser output: {out.decode('utf-8')}")
    if err:
        log_accumulator.add(f"\nParser stderr: {err.decode('utf-8')}")

def process_pdb(record):
    try:
        filepath, content = record
        log_accumulator.add(f"\n\nStarting to process file: {filepath}")
        
        # Extract file name from the file path
        file_name = filepath.rsplit('/', 1)[-1]
        
        if(file_name.endswith('.pdb')):
            base_id = file_name[:-4]
        else:
            base_id = file_name
            file_name = file_name + ".pdb"

        log_accumulator.add(f"\nProcessing PDB file: {file_name}")
        log_accumulator.add(f"\nBase ID: {base_id}")
        
        # Create a temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create PDB file with proper name
            pdb_file_path = os.path.join(temp_dir, f"{file_name}")
            log_accumulator.add(f"\nCreated temporary file at: {pdb_file_path}")
            
            # Create a temporary PDB file
            with open(pdb_file_path, 'w') as f:
                f.write(content)
            
            log_accumulator.add(f"\nStarting Merizo search for {file_name}")
            run_merizo_search(pdb_file_path, file_name,base_id)
            
            
            log_accumulator.add(f"\nSuccessfully completed processing {file_name}\n")
            
    except Exception as e:
        log_accumulator.add(f"\nError processing file {filepath}: {str(e)}\n")
        raise e

def main():
    logger.info("\n\n*** STARTING MERIZO SEARCH PIPELINE ***\n\n")
    
    # Create Spark session with logging configs
    spark = SparkSession.builder \
        .appName("MerizoSearchApp") \
        .config("spark.hadoop.fs.defaultFS", "hdfs://mgmtnode:9000") \
        .master("yarn") \
        .config("spark.yarn.log.interval", "1") \
        .config("spark.yarn.log.aggregation.enable", "true") \
        .getOrCreate()

    # Create accumulator for worker logs
    global log_accumulator
    log_accumulator = spark.sparkContext.accumulator("", StringAccumulatorParam())

    # Get and process files
    pdb_files_rdd = spark.sparkContext.wholeTextFiles("hdfs://mgmtnode:9000/analysis/*.pdb")
    file_count = pdb_files_rdd.count()
    logger.info(f"Found {file_count} PDB files to process")
    
    # Process files and collect worker logs
    pdb_files_rdd.map(process_pdb).collect()
    
    # Print accumulated worker logs
    logger.info("\n=== Worker Execution Logs ===")
    logger.info(log_accumulator.value)
    logger.info("=== End Worker Logs ===")
    
    logger.info("\n\n*** PIPELINE COMPLETED ***\n\n")
    spark.stop()

if __name__ == "__main__":
    main()