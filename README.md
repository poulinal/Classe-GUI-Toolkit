# Classe-GUI-Toolkit
GUI Application Toolkit for CLASSE





## To Run (source code):

``` ssh -Y ____@lnx201.classe.cornell.edu```

```qrsh -q interactive.q -l mem_free=350G -pe sge_pe 20```

<!-- ```source /nfs/chess/sw/anaconda3_sgomezalvarado/bin/activate && conda activate alexenv``` -->
```source /nfs/chess/sw/anaconda3_sgomezalvarado/bin/activate```
```conda create myenv```
```conda activate myenv```

If `nxs_analysis_tools` is only available after activating the CHESS/CLASSE environment, do that before installing or building the app.

`cd` to `~/Classe-GUI-Toolkit/`

```pip install -e .```

`cd` to `~/Classe-GUI-Toolkit/CGTProject`

finally to run:

```python main.py```


## To Run (distribution):
Download the latest release in the github repo:
`cd` to the unzipped release
run `./CGTProject`





# More Info Below:

## Quick Start (No Manual main.py Launch)

From the project root, install once and get a command-line launcher:

```bash
python -m pip install -e .
```

Then run the app from anywhere with:

```bash
cgtproject
```

## Standalone Distribution (No Python Env Required For End User)

Build a self-contained executable from the same Python environment that provides `nxs_analysis_tools`:

```bash
./scripts/build_distribution.sh
```

The executable is produced at:

```bash
dist/CGTProjectApp/CGTProject
```

Run from terminal:

```bash
./dist/CGTProjectApp/CGTProject
```

Install a desktop launcher (Linux):

```bash
./scripts/install_desktop_launcher.sh
```

After that, the app can be opened from the system application menu.

## GitHub Releases

This repository now includes a GitHub Actions workflow at:

```bash
.github/workflows/release.yml
```

It runs when you push a tag like `v0.1.0` and publishes a release asset named:

```bash
dist/CGTProject-linux-x86_64.zip
```

Typical release flow:

```bash
git tag v0.1.0
git push origin v0.1.0
```

That tag push will build the Linux executable on GitHub Actions and attach the zip file to the GitHub Release.

The release workflow runs on a GitHub-hosted runner using a Linux container image and installs `nxs-analysis-tools` from PyPI (with a fallback install from `https://github.com/stevenjgomez/nxs_analysis_tools`).

The project metadata already includes `dask` as a runtime dependency.

If you already published a bad release, create a new tag after updating the workflow, for example:

```bash
git tag v0.0.2
git push origin v0.0.2
```

Then download the new `CGTProject-linux-x86_64.zip` asset from that release.