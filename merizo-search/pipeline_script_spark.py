from pyspark.sql import SparkSession
from pyspark import SparkContext
from subprocess import Popen, PIPE
import tempfile
import os
import sys
from typing import Tuple, Dict
import logging
import subprocess
from typing import Tuple, Optional


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('merizo_pipeline.log'),
        logging.StreamHandler()
    ]
)


def run_command(cmd: list) -> Tuple[Optional[str], Optional[str]]:

    # Convert the command list to a string for logging
    cmd_str = " ".join(cmd)
    logging.info(f"Executing command: {cmd_str}")
    
    try:
        # Start the subprocess and wait for it to complete
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        
        # Convert the output and error messages to strings
        out_str = out.decode("utf-8") if out else None
        err_str = err.decode("utf-8") if err else None
        
        # Check if the command was successful
        if p.returncode != 0:
            logging.error(f"Command failed with return code {p.returncode}")
            logging.error(f"Error output: {err_str}")
            raise subprocess.CalledProcessError(
                p.returncode, cmd_str, output=out_str, stderr=err_str
            )
        
        # Log success and return the results
        logging.info("Command completed successfully")
        if out_str:
            logging.info(f"Output: {out_str}")
        
        return out_str, err_str
            
    except FileNotFoundError:
        # This happens if we can't find the program we're trying to run
        logging.error(f"Command not found: {cmd[0]}")
        raise
        
    except Exception as e:
        # Catch any other unexpected errors
        logging.error(f"Unexpected error running command: {str(e)}")
        raise



def run_merizo_search(pdb_file_path: str, output_prefix: str):

    cmd = ['python',
           '/home/almalinux/merizo-search/merizo-search/merizo.py',
           'easy-search',
           pdb_file_path,
           '/home/almalinux/merizo-search/database/cath-4.3-foldclassdb',
           output_prefix,
           'tmp',
           '--iterate',
           '--output_headers',
           '-d',
           ]
    
    print(f'STEP 1: RUNNING MERIZO: {" ".join(cmd)}')
    p = Popen(cmd, stdin=PIPE,stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    print(out.decode("utf-8"))
    print(err.decode("utf-8"))


    try:
        out, err = run_command(cmd)
        if out:
            logging.info("Merizo search completed successfully")
            logging.debug(f"Merizo output: {out}")
    except Exception as e:
            logging.error(f"Merizo search failed: {str(e)}")
    raise  

def run_parser(file_name_without_extension):
    """
    Run the results_parser.py over the hhr file to produce the output summary
    """
    search_file = file_name_without_extension+"_search.tsv"
    output_dir = '/home/amalinux/'
    print(search_file, output_dir)
    cmd = ['python', 'results_parser.py', output_dir, search_file]
    print(f'STEP 2: RUNNING PARSER: {" ".join(cmd)}')
    p = Popen(cmd, stdin=PIPE,stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    print(out.decode("utf-8"))
    print(err.decode("utf-8"))

def process_pdb(record: Tuple[str, str]):

    filepath, content = record
    
    # Extract file name from the file path
    file_name = filepath.rsplit('/', 1)[-1]

    if(file_name.endswith('.pdb')):
        base_id = file_name[:-4]
    else:
        base_id = file_name
        file_name= file_name + ".pdb"

    logging.info(f"Processing file: {file_name}")
    logging.info(f"Base file name: {base_id}")
    
    # Create a temporary directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create PDB file with proper name
        pdb_file_path = os.path.join(temp_dir, f"{file_name}")
        logging.info(f"pdb_file_path: {pdb_file_path}")
        # Create a temporary PDB file
        with open(pdb_file_path, 'w') as f:
            f.write(content)
        
        # Run merizo search
        run_merizo_search(pdb_file_path, file_name)
        
        # Run Parser
        run_parser(base_id)
        

def main():
    # Initialize Spark session
    spark = SparkSession.builder.appName("MerizoSearchApp") \
    .config("spark.hadoop.fs.defaultFS", "hdfs://mgmtnode:9000").getOrCreate()
    
    
    pdb_files_rdd = spark.sparkContext.wholeTextFiles("hdfs://mgmtnode:9000/analysis/*.pdb")    
    pdb_files_rdd.map(process_pdb).collect()
    
    spark.stop()

if __name__ == "__main__":
    main()

        