import subprocess
import re
import csv
import numpy as np
import matplotlib.pyplot as plt

NUM_SAMPLES = 10
SPICE_FILE = "inversor_mc.spice"
CSV_FILE = "resultados_mc_inversor.csv"
PLOT_FILE = "grafico_vm_monte_carlo.png"

resultados = []

print(f"Iniciando {NUM_SAMPLES} execuções independentes de Monte Carlo no ngspice...\n")

for i in range(1, NUM_SAMPLES + 1):
    # Executa o ngspice em modo batch (-b) para cada amostra independente
    proc = subprocess.run(
        ["ngspice", "-b", SPICE_FILE],
        capture_output=True,
        text=True
    )
    
    # Busca o valor medido de 'vm = <valor>' na saída do ngspice
    match = re.search(r"vm\s*=\s*([0-9eE\.\+\-]+)", proc.stdout, re.IGNORECASE)
    if match:
        vm_val = float(match.group(1))
        resultados.append((i, vm_val))
        print(f"Amostra {i:02d}: Vm = {vm_val:.6f} V")
    else:
        print(f"Erro na amostra {i:02d}. Saída do ngspice:\n{proc.stderr}\n{proc.stdout}")
        break

if len(resultados) == NUM_SAMPLES:
    vms = np.array([r[1] for r in resultados])
    media = np.mean(vms)
    desvio = np.std(vms, ddof=1)
    minimo = np.min(vms)
    maximo = np.max(vms)

    # 1. Salvar CSV
    with open(CSV_FILE, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Amostra", "Vm_V"])
        for amostra, vm in resultados:
            writer.writerow([amostra, f"{vm:.6f}"])
        writer.writerow([])
        writer.writerow(["Media_V", f"{media:.6f}"])
        writer.writerow(["Desvio_Padrao_V", f"{desvio:.6f}"])
        writer.writerow(["Minimo_V", f"{minimo:.6f}"])
        writer.writerow(["Maximo_V", f"{maximo:.6f}"])

    print(f"\nResumo Estatístico ({NUM_SAMPLES} amostras):")
    print(f"  Média (μ):         {media:.6f} V")
    print(f"  Desvio Padrão (σ): {desvio:.6f} V ({desvio*1000:.3f} mV)")
    print(f"  Mínimo / Máximo:   {minimo:.6f} V / {maximo:.6f} V")
    print(f"\nCSV salvo em: {CSV_FILE}")

    # 2. Gerar Gráfico
    amostras = [r[0] for r in resultados]
    plt.figure(figsize=(8, 4.8))
    plt.plot(amostras, vms, marker="o", linestyle="-", color="#1f77b4", linewidth=2, label="Vm medido")
    plt.axhline(media, color="#d62728", linestyle="--", linewidth=1.5, label=f"Média = {media:.4f} V")
    plt.fill_between(
        amostras,
        media - desvio,
        media + desvio,
        color="#d62728",
        alpha=0.15,
        label=f"±1σ ({desvio*1000:.2f} mV)"
    )

    plt.title("Variação da Tensão de Chaveamento (Vm) - Monte Carlo SKY130A (10 Amostras)")
    plt.xlabel("Número da Amostra")
    plt.ylabel("Tensão de Chaveamento Vm (V)")
    plt.xticks(amostras)
    plt.grid(True, linestyle=":", alpha=0.7)
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOT_FILE, dpi=300)
    print(f"Gráfico salvo em: {PLOT_FILE}")
