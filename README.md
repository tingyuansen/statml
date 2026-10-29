# Statistical Machine Learning for Astronomy

> A consistently Bayesian, first-principles treatment of machine learning for astronomy — deriving each method from the ground up, with uncertainty quantification and statistical rigor at its core. For final-year undergraduates and graduate students, each chapter paired with a hands-on tutorial on real astronomical data.

**📖 Read online:** **[statml.org](https://statml.org/)** (mirror: [tingyuansen.github.io/statml](https://tingyuansen.github.io/statml/))
&nbsp;·&nbsp; **📄 Full text on arXiv:** [arXiv:2506.12230](https://arxiv.org/abs/2506.12230)

The online reader places each textbook chapter next to its companion tutorial(s), so
you can move between theory and practice in one place.

---

## Author

**Yuan-Sen Ting** — The Ohio State University

---

## About

This repository hosts the companion tutorials for the textbook *Statistical Machine
Learning for Astronomy* and the source for its online reader. The book gives a
systematic, consistently Bayesian treatment of machine learning for astronomical
research — deriving each method from first principles and revealing how modern
techniques connect to their classical statistical foundations, with uncertainty
quantification throughout. Each chapter is applied to real astronomical problems:
APOGEE spectra, Gaia photometry, JWST images, Kepler light curves, and more.

- **Foundations** — probability, Bayesian inference, summary statistics
- **Regression** — least squares to fully Bayesian, with input uncertainties
- **Classification** — logistic regression, multi-class, Bayesian extensions
- **Unsupervised learning** — PCA, K-means, Gaussian mixtures
- **Inference at scale** — Monte Carlo sampling and MCMC
- **Modern methods** — Gaussian processes and neural networks

Browse the full, interleaved table of contents on the
[online reader](https://statml.org/).

---

## Repository layout

```
statml/
├── tutorials/          # 22 executed notebooks (tutorial_chapter_*.ipynb)
├── data/               # datasets used by the tutorials (dataset_*)
├── docs/               # the online reader (served at statml.org and on GitHub Pages)
│   ├── index.html      #   landing page / table of contents
│   ├── reader.html     #   chapter + tutorial reader
│   ├── assets/         #   styles, renderer, manifest
│   ├── content/        #   generated chapter & tutorial JSON
│   └── figures/        #   chapter figures (PNG)
└── build_statml.py     # builds docs/ from the LaTeX sources + notebooks
```

## Tutorials

The 22 tutorial notebooks in `tutorials/` are self-contained and executed, so the
rendered site shows their plots. They load the datasets in `data/` via relative
paths, so they run as-is once you have the dependencies:

```bash
pip install numpy scipy matplotlib pandas scikit-learn jupyterlab torch   # torch for Tutorial 8 and Chapter 15
pip install sentence-transformers umap-learn pillow                      # Tutorial 8 only
cd tutorials && jupyter lab
```

Most tutorials need only NumPy and Matplotlib. SciPy is used in Tutorials 12, 13b and 14a,
pandas in 8 and 11a, scikit-learn in 7, 8 and 9, and PyTorch in 8 and 15a to 15d.
The star-galaxy sample of Tutorial 14b holds 600 Gaia DR3 sources with labels from
SDSS DR17, with the classes of Hughes et al. (2022).

---

## Building the site

The reader is a static site under `docs/`. Every push to `main` publishes it twice:
a Vercel project serves `docs/` at statml.org, and GitHub Pages serves the same folder
at tingyuansen.github.io/statml as a mirror. Neither redirects to the other, so each
stays reachable if a network blocks the other. `docs/` is rebuilt by
`build_statml.py`:

- **Chapters** are converted from the LaTeX sources with `pandoc`, with math kept raw
  for KaTeX. Section, figure and table numbers and the cross-references come from a
  draft LaTeX run, so they match the printed book, and each chapter ends with the
  works of the book's bibliography that its Further Reading names. Figures are
  converted from PDF to PNG. The LaTeX sources are kept privately and are not part
  of this repository, so a full chapter rebuild requires them — the rendered output
  in `docs/content/` is committed.
- **Tutorials** are slimmed from the executed notebooks into `docs/content/*.json`.

```bash
python3 build_statml.py            # rebuild chapters, tutorials, and the manifest
python3 build_statml.py --figures  # also re-convert figures (slower)
```

Dependencies: `pandoc`, `pdflatex`, `poppler` (`pdftoppm`), and Python 3 with
`beautifulsoup4`. To preview locally,
serve `docs/` over HTTP:

```bash
cd docs && python3 -m http.server 8000   # then open http://localhost:8000
```

---

## How to cite

If you find these resources useful in your research or teaching, please cite the
textbook and/or the tutorial repository.

```bibtex
@article{ting2025statistical,
  title   = {Statistical Machine Learning for Astronomy},
  author  = {Ting, Yuan-Sen},
  journal = {arXiv preprint arXiv:2506.12230},
  year    = {2025}
}

@software{ting2025statisticaltutorial,
  author    = {Ting, Yuan-Sen},
  title     = {tingyuansen/statml: Statistical Machine Learning for Astronomy — Tutorials (v1.0)},
  year      = {2025},
  publisher = {Zenodo},
  version   = {v1.0},
  doi       = {10.5281/zenodo.16495692},
  url       = {https://doi.org/10.5281/zenodo.16495692}
}
```

---

## License

© 2025 Yuan-Sen Ting. These materials may be redistributed by sharing the original
GitHub repository link for educational purposes. Any other reproduction or adaptation
requires explicit permission from the author.
