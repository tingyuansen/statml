# Statistical Machine Learning for Astronomy

> A graduate-level course that builds machine learning from Bayesian first principles, with uncertainty quantification at its core — each chapter paired with hands-on tutorials on real astronomical data.

**📖 Read online:** **[tingyuansen.github.io/statml](https://tingyuansen.github.io/statml/)**
&nbsp;·&nbsp; **📄 Full text on arXiv:** [arXiv:2506.12230](https://arxiv.org/abs/2506.12230)

The online reader renders every textbook chapter alongside its companion tutorial(s),
with all code and figures preserved inline so you can move between theory and practice
in one place.

---

## Author

**Yuan-Sen Ting** — The Ohio State University

---

## About

This repository hosts the companion tutorials for the textbook *Statistical Machine
Learning for Astronomy* and the source for its online reader. The book develops
machine learning through the lens of Bayesian inference, emphasizing principled
uncertainty quantification, and applies each idea to real astronomical problems:
APOGEE spectra, Gaia photometry, JWST images, Kepler light curves, and more.

- **Foundations** — probability, Bayesian inference, summary statistics
- **Regression** — least squares to fully Bayesian, with input uncertainties
- **Classification** — logistic regression, multi-class, Bayesian extensions
- **Unsupervised learning** — PCA, K-means, Gaussian mixtures
- **Inference at scale** — Monte Carlo sampling and MCMC
- **Modern methods** — Gaussian processes and neural networks

Browse the full, interleaved table of contents on the
[online reader](https://tingyuansen.github.io/statml/).

---

## Tutorials

The 21 tutorial notebooks (`tutorial_chapter_*.ipynb`) are self-contained and
executed, so the rendered site shows every plot. Their datasets
(`dataset_*.npz`, `.npy`, `.csv`, `.pkl.zip`) live in the repository root, so the
notebooks can also be run locally:

```bash
pip install numpy scipy matplotlib jupyterlab torch   # torch only for Chapter 15
jupyter lab
```

---

## Building the site

The reader is a static site under `docs/`, rebuilt by `build_statml.py`:

- **Chapters** are converted from the LaTeX sources with `pandoc` (math kept raw for
  KaTeX, citations resolved via `citeproc`); figures are converted from PDF to PNG.
  The LaTeX sources are kept privately and are not part of this repository, so a full
  chapter rebuild requires them — the rendered output in `docs/content/` is committed.
- **Tutorials** are slimmed from the executed notebooks into `docs/content/*.json`.

```bash
python3 build_statml.py            # rebuild chapters, tutorials, and the manifest
python3 build_statml.py --figures  # also re-convert figures (slower)
```

Dependencies: `pandoc`, `poppler` (`pdftoppm`), and Python 3. To preview locally,
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
