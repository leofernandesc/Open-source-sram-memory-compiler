load write_driver_layout
save write_driver_routed_hier
flatten write_driver_flat
load write_driver_flat
drc check
drc count total
save write_driver_flat
quit -noprompt
