import sys
import csv
import json
from collections import defaultdict
import statistics
import os

# Location to save the output
dir_for_output = '/home/alamlinux'

cath_ids = defaultdict(int)
plDDT_values = []
id = sys.argv[2].rstrip("_search.tsv")

search_file_path = os.path.join(sys.argv[1],sys.argv[2])

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
    
    output_file = os.path.join(dir_for_output, f"{id}.parsed")

    with open(output_file, "w", encoding="utf-8") as fhOut:
        if len(plDDT_values) > 0:
            fhOut.write(f"#{sys.argv[2]} Results. mean plddt: {statistics.mean(plDDT_values)}\n")
        else:
             fhOut.write(f"#{sys.argv[2]} Results. mean plddt: 0\n")
        fhOut.write("cath_id,count\n")
        for cath, v in cath_ids.items():
            fhOut.write(f"{cath},{v}\n")
