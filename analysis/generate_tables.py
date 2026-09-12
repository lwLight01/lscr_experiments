import glob
import json
import os

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

RESULTS_DIR  = os.path.join(os.path.dirname(__file__), '..', 'results')
FIGURES_DIR  = os.path.join(os.path.dirname(__file__), '..', 'results')

COLOR_BASELINE = "#e74c3c"
COLOR_LSCR     = "#2ecc71"

def load_data() -> pd.DataFrame:

    summaries = []
    for f in glob.glob(os.path.join(RESULTS_DIR, '*_summary.json')):
        with open(f) as fp:
            summaries.append(json.load(fp))
    if not summaries:
        raise FileNotFoundError(
            f"No summary files in {RESULTS_DIR}. Run the experiment first."
        )
    return pd.DataFrame(summaries)

def plot_session_survival(df: pd.DataFrame):

    scenarios = ['S2', 'S3', 'S4', 'S5', 'S6', 'S11']
    bl_rates, lscr_rates = [], []
    bl_errs,  lscr_errs  = [], []

    for s in scenarios:
        bl   = df[(df['scenario'] == s) & (df['mode'] == 'baseline')]
        lc   = df[(df['scenario'] == s) & (df['mode'] == 'lscr')]

        bl_r   = (bl['total_received_ok'] / bl['total_sent']) * 100
        lscr_r = (lc['total_received_ok'] / lc['total_sent']) * 100

        bl_rates.append(bl_r.mean())
        lscr_rates.append(lscr_r.mean())
        bl_errs.append(bl_r.sem() * 1.96)
        lscr_errs.append(lscr_r.sem() * 1.96)

    x     = np.arange(len(scenarios))
    width = 0.35

    fig, ax = plt.subplots(figsize=(11, 6))
    bars1 = ax.bar(x - width / 2, bl_rates,   width,
                   yerr=bl_errs,   capsize=4,
                   label='Baseline', color=COLOR_BASELINE, alpha=0.85)
    bars2 = ax.bar(x + width / 2, lscr_rates, width,
                   yerr=lscr_errs, capsize=4,
                   label='LSCR',     color=COLOR_LSCR,     alpha=0.85)

    ax.set_ylabel('Session Survival Rate (%)', fontsize=12)
    ax.set_xlabel('Network Scenario', fontsize=12)
    ax.set_title('Figure 4 — Session Survival: Baseline vs. LSCR\n'
                 '(error bars = 95% CI, 10 trials each)', fontsize=13)
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, fontsize=11)
    ax.set_ylim(0, 110)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.0f%%'))
    ax.legend(fontsize=11)
    ax.grid(axis='y', linestyle='--', alpha=0.4)

    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, 'fig4_session_survival.png')
    plt.savefig(out, dpi=300)
    plt.close()
    print(f"[figures] Saved → {out}")

def plot_recovery_latency(df: pd.DataFrame):

    scenarios = ['S2', 'S3', 'S4', 'S6', 'S11']
    lscr_data = df[df['mode'] == 'lscr']

    data = []
    for s in scenarios:
        vals = lscr_data[lscr_data['scenario'] == s]['avg_recovery_latency_ms'].values
        data.append(vals if len(vals) > 0 else [0])

    fig, ax = plt.subplots(figsize=(10, 6))
    bp = ax.boxplot(data, tick_labels=scenarios, patch_artist=True,
                    medianprops=dict(color='black', linewidth=2))
    for patch in bp['boxes']:
        patch.set_facecolor(COLOR_LSCR)
        patch.set_alpha(0.7)

    ax.set_ylabel('Recovery Latency (ms)', fontsize=12)
    ax.set_xlabel('Network Scenario', fontsize=12)
    ax.set_title('Figure 5 — LSCR Recovery Latency by Scenario', fontsize=13)
    ax.grid(axis='y', linestyle='--', alpha=0.4)

    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, 'fig5_recovery_latency.png')
    plt.savefig(out, dpi=300)
    plt.close()
    print(f"[figures] Saved → {out}")

def plot_detection_rate(df: pd.DataFrame):

    scenarios = [f"S{i}" for i in range(1, 13)]
    lscr_data = df[df['mode'] == 'lscr']

    rates = []
    for s in scenarios:
        subset = lscr_data[lscr_data['scenario'] == s]
        if len(subset) > 0 and subset['divergence_actual'].sum() > 0:
            rate = subset['detection_rate'].mean() * 100
        else:
            rate = 100.0
        rates.append(rate)

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(scenarios, rates, marker='o', linewidth=2,
            color=COLOR_LSCR, label='LSCR Detection Rate')
    ax.axhline(y=100, color='gray', linestyle='--', alpha=0.6, label='100% target')
    ax.fill_between(range(len(scenarios)), rates, alpha=0.15, color=COLOR_LSCR)

    ax.set_ylabel('Detection Rate (%)', fontsize=12)
    ax.set_xlabel('Scenario', fontsize=12)
    ax.set_title('Figure 6 — LSCR State Divergence Detection Rate', fontsize=13)
    ax.set_ylim(0, 110)
    ax.set_xticks(range(len(scenarios)))
    ax.set_xticklabels(scenarios)
    ax.legend(fontsize=11)
    ax.grid(linestyle='--', alpha=0.4)

    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, 'fig6_detection_rate.png')
    plt.savefig(out, dpi=300)
    plt.close()
    print(f"[figures] Saved → {out}")

if __name__ == "__main__":
    os.makedirs(FIGURES_DIR, exist_ok=True)
    df = load_data()
    print(f"[figures] Loaded {len(df)} summaries")

    plot_session_survival(df)
    plot_recovery_latency(df)
    plot_detection_rate(df)

    print("\n[figures] All figures generated in results/")
    print("fig4_session_survival.png")
    print("fig5_recovery_latency.png")
    print("fig6_detection_rate.png")
