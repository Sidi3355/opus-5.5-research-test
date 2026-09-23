# Build every version of the paper. Run from paper/: `make` builds all, `make iclr` builds one.
# Output goes to build/<version>/<version>.pdf (not tracked); `python3 package.py` then copies
# the final PDFs, supplementary zip and arXiv source into ../submission/.
#
#   iclr, icml, neurips              anonymous submissions (official submission styles)
#   iclr_named, icml_named, neurips_named    named preprints (neurips_named is also the arXiv version)
VERSIONS = iclr icml neurips iclr_named icml_named neurips_named
STY_iclr = iclr2027
STY_iclr_named = iclr2027
STY_icml = icml2026
STY_icml_named = icml2026
STY_neurips = neurips2026
STY_neurips_named = neurips2026

all: $(VERSIONS)

$(VERSIONS):
	TEXINPUTS=.:$(CURDIR)/styles/$(STY_$@)//: BSTINPUTS=$(CURDIR)/styles/$(STY_$@)//: BIBINPUTS=$(CURDIR): \
	latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=build/$@ venues/$@.tex

clean:
	rm -rf build

.PHONY: all clean $(VERSIONS)
