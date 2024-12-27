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
import sys

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

def run_merizo_search(pdb_file_path: str, file_name: str, hdfs_folder: str):


    # List files in current directory after command execution
    current_dir = os.getcwd()
    files_after = os.listdir(current_dir)


    cmd = ['python',
           '/home/almalinux/merizo-search/merizo.py',
           'easy-search',
           pdb_file_path,
           '/home/almalinux/merizo-search/database/cath-4.3-foldclassdb',
           file_name,
           'tmp',
           '--iterate',
           '--output_headers',
           ]
    
    p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()

    if p.returncode != 0:
        raise Exception(f"Merizo search failed: {err.decode('utf-8')}")

    # List files in current directory after command execution
    files_after = os.listdir(current_dir)

    #add segment and search files to hdfs

    segment_file_path = os.path.join(current_dir,file_name+'_segment.tsv')
    search_file_path = os.path.join(current_dir,file_name+'_search.tsv')

    hdfs_merizo_output_path = f"hdfs://mgmtnode:9000/data/{hdfs_folder}/"

    # Only add files if they exist
    if os.path.exists(segment_file_path):
        add_to_hdfs(segment_file_path, hdfs_merizo_output_path)
    else:
        log_accumulator.add(f"\nWarning: Segment file not found at {segment_file_path}")

    if os.path.exists(search_file_path):
        add_to_hdfs(search_file_path, hdfs_merizo_output_path)
    else:
        log_accumulator.add(f"\nWarning: Search file not found at {search_file_path}")
    
    if out:
        log_accumulator.add(f"\nMerizo output: {out.decode('utf-8')}")
    if err:
        log_accumulator.add(f"\nMerizo stderr: {err.decode('utf-8')}")

    run_parser(file_name,current_dir,hdfs_folder) #output prefix is the file name with extension

def add_to_hdfs(file_path, hdfs_path):
    """
    Add a file to HDFS
    """

    mkdir_cmd = ['/home/almalinux/hadoop-3.4.0/bin/hdfs', 'dfs', '-mkdir', '-p', hdfs_path]
    log_accumulator.add(f"\nCreating HDFS directory: {' '.join(mkdir_cmd)}")

    p = Popen(mkdir_cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()


    add_cmd = ['/home/almalinux/hadoop-3.4.0/bin/hdfs', 'dfs', '-copyFromLocal', file_path, hdfs_path]
    log_accumulator.add(f"\nAdding file to HDFS: {' '.join(add_cmd)}")
    
    p = Popen(add_cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    
    if out:
        log_accumulator.add(f"\nHDFS output: {out.decode('utf-8')}")
    if err:
        log_accumulator.add(f"\nHDFS stderr: {err.decode('utf-8')}")

def run_parser(file_name, current_dir, hdfs_folder):

    #test.pdb_search.tsv
    search_file = file_name+"_search.tsv"

    cath_ids = defaultdict(int)
    plDDT_values = []

    search_file_path = os.path.join(current_dir,search_file)

    # Add check for file existence
    if not os.path.exists(search_file_path):
        log_accumulator.add(f"\nError: Search file not found at {search_file_path}")
        return

    with open(search_file_path, "r") as fhIn:
        next(fhIn)
        msreader = csv.reader(fhIn, delimiter='\t',)
        tot_entries = 0
        for i, row in enumerate(msreader):
            tot_entries = i+1
            plDDT_values.append(float(row[3]))
            meta = row[15]
            data = json.loads(meta)
            cath_ids[data["cath"]] += 1
    
        
        # Create a temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir: 

            output_file = os.path.join(temp_dir, f"{file_name}.parsed")
            with open(output_file, "w", encoding="utf-8") as fhOut:
                if len(plDDT_values) > 0:
                    fhOut.write(f"#{search_file} Results. mean plddt: {statistics.mean(plDDT_values)}\n")
                else:
                    fhOut.write(f"#{search_file} Results. mean plddt: 0\n")
                fhOut.write("cath_id,count\n")
                for cath, v in cath_ids.items():
                    fhOut.write(f"{cath},{v}\n")
            hdfs_parsed_output_path = f"hdfs://mgmtnode:9000/parsed/{hdfs_folder}/"
            add_to_hdfs(output_file, hdfs_parsed_output_path)

def process_pdb(record, hdfs_folder):
    try:
        filepath, content = record
        
        # Extract file name from the file path
        file_name = filepath.rsplit('/', 1)[-1]
        
        if(file_name.endswith('.pdb')):
            base_id = file_name[:-4]
        else:
            base_id = file_name
            file_name = file_name + ".pdb"
        
        # Create a temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create PDB file with proper name
            pdb_file_path = os.path.join(temp_dir, f"{file_name}")
            
            # Create a temporary PDB file
            with open(pdb_file_path, 'w') as f:
                f.write(content)
            
            run_merizo_search(pdb_file_path, file_name, hdfs_folder)
            
            
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
    
    hdfs_folder = sys.argv[1]
    hdfs_input_path = f"hdfs://mgmtnode:9000/alphafold/{hdfs_folder}/*.pdb"

    # Create accumulator for worker logs
    global log_accumulator
    log_accumulator = spark.sparkContext.accumulator("", StringAccumulatorParam())

    # Get and process files
    pdb_files_rdd = spark.sparkContext.wholeTextFiles(hdfs_input_path)
    
    # Add indices and filter to first 100 elements, then add hdfs_folder
    # indexed_rdd = pdb_files_rdd.zipWithIndex()
    # filtered_rdd = indexed_rdd.filter(lambda x: x[1] < 100).map(lambda x: x[0])
    # filtered_rdd.map(lambda x: process_pdb(x, hdfs_folder)).collect()
    pdb_files_rdd.map(lambda x: process_pdb(x, hdfs_folder)).collect()
    
    logger.info(log_accumulator.value)
    spark.stop()

if __name__ == "__main__":
    main()