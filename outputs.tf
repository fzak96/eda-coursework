output host_vm_ids {
  value = harvester_virtualmachine.hostvm[*].network_interface[*].ip_address
}

output host_vm_ips {
  value = harvester_virtualmachine.hostvm.*.id
}