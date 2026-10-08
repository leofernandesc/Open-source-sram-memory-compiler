"""Locate the two storage nodes of a Magic-extracted 6T bitcell."""

import re


def bitcell_storage_nodes(netlist: str) -> tuple[str, str]:
    access: dict[str, str] = {}
    for line in netlist.splitlines():
        parts = line.split()
        if (
            len(parts) < 7
            or not parts[0].startswith("X")
            or parts[2].split(".")[0] != "WL"
            or parts[5] != "sky130_fd_pr__nfet_01v8"
            or "w=0.6" not in parts
        ):
            continue
        first, third = parts[1], parts[3]
        if re.fullmatch(r"BLB?(?:\.t\d+)?", first):
            bitline, storage = first, third
        elif re.fullmatch(r"BLB?(?:\.t\d+)?", third):
            bitline, storage = third, first
        else:
            continue
        access[bitline.split(".")[0]] = storage
    if set(access) != {"BL", "BLB"}:
        raise ValueError(f"expected BL and BLB access devices, found {access}")
    # Magic splits each storage net into resistor-connected terminals.  The
    # inverter output is the stable latch node; the access-device terminal
    # can be separated from it by hundreds of ohms in extracted PEX.
    return storage_output_node(access["BL"]), storage_output_node(access["BLB"])


def storage_output_node(node: str) -> str:
    base = re.sub(r"\.t\d+$", "", node)
    return f"{base}.t0"
