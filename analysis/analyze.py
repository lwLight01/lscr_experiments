import glob
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

RESULTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'results')
SCENARIOS   = [f"S{i}" for i in range(1, 13)]
MODES       = ["baseline", "lscr"]

def load_all_summaries() -> pd.DataFrame:

    summaries = []
    pattern   = os.path.join(RESULTS_DIR, '*_summary.json')
    files     = glob.glob(pattern)

    if not files:
        print(f"[ERROR] No summary files found in {RESULTS_DIR}")
        print("        Run the experiment first with: sudo ./scripts/run_all.sh")
        sys.exit(1)

    for f in files:
        with open(f) as fp:
            summaries.append(json.load(fp))

    df = pd.DataFrame(summaries)
    print(f"[analyze] Loaded {len(df)} experiment summaries from {RESULTS_DIR}")
    return df

def ci95(values) -> tuple:

    n    = len(values)
    mean = np.mean(values)
    if n < 2:
        return mean, 0.0
    se = stats.sem(values)
    margin = se * stats.t.ppf(0.975, df=n - 1)
    return mean, margin

def compute_table_4(df: pd.DataFrame):

    print("\n" + "=" * 65)
    print(" TABLE 4: State Divergence Events (per 1000 messages × 10 trials)")
    print("=" * 65)
    print(f"{'Scenario':<10} {'Mode':<10} {'Mean Divergences':>18} {'±95% CI':>10} {'Detection %':>12}")
    print("-" * 65)

    for scenario in SCENARIOS:
        for mode in MODES:
            subset = df[(df['scenario'] == scenario) & (df['mode'] == mode)]
            if len(subset) == 0:
                continue
            mean_div, ci = ci95(subset['divergence_detected'].values)
            det_rate     = subset['detection_rate'].mean() * 100
            print(f"  {scenario:<8} {mode:<10} {mean_div:>18.1f} {ci:>10.2f} {det_rate:>11.1f}%")

    print("-" * 65)

def compute_table_5(df: pd.DataFrame):

    print("\n" + "=" * 65)
    print(" TABLE 5: Recovery Performance (LSCR mode only)")
    print("=" * 65)
    print(f"{'Scenario':<10} {'Attempts':>10} {'Success Rate':>14} {'Avg Latency ms':>16}")
    print("-" * 65)

    lscr_df = df[df['mode'] == 'lscr']
    for scenario in SCENARIOS:
        subset = lscr_df[lscr_df['scenario'] == scenario]
        if len(subset) == 0 or subset['recovery_attempts'].sum() == 0:
            continue
        total_attempts   = subset['recovery_attempts'].sum()
        success_rate     = subset['recovery_success_rate'].mean() * 100
        avg_lat          = subset['avg_recovery_latency_ms'].mean()
        print(f"  {scenario:<8} {total_attempts:>10} {success_rate:>13.1f}% {avg_lat:>15.2f}")

    print("-" * 65)

def compute_table_6(df: pd.DataFrame):

    print("\n" + "=" * 65)
    print(" TABLE 6: Security Metrics (all zeros = PASS)")
    print("=" * 65)
    print(f"{'Mode':<12} {'Nonce Reuse':>12} {'Replay Accept':>15} "
          f"{'Invalid Accept':>16} {'Unsafe Rec.':>12}")
    print("-" * 65)

    for mode in MODES:
        subset = df[df['mode'] == mode]
        nonce_reuse  = subset['nonce_reuse_count'].sum()
        replay_acc   = subset['replay_accepted'].sum()
        invalid_acc  = subset['invalid_accepted'].sum()
        unsafe_rec   = subset['unsafe_recoveries'].sum() if mode == 'lscr' else '-'
        print(f"  {mode:<10} {nonce_reuse:>12} {replay_acc:>15} "
              f"{invalid_acc:>16} {str(unsafe_rec):>12}")

    print("-" * 65)
    nonce_total  = df['nonce_reuse_count'].sum()
    replay_total = df['replay_accepted'].sum()
    if nonce_total == 0 and replay_total == 0:
        print("  ✓ SECURITY PASS: No nonce reuse or replay acceptance detected")
    else:
        print(f"  ✗ SECURITY FAIL: nonce_reuse={nonce_total}, replay_accepted={replay_total}")

def compute_table_9(df: pd.DataFrame):

    print("\n" + "=" * 65)
    print(" TABLE 9: Baseline vs LSCR — Session Survival Rate")
    print("=" * 65)
    print(f"{'Scenario':<10} {'Baseline':>12} {'LSCR':>12} {'Improvement':>14}")
    print("-" * 65)

    for scenario in SCENARIOS:
        baseline = df[(df['scenario'] == scenario) & (df['mode'] == 'baseline')]
        lscr     = df[(df['scenario'] == scenario) & (df['mode'] == 'lscr')]

        if len(baseline) == 0 or len(lscr) == 0:
            continue

        bl_rate   = (baseline['total_received_ok'].mean() /
                     baseline['total_sent'].mean()) * 100
        lscr_rate = (lscr['total_received_ok'].mean() /
                     lscr['total_sent'].mean()) * 100
        delta     = lscr_rate - bl_rate

        print(f"  {scenario:<8} {bl_rate:>11.1f}% {lscr_rate:>11.1f}% "
              f"  {'+' if delta >= 0 else ''}{delta:.1f}%")

    print("-" * 65)

if __name__ == "__main__":
    df = load_all_summaries()

    compute_table_4(df)
    compute_table_5(df)
    compute_table_6(df)
    compute_table_9(df)

    print("\n[analyze] Done — copy the tables above into your paper.")
