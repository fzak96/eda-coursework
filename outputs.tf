output mgmt_vm_ids {
  value = harvester_virtualmachine.mgmtvm[*].network_interface[*].ip_address
}

output mgmt_vm_ips {
  value = harvester_virtualmachine.mgmtvm.*.id
}