#!/usr/bin/env python3

import json
import subprocess
import argparse

def run(command):
    return subprocess.run(command, capture_output=True, encoding='UTF-8')

def generate_inventory():
    command = "terraform output --json mgmt_vm_ips".split()
    ip_data = json.loads(run(command).stdout)
    mgmt_node = ip_data.pop()

    host_vars = {}

    host_vars[mgmt_node] = { "ip": [mgmt_node] }


    command = "terraform output --json storage_vm_ips".split()
    ip_data = json.loads(run(command).stdout)
    storage_node = ip_data.pop()
    host_vars[storage_node] = { "ip": [storage_node] }



    counter = 0
    worker_nodes = []

    command = "terraform output --json worker_vm_ips".split()
    ip_data = json.loads(run(command).stdout)

    for a in ip_data:
        name = a
        host_vars[name] = { "ip": [a] }
        worker_nodes.append(name)
        counter += 1

    _meta = {}
    _meta["hostvars"] = host_vars
    _all = { "children": ["mgmtnode", "workernodes", "storagenode"] }

    _workernodes = { "hosts": worker_nodes }
    _mgmtnode = { "hosts" : [mgmt_node] }
    _storagenode = { "hosts" : [storage_node] }

    _jd = {}
    _jd["_meta"] = _meta
    _jd["all"] = _all
    _jd["workernodes"] = _workernodes
    _jd["mgmtnode"] = _mgmtnode
    _jd["storagenode"] = _storagenode

    jd = json.dumps(_jd, indent=4)
    return jd


if __name__ == "__main__":

    ap = argparse.ArgumentParser(
        description = "Generate a cluster inventory from Terraform.",
        prog = __file__
    )

    mo = ap.add_mutually_exclusive_group()
    mo.add_argument("--list",action="store", nargs="*", default="dummy", help="Show JSON of all managed hosts")
    mo.add_argument("--host",action="store", help="Display vars related to the host")

    args = ap.parse_args()

    if args.host:
        print(json.dumps({}))
    elif len(args.list) >= 0:
        jd = generate_inventory()
        print(jd)
    else:
        raise ValueError("Expecting either --host $HOSTNAME or --list")

    
