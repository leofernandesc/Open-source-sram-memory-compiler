# Apresentação complementar da Fase 2

Esta revisão mantém os 22 slides e a estrutura da
[apresentação publicada](../README.md). Atualiza slides 14, 15, 17, 18, 20 e
21 com resultados de C1/C2, captura e corrente. Os outros 16 slides permanecem
com o mesmo conteúdo. A apresentação e os relatórios anteriores continuam
intactos. Linguagem oral e notas em português; texto e diagramas editáveis.

- [PPTX editável](phase2_technical_review.pptx).
- [PDF de visualização](phase2_technical_review.pdf).
- [Conteúdo por slide](phase2_technical_review.md).
- [Roteiro de fala](speaker_notes.md).
- [24 perguntas e respostas](technical_qa.md), com atualização das respostas
  existentes sobre fases, sense, captura, barramento e dados brutos.
- `slides.json`: conteúdo e notas da revisão.
- `assets/sources.json`: origem e hashes das figuras reais.
- `base_reference.json`: identidade das fontes publicadas e slides alterados.

`prepare_deck.py` aplica a atualização incremental sobre o deck anterior,
prepara textos/figuras e adapta o renderer para o novo diretório e gráfico
de barramento. Não executa EDA. Para editar esta revisão de forma persistente,
alterar esse script; rodá-lo novamente recria JSON, Markdown e renderer.
O PPTX também pode ser editado diretamente, sem alegar que mudanças manuais
preservam os hashes ou a reprodutibilidade do build.

```sh
python3 presentations/phase2/extension_20261104/prepare_deck.py
./tools/sram-eda env PYTHONPATH=/work/build/phase2/presentation_deps python3 presentations/phase2/extension_20261104/build_deck.py
libreoffice -env:UserInstallation=file:///absolute/project/build/presentations/extension_lo_profile --headless --convert-to 'pdf:impress_pdf_Export:{"UseTaggedPDF":{"type":"boolean","value":"false"}}' --outdir presentations/phase2/extension_20261104 presentations/phase2/extension_20261104/phase2_technical_review.pptx
```

Substituir `/absolute/project` pelo checkout. Dependências pequenas e a opção
de instalação no diretório ignorado estão no README da apresentação anterior.
Para novas figuras, usar `tools/plot_phase2_extension.py --output` com um
diretório novo e os raws verificados; revisar a seleção em `prepare_deck.py`.
Não usar o modo de refresh do renderer antigo para substituir as curvas novas.
Não foi executada importação em Google Slides.

Os totais incluem seus subconjuntos de bits lidos. Reanálise dos mesmos dados,
piloto e testes dos scripts não são apresentados como transações exclusivas
da SRAM. O probe oposto de 1 kΩ é identificado como calibração externa;
DATA não precisa manter nível lógico enquanto submetido a esse probe.
