# Initial SKY130A physical scaffold for the frozen sense-amplifier leaf.
set project_root "/work"
set netlist "$project_root/layout/sense_amp/sense_amp_import.spice"

# netlist_to_layout temporarily restores the cell that was active when the
# import started.  A named scratch cell keeps that context editable in
# headless Magic; it is never saved to disk.
load __sense_amp_import_scratch__
magic::netlist_to_layout $netlist sky130

set physical_top sense_amp_sram6t
set physical_children [cellname list children $physical_top]
foreach child $physical_children {
    load $child
    save $child
}
load $physical_top
save sense_amp_import

select top cell
box select
puts "SENSE_AMP_IMPORT_BBOX=[box values]"

drc check
drc count total
quit -noprompt
