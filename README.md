# LSCR Experiment

This repository contains the experimental setup, simulation scripts, and analysis code for evaluating the Lightweight Secure Communication Protocol (LSCR) against a baseline protocol.

## Prerequisites

To run these experiments, you will need a Linux environment (or a virtual machine/WSL) with the following installed:
- **Python 3**
- **sudo privileges** (required for `tcpdump` and `tc qdisc` network emulation)
- **tcpdump** (for packet capture)
- **iproute2** (for `tc` traffic control)

---

## 1. Setup Procedure

Follow these steps to set up the experimental environment:

### A. Clone the Repository
```bash
git clone https://github.com/lwLight01/lscr_experiments.git ~/lscr-experiment
cd ~/lscr-experiment
```
*(Note: Ensure the folder is named `lscr-experiment` and is located in your `$HOME` directory, as some scripts expect this path: `$HOME/lscr-experiment`)*

### B. Generate a Shared Key
The cryptographic engine requires a 32-byte shared key to operate. Generate it in the root of the project:
```bash
python3 -c "import os; open('shared_key.bin', 'wb').write(os.urandom(32))"
```

### C. Set up the Python Virtual Environment
The scripts expect a virtual environment named `venv` in the project root:
```bash
python3 -m venv venv
source venv/bin/activate
```

### D. Install Python Dependencies
Install the required packages for running the clients/servers and analyzing the data:
```bash
pip install numpy pandas scipy matplotlib psutil cryptography
```

---

## 2. Running the Experiments

Before running the experiments, ensure the shell scripts have executable permissions and Linux-style line endings (especially if the repository was modified on Windows). Run this in the project root:
```bash
chmod +x scripts/*.sh
dos2unix scripts/*.sh 2>/dev/null || true
```

The experiment consists of 12 scenarios (`S1` to `S12`), comparing two modes (`baseline` and `lscr`).

### Option A: Run the Full Suite (Recommended for full results)
To run all scenarios, modes, and trials automatically:
```bash
sudo ./scripts/run_all.sh
```
> **Note:** The full suite takes approximately 2–4 hours to complete. Results are saved in the `results/` folder, PCAPs in `pcaps/`, and logs in `logs/`.

### Option B: Run a Single Scenario
If you want to test a specific scenario (e.g., Scenario 1, LSCR mode, Trial 1):
```bash
sudo ./scripts/run_scenario.sh S1 lscr 1
```

---

## 3. Analyzing the Results

Once the experiments have finished, you can generate the analytical tables and plots for your paper.

### Generate Data Tables
Move into the analysis directory and run the analysis script. This will output Tables 4, 5, 6, and 9 directly to your console:
```bash
cd analysis
python3 analyze.py
```

### Generate Plots (Figures)
To generate the visualizations (Figures 4, 5, and 6), run:
```bash
python3 generate_tables.py
```
The figures will be saved as PNG images (`fig4_session_survival.png`, `fig5_recovery_latency.png`, `fig6_detection_rate.png`) in the `results/` directory.
