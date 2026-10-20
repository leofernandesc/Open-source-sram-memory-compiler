load wl_driver_layout
save wl_driver_routed_hier
flatten wl_driver_flat
load wl_driver_flat
drc check
drc count total
save wl_driver_flat
quit -noprompt
