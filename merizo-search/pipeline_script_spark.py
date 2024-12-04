from pyspark.sql import SparkSession
from pyspark import SparkContext
from subprocess import Popen, PIPE
import tempfile
import os
import sys
from typing import Tuple, Dict

def run_merizo_search(pdb_file_path: str, output_prefix: str):

    cmd = ['python',
           'home/almalinux/merizo-search/merizo-search/merizo.py',
           'easy-search',
           pdb_file_path,
           '/home/almalinux/merizo-search/database/cath-4.3-foldclassdb',
           output_prefix,
           'tmp',
           '--iterate',
           '--output_headers',
           '-d',
           'cpu',
           '--threads',
           '1'
           ]
    
    print(f'STEP 1: RUNNING MERIZO: {" ".join(cmd)}')
    p = Popen(cmd, stdin=PIPE,stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()

def run_parser(file_name_without_extension):
    """
    Run the results_parser.py over the hhr file to produce the output summary
    """
    search_file = file_name_without_extension+"_search.tsv"
    print(search_file, sys.argv[2])
    cmd = ['python', 'results_parser.py', sys.argv[2], search_file]
    print(f'STEP 2: RUNNING PARSER: {" ".join(cmd)}')
    p = Popen(cmd, stdin=PIPE,stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    print(out.decode("utf-8"))

def process_pdb(record: Tuple[str, str]):

    filepath, content = record
    
    # Extract file name from the file path
    file_name = filepath.rsplit('/', 1)[-1]

    if(file_name.endswith('.pdb')):
        base_id = file_name[:-4]
    else:
        base_id = file_name
        file_name= file_name + ".pdb"
    
    # Create a temporary directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create PDB file with proper name
        pdb_file_path = os.path.join(temp_dir, f"{file_name}")
        
        # Create a temporary PDB file
        with open(pdb_file_path, 'w') as f:
            f.write(content)
        
        # Run merizo search
        run_merizo_search(pdb_file_path, file_name)
        
        # Run Parser
        run_parser(base_id)
        

def main():
    # Initialize Spark session
    spark = SparkSession.builder.appName("MerizoSearchApp").getOrCreate()
    
    # Read PDB files from HDFS
    pdb_files = spark.sparkContext.wholeTextFiles("/analysis/*.pdb")
    print(pdb_files.collect())
    
    pdb_files.map(process_pdb)
    
    spark.stop()

if __name__ == "__main__":
    main()

        