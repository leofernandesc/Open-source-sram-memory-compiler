drc euclidean on
drc style drc(full)
drc on

foreach cell {column_32_full_g7_wpre2p52 column_32_full_g7_wpre2p52_flat} {
    load $cell
    select top cell
    expand
    box select
    drc check
    drc catchup
    set count 0
    foreach {rule boxes} [drc listall why] {
        incr count [llength $boxes]
    }
    puts "FULL_G7_DRC_$cell=$count"
    if {$count != 0} { error "full-cell DRC failed for $cell" }
}
quit -noprompt
