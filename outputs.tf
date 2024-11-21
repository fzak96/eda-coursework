output mgmt_vm_ids {
  value = harvester_virtualmachine.mgmtvm[*].network_interface[*].ip_address
}

output mgmt_vm_ips {
  value = harvester_virtualmachine.mgmtvm.*.id
}

output worker_vm_ids {
  value = harvester_virtualmachine.workervm[*].network_interface[*].ip_address
}

output worker_vm_ips {
  value = harvester_virtualmachine.workervm.*.id
}