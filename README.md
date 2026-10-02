# GRAZING

Installation instructions for GRAZING_9 and Python tools for processing its output.

GRAZING_9 is an interactive Fortran program for estimating heavy-ion reactions at moderate bombarding energies. It calculates mass and charge distributions, kinetic and excitation energies, angular distributions and capture cross sections.

Ref: [Official GRAZING_9 page](https://www.to.infn.it/~nanni/grazing/)

## Contents

- `install-grazing.sh`: downloads GRAZING_9 from the official INFN page
- `grazing_builder.py`: builds residue tables and reconstructs recoil properties
- `grazing_plotter.py`: plots residue maps, isotope yields and recoil distributions
- `xe_pt_195Os.yaml`: example configuration for the `136Xe + 198Pt` reaction

The GRAZING executable and its data files are not stored in this repository.

## Install GRAZING_9

Clone this repository and run the installer:

```bash
git clone https://github.com/sid70630/Grazing.git
cd Grazing
bash install-grazing.sh
```

The installer downloads the official 64-bit executable and data files into `~/grazing`. It also adds `GRAZING_DIR` and the executable directory to `~/.bashrc`.

Open a new terminal and test:

```bash
echo "$GRAZING_DIR"
which grazing_9_64bit
grazing_9_64bit
```

## Manual installation

```bash
mkdir -p ~/grazing
cd ~/grazing

wget https://www.to.infn.it/~nanni/grazing/grazing_env.tar.gz
tar -xzf grazing_env.tar.gz
chmod +x grazing_9 grazing_9_64bit
```

Add the environment:

```bash
cat >> ~/.bashrc <<'EOF'

# GRAZING
export GRAZING_DIR="$HOME/grazing/data"
export PATH="$HOME/grazing:$PATH"
EOF

source ~/.bashrc
```

Test:

```bash
file ~/grazing/grazing_9_64bit
grazing_9_64bit
```

## Install the Python tools

Create a separate environment:

```bash
cd ~/Grazing
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Check the commands:

```bash
python grazing_builder.py --help
python grazing_plotter.py --help
```

## Configuration

Copy the example before changing it:

```bash
cp xe_pt_195Os.yaml my_case.yaml
```

Edit the reaction, isotope of interest, GRAZING folders and plotting ranges in `my_case.yaml`.

The example uses:

```yaml
base_dir: "~/grazing"
```

The `case_folder` must contain the case-specific `fort.*` files produced by the main GRAZING calculation.

## Build the tables

```bash
source ~/Grazing/.venv/bin/activate
cd ~/Grazing

python grazing_builder.py run-case --config my_case.yaml
```

Depending on the YAML settings, the builder:

1. runs the target-like-fragment evaporation calculation;
2. collects the generated residue files;
3. writes the post-evaporation yield tables;
4. reads the mapped `fort.*` files;
5. builds and filters the recoil kernel;
6. reconstructs recoil angles and energies.

## Make the plots

```bash
python grazing_plotter.py run-case --config my_case.yaml
```

The plotter produces:

- a post-evaporation map in the proton-neutron plane;
- an isotope-chain cross-section plot;
- recoil angle, energy and angle-energy distributions.

Run `deactivate` when finished.

## Note

GRAZING_9 was written by Aage Winther. The executable and supporting data are downloaded directly from the [official distribution page](https://www.to.infn.it/~nanni/grazing/) and remain subject to the terms of their authors and distributors.

This repository contains separate installation instructions and Python analysis tools. It does not claim ownership of GRAZING_9 or redistribute its executable or data files.
