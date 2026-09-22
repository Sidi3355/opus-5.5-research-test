# Build every venue version. Style files are resolved through TEXINPUTS/BSTINPUTS.
VENUES = iclr icml neurips arxiv
STY_iclr = styles/iclr2027
STY_icml = styles/icml2026
STY_neurips = styles/neurips2026
STY_arxiv = styles/neurips2026

all: $(VENUES)

$(VENUES):
	cd $@ && TEXINPUTS=.:../$(STY_$@)//: BSTINPUTS=.:../$(STY_$@)//: BIBINPUTS=..: latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
	cp $@/main.pdf ../paper_$@.pdf 2>/dev/null || true

clean:
	for v in $(VENUES); do (cd $$v && latexmk -C main.tex); done

.PHONY: all clean $(VENUES)
