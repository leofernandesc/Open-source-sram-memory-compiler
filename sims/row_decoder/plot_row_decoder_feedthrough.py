#!/usr/bin/env python3
"""Plot the two measured feedthrough corrections from saved SPICE waveforms."""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from plot_row_decoder_review import read_raw


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("baseline_clock_raw", "fixed_clock_raw", "baseline_address_raw", "fixed_address_raw"):
        parser.add_argument(name,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    fig,axes=plt.subplots(2,1,figsize=(10,7),layout="constrained")
    for ax,base,fix,node,start,title in (
        (axes[0],args.baseline_clock_raw,args.fixed_clock_raw,"v(x1.n3)",10,
         "Unselected N3 after PCLK rises: TT, 1.8 V, 27 C, 50 ps edge"),
        (axes[1],args.baseline_address_raw,args.fixed_address_raw,"v(x1.a0b)",22,
         "A0B after A0 rises: SS, 1.8 V, -40 C, 50 ps address edge")):
        for file,label,color in ((base,"Before sizing correction","firebrick"),
                                  (fix,"After sizing correction","seagreen")):
            traces=read_raw(file)
            t=traces["time"]*1e9
            keep=(t>=start-.03)&(t<=start+.2)
            ax.plot((t[keep]-start)*1000,traces[node][keep],label=label,color=color)
        ax.axhline(1.95,color="black",ls="--",label="1.95 V upper model screen")
        ax.axhline(1.8,color="gray",ls=":",label="VDD")
        ax.set(title=title,xlabel="Time from input edge start (ps)",ylabel="Voltage (V)",ylim=(1.70,2.04))
        ax.legend(fontsize=9,loc="upper right")
        ax.grid(alpha=.25)
    fig.suptitle("Dynamic decoder: precharge and address feedthrough correction (pre-layout)")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(args.output,dpi=160)
    plt.close(fig)
    print(args.output)


if __name__=="__main__":
    main()
