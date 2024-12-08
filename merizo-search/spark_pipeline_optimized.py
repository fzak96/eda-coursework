from pyspark.sql import SparkSession
from subprocess import Popen, PIPE
import tempfile
import os
from typing import Tuple
import logging
import sys
from pyspark.accumulators import AccumulatorParam
import csv
import json
from collections import defaultdict
import statistics

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

def run_merizo_search(pdb_file_path: str, file_name: str):


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
           file_name,
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

    #add segment and search files to hdfs

    segment_file_path = os.path.join(current_dir,file_name+'_segment.tsv')
    search_file_path = os.path.join(current_dir,file_name+'_search.tsv')

    add_to_hdfs(segment_file_path, 'hdfs://mgmtnode:9000/data/')
    add_to_hdfs(search_file_path, 'hdfs://mgmtnode:9000/data/')
    
    if out:
        log_accumulator.add(f"\nMerizo output: {out.decode('utf-8')}")
    if err:
        log_accumulator.add(f"\nMerizo stderr: {err.decode('utf-8')}")

    log_accumulator.add(f"\nStarting Parser for {file_name}")
    run_parser(file_name,current_dir) #output prefix is the file name with extension

def add_to_hdfs(file_path, hdfs_path):
    """
    Add a file to HDFS
    """
    cmd = ['/home/almalinux/hadoop-3.4.0/bin/hdfs', 'dfs', '-copyFromLocal', file_path, hdfs_path]
    log_accumulator.add(f"\nAdding file to HDFS: {' '.join(cmd)}")
    
    p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    
    if out:
        log_accumulator.add(f"\nHDFS output: {out.decode('utf-8')}")
    if err:
        log_accumulator.add(f"\nHDFS stderr: {err.decode('utf-8')}")

def run_parser(file_name, current_dir):

    #test.pdb_search.tsv
    search_file = file_name+"_search.tsv"

    cath_ids = defaultdict(int)
    plDDT_values = []

    search_file_path = os.path.join(current_dir,search_file)
    log_accumulator.add(f"\n\n Looking for _search.tsv file in {search_file_path}")

    with open(search_file_path, "r") as fhIn:
        next(fhIn)
        msreader = csv.reader(fhIn, delimiter='\t',)
        for i, row in enumerate(msreader):
            plDDT_values.append(float(row[3]))
            meta = row[15]
            data = json.loads(meta)
            cath_ids[data["cath"]] += 1
    
        
        # Create a temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir: 

            output_file = os.path.join(temp_dir, f"{file_name}.parsed")
            with open(output_file, "w", encoding="utf-8") as fhOut:
                if len(plDDT_values) > 0:
                    fhOut.write(f"#{sys.argv[2]} Results. mean plddt: {statistics.mean(plDDT_values)}\n")
                else:
                    fhOut.write(f"#{sys.argv[2]} Results. mean plddt: 0\n")
                fhOut.write("cath_id,count\n")
                for cath, v in cath_ids.items():
                    fhOut.write(f"{cath},{v}\n")
            add_to_hdfs(output_file, 'hdfs://mgmtnode:9000/parsed/')

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
            run_merizo_search(pdb_file_path, file_name)
            
            
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