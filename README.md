# Statistical Machine Learning for Astronomy

Companion tutorials and online reader for the textbook by **Yuan-Sen Ting** (The Ohio State University):
a consistently Bayesian, first-principles treatment of machine learning for astronomy, for final-year
undergraduates and graduate students.

**📖 Read online: [statml.org](https://statml.org/)** &nbsp;·&nbsp; 📄 Full text: [arXiv:2506.12230](https://arxiv.org/abs/2506.12230)

The reader sets the 16 chapters beside their 22 hands-on tutorials on real astronomical data: APOGEE
spectra, Gaia photometry, JWST images, Kepler light curves and more.

## Running the tutorials

The notebooks in `tutorials/` are executed and load the datasets in `data/` by relative path:

```bash
pip install numpy scipy matplotlib pandas scikit-learn torch jupyterlab
cd tutorials && jupyter lab
```

Most tutorials need only NumPy and Matplotlib. PyTorch is used in Tutorials 8 and 15a to 15d, and
Tutorial 8 also needs `pip install sentence-transformers umap-learn pillow`. The star-galaxy sample of
Tutorial 14b holds 600 Gaia DR3 sources with labels from SDSS DR17, with the classes of Hughes et al. (2022).

## Repository

`tutorials/` notebooks · `data/` datasets · `docs/` the reader, published on every push to `main` at
statml.org and mirrored at [tingyuansen.github.io/statml](https://tingyuansen.github.io/statml/) ·
`build_statml.py` rebuilds `docs/` from the notebooks and the book's LaTeX sources (kept privately).

## How to cite

```bibtex
@article{ting2025statistical,
  title   = {Statistical Machine Learning for Astronomy},
  author  = {Ting, Yuan-Sen},
  journal = {arXiv preprint arXiv:2506.12230},
  year    = {2025}
}

@software{ting2026statisticaltutorial,
  author    = {Ting, Yuan-Sen},
  title     = {tingyuansen/statml: Statistical Machine Learning for Astronomy — Tutorials (v1.0)},
  year      = {2026},
  publisher = {Zenodo},
  version   = {v1.0},
  doi       = {10.5281/zenodo.23802476},
  url       = {https://doi.org/10.5281/zenodo.23802476}
}
```

## License

© 2025 Yuan-Sen Ting. These materials may be redistributed by sharing the original GitHub repository link
for educational purposes. Any other reproduction or adaptation requires explicit permission from the author.
