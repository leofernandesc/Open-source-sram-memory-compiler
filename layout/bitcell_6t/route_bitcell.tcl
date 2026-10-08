# Route the frozen 6T bitcell scaffold produced by generate_import.tcl.
# The six SKY130 PCells remain unchanged; only parent-level interconnect,
# body taps, labels, and ports are added here.

load bitcell_6t_placed
save bitcell_6t
snap internal

proc m3_rail {y} {
    box values -450 [expr {$y - 42}] 3000 [expr {$y + 42}]
    paint metal3
}

proc terminal_to_m3 {tx ty vx track {sd_half_y 0}} {
    # Generated/repaired leaf devices already expose D/S/G/body on M1.
    # Extend M1 laterally to a dedicated Via1 column, then route vertically
    # on M2 and land on the logical M3 rail.
    # Source/drain contacts are native M1 rings around a ViaLI array.  Fill
    # that ring before leaving horizontally so no narrow M1 notch remains.
    if {$sd_half_y > 0} {
        box values [expr {$tx - 24}] [expr {$ty - $sd_half_y}] \
                   [expr {$tx + 24}] [expr {$ty + $sd_half_y}]
        paint metal1
    }

    set m1lo [expr {min($tx, $vx) - 20}]
    set m1hi [expr {max($tx, $vx) + 20}]
    box values $m1lo [expr {$ty - 18}] $m1hi [expr {$ty + 18}]
    paint metal1

    box values [expr {$vx - 36}] [expr {$ty - 36}] \
               [expr {$vx + 36}] [expr {$ty + 36}]
    paint metal1
    paint metal2
    box values [expr {$vx - 26}] [expr {$ty - 26}] \
               [expr {$vx + 26}] [expr {$ty + 26}]
    contact m2contact

    set ylo [expr {min($ty, $track) - 42}]
    set yhi [expr {max($ty, $track) + 42}]
    box values [expr {$vx - 42}] $ylo [expr {$vx + 42}] $yhi
    paint metal2

    box values [expr {$vx - 42}] [expr {$track - 42}] \
               [expr {$vx + 42}] [expr {$track + 42}]
    paint metal3
    box values [expr {$vx - 30}] [expr {$track - 30}] \
               [expr {$vx + 30}] [expr {$track + 30}]
    contact m3contact
}

# One horizontal M3 rail per logical net.  M2 is used only for vertical
# branches, which allows crossings without accidental shorts.
set VDD_Y -400
set Q_Y   -550
set QB_Y  -700
set VSS_Y -2450
set WL_Y  -2600
set BL_Y  -2750
set BLB_Y -2900

foreach y [list $VDD_Y $Q_Y $QB_Y $VSS_Y $WL_Y $BL_Y $BLB_Y] {
    m3_rail $y
}

# Left inverter: PU_L / PD_L and left access transistor.
# PU_L center=(200,-1000): source=VDD, drain=Q, gate=QB
terminal_to_m3 156 -1000    0 $VDD_Y 42
terminal_to_m3 244 -1000  480 $Q_Y   42
terminal_to_m3 200  -894 -160 $QB_Y
terminal_to_m3 200  -792  160 $VDD_Y

# PD_L center=(200,-1900): source=VSS, drain=Q, gate=QB
terminal_to_m3 156 -1900    0 $VSS_Y 126
terminal_to_m3 244 -1900  480 $Q_Y   126
terminal_to_m3 200 -1719 -160 $QB_Y
terminal_to_m3 200 -1617  160 $VSS_Y

# ACC_L center=(1400,-1900): left diffusion=BL, right diffusion=Q, gate=WL
terminal_to_m3 1356 -1900 1240 $BL_Y
terminal_to_m3 1444 -1900 1600 $Q_Y  60
terminal_to_m3 1400 -1785 2800 $WL_Y
terminal_to_m3 1400 -1683 1760 $VSS_Y

# Right inverter: PU_R / PD_R and right access transistor.
# PU_R center=(900,-1000): source=VDD, drain=QB, gate=Q
terminal_to_m3 856 -1000  640 $VDD_Y 42
terminal_to_m3 944 -1000 1120 $QB_Y  42
terminal_to_m3 900  -894 1280 $Q_Y
terminal_to_m3 900  -792  800 $VDD_Y

# PD_R center=(800,-1900): source=VSS, drain=QB, gate=Q
terminal_to_m3 756 -1900  640 $VSS_Y 126
terminal_to_m3 844 -1900 1120 $QB_Y  126
terminal_to_m3 800 -1719  960 $Q_Y
terminal_to_m3 800 -1617  800 $VSS_Y

# ACC_R center=(2000,-1900): left diffusion=BLB, right diffusion=QB, gate=WL
terminal_to_m3 1956 -1900 1920 $BLB_Y 60
terminal_to_m3 2044 -1900 2240 $QB_Y  60
terminal_to_m3 2000 -1785 2800 $WL_Y
terminal_to_m3 2000 -1683 2400 $VSS_Y

# Ports live on M3 rails, away from device-level routing.
proc make_port {name index x y} {
    set xlo [expr {$x - 25}]
    set xhi [expr {$x + 25}]
    set ylo [expr {$y - 25}]
    set yhi [expr {$y + 25}]
    box values $xlo $ylo $xhi $yhi
    label $name center metal3
    select clear
    select do labels
    select area metal3
    port make $index n
    select clear
    select no labels
}

make_port VDD 0 -230 $VDD_Y
make_port BL  1 -230 $BL_Y
make_port BLB 2 -230 $BLB_Y
make_port VSS 3 -230 $VSS_Y
make_port WL  4 -230 $WL_Y

drc euclidean on
drc style drc(full)
drc on
select top cell
expand
drc catchup
set bitcell_route_errors [drc listall why]
puts "BITCELL_ROUTE_DRC_ERRORS=[llength $bitcell_route_errors]"
if {[llength $bitcell_route_errors] > 0} {
    puts "BITCELL_ROUTE_DRC_DETAIL=$bitcell_route_errors"
}

save bitcell_6t
quit -noprompt
