#!/usr/bin/env python3
"""Incremental narrative for the existing 22 slides; preserves published deck."""
import hashlib
import json
import shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent;BASE=OUT.parent


def main():
    slides=json.loads((BASE/'slides.json').read_text())
    s=slides[13];s['source']=['docs/phase2_timing_extension.md','reports/phase2/extension_20261104/c2_bus/results.json']
    s['speech']='Este recorte é da leitura da linha 1 na campanha nova de barramento, depois de a saída ter registrado AA. A nova palavra é 55. A wordline ativa desenvolve o diferencial e SCLK inicia a regeneração. RAW e a entrada do FF já ficam disponíveis durante a fase alta, mas FF_Q e DATA mantêm o resultado anterior até a captura na descida. O clock local chega cerca de 0,23 a 0,25 nanossegundo depois da descida pública. Nos bits que mudaram, o novo DATA ficou válido cerca de 0,49 a 0,55 nanossegundo depois dessa descida. São medidas da bancada nominal, sem carga externa caracterizada.'
    s['caveat']='Fonte C2, ciclo 7; TT, sem wire RC. A validade de DATA é distinta da habilitação do driver.'
    s=slides[14];s['speech']+=' No top final e nas sequências adicionais, a guarda entre liberação da pré-carga e escrita ficou em torno de 212 ps. Esses resultados usam circuitos e estímulos distintos dos dois pilotos da figura.'
    s['source'].append('docs/phase2_timing_extension.md')
    s=slides[16];s['bullets']=['Dirigida anterior: 1.332 checks, incluindo 160 bits lidos.',
        'C1: 1.150 checks; leituras e reescritas adjacentes na mesma linha.',
        'C2: 1.281 checks; máscara viva e corrente do barramento.']
    s['source']=['docs/phase2_coverage_extension.md','reports/phase2/extension_20261104/c1_sequences/results.json']
    s['speech']='A campanha anterior cobria walking-one e walking-zero. A auditoria dos estímulos mostrou duas lacunas mais específicas: leituras consecutivas da mesma linha e escritas complementares adjacentes nela. C1 passou nesses casos, verificando também as outras palavras conhecidas. O gráfico mostra a troca dos nós de armazenamento e a saída registrada. C2 acrescentou observação de corrente na liberação e reativação do barramento. Os 1.150 e 1.281 checks já incluem 72 e 48 bits lidos, respectivamente. O piloto é subconjunto e não aumenta cobertura exclusiva. Também conferimos pré-carga e estabilidade nos mesmos transientes; não são outras transações.'
    s['caveat']='Gráfico C1, 128..288 ns; ambos os novos testes utilizam o mesmo DUT físico e TT nominal.'
    s=slides[17];s['kind']='bus_timing';s['title']='Contrato temporal e barramento'
    s['bullets']=['FF_Q preservado durante a máscara viva.',
        'Liberação: corrente e tensão verificadas juntas.',
        'Sob probe de 1 kΩ: tDIS ≈0,13–0,18 ns; tEN ≈0,63 ns.',
        'Medidas nominais; turnaround garantido pendente.']
    s['source']=['docs/phase2_timing_extension.md','specs/sram_4x8_timing_contract.md']
    s['speech']='O contrato mantém subida para capturar a requisição e descida para capturar leitura. Nesta figura, depois da leitura, aplicamos um probe de um quilo-ohm contra o valor de saída. É uma calibração externa para observar se o driver conduz; DATA não precisa ser nível lógico válido enquanto essa carga oposta está ligada. Ao retirar a leitura viva por CSb, a corrente cai e DATA acompanha o probe, enquanto FF_Q permanece constante. Quando restauramos CSb, volta a existir corrente. Após retirar o probe, o dado normal é recuperado. O atraso indicado usa um piso de cinquenta microampères, não uma especificação de leakage ou de turnaround. Na troca para o mestre forte, as guardas ensaiadas de 0,3 e 0,6 nanossegundo não apresentaram sobreposição detectada. Não são guardas mínimas garantidas.'
    s['caveat']='tDIS/tEN no slide abreviam cruzamentos nominais de corrente sob o probe declarado; não são limites públicos qualificados.'
    s['transition']='A partida continua apoiada nos cinco cenários já publicados.'
    s=slides[19];s['bullets'][3]='Sequências críticas, máscara viva e partida nominal verificadas.'
    s['source'].append('docs/phase2_extension_state_20261104.md')
    s['speech']+=' A rodada adicional não alterou circuito ou layout. A revisão dos dados também foi reproduzida num worktree limpo, usando o pacote opcional de transientes. Essa reprodução é da análise: não foi outra execução de SPICE.'
    s=slides[20];s['speech']+=' As medições novas de DATA e corrente continuam nominais, sem transformar os parâmetros públicos pendentes em garantias.'
    (OUT/'slides.json').write_text(json.dumps(slides,ensure_ascii=False,indent=2)+'\n')
    # Markdown references become relative to this deeper presentation folder.
    outline=['# Apresentação técnica da Fase 2 — rodada complementar\n']
    notes=['# Roteiro de fala — revisão complementar da Fase 2\n']
    for i,s in enumerate(slides,1):
        refs='; '.join(f'[{Path(r).name}](../../../{r})' for r in s['source'])
        outline.append(f"## Slide {i} — {s['title'].replace(chr(10),' ')}\n\n"+'\n'.join('- '+b for b in s['bullets'])+f'\n\nFontes: {refs}.\n')
        notes.append(f"## Slide {i} — {s['title'].replace(chr(10),' ')}\n\nObjetivo: {s['takeaway']}\n\n{s['speech']}\n\nRessalva: {s['caveat']}\n\nTransição: {s['transition']}\n\nFontes: {refs}.\n")
    (OUT/'phase2_technical_review.md').write_text('\n'.join(outline));(OUT/'speaker_notes.md').write_text('\n'.join(line.rstrip() for line in '\n'.join(notes).splitlines())+'\n')
    qa=(BASE/'technical_qa.md').read_text().replace('../../','../../../')
    additions={8:'No top final, a nova medição PRECH80→WE20 foi 211,3–212,9 ps. WL80 antecedeu SCLK20 em 238,5–243,9 ps; taps não foram modificados.',
      9:'No modelo sem wire RC, o diferencial com sinal correto já foi observado 50 ps antes de SCLK20. Isso confirma a ordem nesse experimento, sem caracterizar sensibilidade do SA.',
      11:'As menores janelas novas foram cerca de 7,435 ns em RAW e 7,240 ns em FF_D antes do clock local. FF_Q mudou após 0,190–0,223 ns; DATA válido apareceu 0,489–0,549 ns após a descida pública, nos bits que mudaram. Esses instantes distinguem clock local, mux, registro e driver.',
      16:'Uma segunda passagem conferiu o complemento físico de DIN e os oito NANDs equivalentes dos enables. A primeira versão desse auditor presumiu uma rede comum e foi corrigida; não houve defeito no circuito.',
      18:'C1 acrescentou READ→READ e WRITE→WRITE na mesma linha, com checks das palavras não selecionadas. Foram 1.150 checks, incluindo 72 bits lidos.',
      23:'C2 passou em 1.281 checks, incluindo 48 bits. Com probe oposto de 1 kΩ, os cruzamentos de corrente de 50 µA ocorreram em ~0,13–0,18 ns ao desativar e ~0,63 ns ao reativar. Não são máximos garantidos. Os handoffs de 0,3/0,6 ns não tiveram sobreposição detectada. O dado anterior pode aparecer durante a fase alta antes da nova captura.',
      24:'A extensão acrescenta um bundle opcional no mesmo formato, com três raws (piloto C1, C1 completo e C2). Nenhum dump grande é incluído no Git; sem transferência do pacote, é necessário regenerar as campanhas.'}
    import re
    for n,text in additions.items():
        pattern=rf'(## {n}\. .*?)(?=\n## \d+\.|\Z)'
        qa=re.sub(pattern,lambda m:m[0].rstrip()+'\n\n'+text+' [Análise complementar](../../../docs/phase2_timing_extension.md).\n',qa,flags=re.S)
    (OUT/'technical_qa.md').write_text(qa)
    assets=OUT/'assets';assets.mkdir(exist_ok=True)
    meta=json.loads((BASE/'assets/sources.json').read_text())
    for n in meta:shutil.copyfile(BASE/'assets'/n,assets/n)
    new=ROOT/'reports/phase2/extension_20261104/figures_revised';sources=json.loads((new/'sources.json').read_text())
    for dest,src in [('access_phases.png','read_path.png'),('storage_readback.png','consecutive_access.png'),('bus_mask_current.png','bus_mask_current.png')]:
        shutil.copyfile(new/src,assets/dest);meta[dest]=sources[src]
    (assets/'sources.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
    renderer=(BASE/'build_deck.py').read_text().replace('parents[2]','parents[3]')
    renderer=renderer.replace("  elif kind=='timing':", "  elif kind=='bus_timing':\n   picture(s,'bus_mask_current.png',.65,1.55,8.2,4.65);bullet_list(s,d['bullets'],x=9.15,y=1.8,w=3.45,step=1.12,size=15.5)\n  elif kind=='timing':")
    renderer=renderer.replace('if a.refresh_figures:figures()',"if a.refresh_figures:p.error('Use plot_phase2_extension.py and prepare_deck.py for extension figures')")
    (OUT/'build_deck.py').write_text(renderer)
    (OUT/'base_reference.json').write_text(json.dumps(dict(base_commit='4ffbbf571bdff1c995de5bd2815083b3a0eda3d0',
       source_slides_sha256=hashlib.sha256((BASE/'slides.json').read_bytes()).hexdigest(),
       renderer_base_sha256=hashlib.sha256((BASE/'build_deck.py').read_bytes()).hexdigest(),
       changed_slides=[14,15,17,18,20,21],unchanged_slide_count=16,
       scope='Same 22-slide narrative; incremental evidence and wording only. Published original preserved.'),indent=2)+'\n')


if __name__=='__main__':main()
