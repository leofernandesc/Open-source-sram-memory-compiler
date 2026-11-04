# Phase 2 technical presentation

22 slides; primary language Portuguese, title/subtitle in English. The deck
is intended for a 20–25 minute academic review plus discussion. No affiliation
or advisor name was invented: the repository establishes the team first names
Danilo, André and Leonardo, and no verified institution for this deck.

## Files

- `phase2_technical_review.pptx`: editable text, tables and native block diagrams.
- `phase2_technical_review.pdf`: reviewed visualization export.
- `slides.json`: editable narrative/content and Portuguese speaker notes.
- `make_content.py`: authored narrative source; regenerates slides.json and Markdown.
- `phase2_technical_review.md`: slide-by-slide outline and source links.
- `speaker_notes.md`: objective, speech, emphasis, caveat and transition per slide.
- `technical_qa.md`: 24 anticipated questions with repository references.
- `assets/`: real evidence figures and `sources.json` with provenance/hashes.
- `build_deck.py`: native PPTX/figure generation, no EDA execution.

## Edit, rebuild and export

For direct editing, open the PPTX in PowerPoint/LibreOffice, or import it into
Google Slides. Editable objects and notes are in the PPTX; plot images remain
raster figures. Google Slides import has not been executed or certified.

For reproducible content changes, edit `make_content.py`, run it, and build.
Alternatively edit `slides.json` for a one-off deck; running make_content.py
again replaces that JSON and its generated Markdown from the authored source.

The existing EDA container already supplies lxml, Pillow, NumPy and matplotlib.
Only three small Python packages were installed into an ignored local target,
without modifying the image or the system Python:

```sh
./tools/sram-eda python3 -m pip install --no-deps --target /work/build/phase2/presentation_deps -r presentations/phase2/requirements.txt
python3 presentations/phase2/make_content.py
./tools/sram-eda env PYTHONPATH=/work/build/phase2/presentation_deps python3 presentations/phase2/build_deck.py
```

A normal build reuses the selected PNGs and validates their hashes. To
regenerate waveform PNGs from the original full raw data, use `--refresh-figures`.
This requires the data identified in the receipts or its verified optional
transfer bundle; it never launches SPICE. Block diagrams are explanatory,
not presented as measured waveforms or physical geometries.

Linux PDF export used the existing LibreOffice with a separate profile:

```sh
libreoffice -env:UserInstallation=file:///absolute/project/build/presentations/libreoffice_profile --headless --convert-to pdf --outdir presentations/phase2 presentations/phase2/phase2_technical_review.pptx
```

Replace `/absolute/project` with this checkout. Validation checks slide count,
notes, object bounds, PDF text and representative rendered pages. Source
figures, hashes and current evidence remain the authority if a later edit
changes the presentation. No count includes a read-bit subset a second time.
