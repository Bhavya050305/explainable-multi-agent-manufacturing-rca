"""
ManuMind AI — Isolation Forest SHAP Evaluation & Benchmark Pipeline
Department of AI & Data Science — RMK Engineering College

Executes local explanation generation, global feature importance aggregation,
runtime microbenchmarking on validation data, and final frozen test evaluation.
"""

import json
import logging
import os
import platform
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import sklearn
import shap

from backend.app.ml.shap_explainability.config import (
    ShapExplainerConfig,
    FEATURE_COLUMNS,
    FEATURE_UNITS
)
from backend.app.ml.shap_explainability.explainer import IsolationForestShapExplainer
from backend.app.ml.shap_explainability.visualize import (
    plot_waterfall,
    plot_global_feature_importance,
    plot_beeswarm
)

logger = logging.getLogger("ShapEvaluationPipeline")


class ShapEvaluationPipeline:
    """Master evaluation and benchmarking service for Isolation Forest Kernel SHAP."""

    def __init__(
        self,
        config: Optional[ShapExplainerConfig] = None,
        explainer: Optional[IsolationForestShapExplainer] = None
    ):
        self.config = config or ShapExplainerConfig()
        self.explainer = explainer or IsolationForestShapExplainer(config=self.config)
        self.feature_cols = list(self.config.feature_cols)

    def run_development_benchmark(
        self,
        num_warmup: int = 5,
        num_eval_samples: int = 30
    ) -> Dict[str, Any]:
        """
        Executes a rigorous runtime microbenchmark using validation partition data only.

        Args:
            num_warmup: Warm-up passes to prime Python runtime and CPU cache.
            num_eval_samples: Number of timed repeated observations.

        Returns:
            Dictionary containing hardware environment, latency statistics, and evaluation budget.
        """
        val_df = pd.read_csv(self.config.val_sensor_csv)
        if len(val_df) < num_eval_samples + num_warmup:
            raise ValueError("Insufficient validation samples for benchmarking.")

        features_val = val_df[self.feature_cols].values.astype(np.float64)

        # 1. Warm-up
        logger.info("Executing %d warm-up evaluation passes...", num_warmup)
        for i in range(num_warmup):
            _ = self.explainer.explain_observation(features_val[i], nsamples=self.config.shap_nsamples)

        # 2. Timed benchmarking
        logger.info("Executing %d timed repeated explanation passes...", num_eval_samples)
        latencies_ms: List[float] = []

        for i in range(num_warmup, num_warmup + num_eval_samples):
            t0 = time.perf_counter()
            _ = self.explainer.explain_observation(features_val[i], nsamples=self.config.shap_nsamples)
            t1 = time.perf_counter()
            latencies_ms.append((t1 - t0) * 1000.0)

        latencies_arr = np.array(latencies_ms)

        benchmark_results = {
            "environment": {
                "os": platform.platform(),
                "python_version": sys.version.split()[0],
                "scikit_learn_version": sklearn.__version__,
                "shap_version": shap.__version__,
                "processor": platform.processor() or "AMD64 / x86_64"
            },
            "configuration": {
                "background_samples": len(self.explainer.background_data),
                "shap_nsamples": self.config.shap_nsamples,
                "forward_pass_budget_per_sample": int(len(self.explainer.background_data) * self.config.shap_nsamples),
                "features_evaluated": len(self.feature_cols),
                "warmup_runs": num_warmup,
                "timed_runs": num_eval_samples
            },
            "latency_metrics_ms": {
                "mean": float(np.mean(latencies_arr)),
                "std": float(np.std(latencies_arr)),
                "median": float(np.median(latencies_arr)),
                "p90": float(np.percentile(latencies_arr, 90)),
                "p95": float(np.percentile(latencies_arr, 95)),
                "min": float(np.min(latencies_arr)),
                "max": float(np.max(latencies_arr))
            }
        }

        return benchmark_results

    def evaluate_validation_archetypes(self) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Evaluates the 6 development archetypes (3 normal + 3 anomalous) on the Validation partition.
        Generates corresponding waterfall plots.
        """
        val_df = pd.read_csv(self.config.val_sensor_csv)

        # Target 3 normal and 3 anomalous validation observations
        archetypes = [
            {"label": "Normal 1 (M101 nominal)", "machine_id": "M101", "step": 3000},
            {"label": "Normal 2 (M103 nominal)", "machine_id": "M103", "step": 3100},
            {"label": "Normal 3 (M105 nominal)", "machine_id": "M105", "step": 3200},
            {"label": "Anomalous 1 (M102 overheating)", "machine_id": "M102", "step": 3000},
            {"label": "Anomalous 2 (M104 bearing wear)", "machine_id": "M104", "step": 3100},
            {"label": "Anomalous 3 (M107 pressure drop)", "machine_id": "M107", "step": 3200},
        ]

        explanations: List[Dict[str, Any]] = []
        plot_paths: Dict[str, str] = {}

        for item in archetypes:
            m_id = item["machine_id"]
            st = item["step"]
            m_val = val_df[val_df["machine_id"] == m_id].reset_index(drop=True)
            idx_in_val = st - 2800  # Val steps run 2800..3399
            row = m_val.iloc[idx_in_val]

            x_vec = row[self.feature_cols].values.astype(np.float64)
            exp = self.explainer.explain_observation(
                x_vec,
                machine_id=m_id,
                step=st,
                timestamp=str(row["timestamp"])
            )
            exp["archetype_label"] = item["label"]
            exp["fault_type"] = str(row.get("fault_type", "normal"))
            explanations.append(exp)

            # Generate local waterfall plot
            clean_name = item["label"].split()[0].lower() + "_" + m_id.lower()
            plot_file = os.path.join(self.config.graph_dir, f"waterfall_{clean_name}.png")
            feature_dict = {f: float(row[f]) for f in self.feature_cols}
            plot_waterfall(
                explanation=exp,
                save_path=plot_file,
                feature_values=feature_dict,
                scaled=True,
                title=f"{item['label']} — Machine {m_id} (Step {st})"
            )
            plot_paths[item["label"]] = plot_file

        return explanations, plot_paths

    def evaluate_cohort(
        self,
        df: pd.DataFrame,
        cohort_name: str = "validation_cohort",
        sample_limit: int = 100
    ) -> Dict[str, Any]:
        """
        Evaluates a cohort of observations, calculating global feature importance,
        additivity pass rate, and generating summary plots.
        """
        N = min(len(df), sample_limit)
        subset_df = df.iloc[:N].copy()

        X_matrix = subset_df[self.feature_cols].values.astype(np.float64)
        explanations = self.explainer.explain_batch(X_matrix, metadata_df=subset_df)

        # Global statistics
        additivity_errors = [exp["additivity_error"] for exp in explanations if exp.get("additivity_error") is not None]
        all_additive = all(exp.get("additivity_verified", False) for exp in explanations)
        max_additivity_error = max(additivity_errors) if additivity_errors else 0.0

        # Feature importance matrix
        abs_matrix = np.zeros((len(explanations), len(self.feature_cols)), dtype=np.float64)
        for i, exp in enumerate(explanations):
            for j, f in enumerate(self.feature_cols):
                abs_matrix[i, j] = abs(exp["feature_attributions"][f])

        mean_abs_importance = {
            f: float(np.mean(abs_matrix[:, j])) for j, f in enumerate(self.feature_cols)
        }

        # Render global graphs
        importance_plot_path = os.path.join(self.config.graph_dir, f"{cohort_name}_feature_importance.png")
        plot_global_feature_importance(
            explanations=explanations,
            save_path=importance_plot_path,
            title=f"Global SHAP Feature Importance — {cohort_name.replace('_', ' ').title()} (N={len(explanations)})"
        )

        beeswarm_plot_path = os.path.join(self.config.graph_dir, f"{cohort_name}_beeswarm.png")
        plot_beeswarm(
            explanations=explanations,
            raw_feature_matrix=X_matrix,
            save_path=beeswarm_plot_path,
            title=f"SHAP Summary Beeswarm Distribution — {cohort_name.replace('_', ' ').title()} (N={len(explanations)})"
        )

        cohort_results = {
            "cohort_name": cohort_name,
            "sample_count": len(explanations),
            "all_additive": all_additive,
            "max_additivity_error": float(max_additivity_error),
            "mean_abs_importance": mean_abs_importance,
            "importance_plot_path": importance_plot_path,
            "beeswarm_plot_path": beeswarm_plot_path
        }

        return cohort_results

    def run_final_frozen_test_evaluation(self) -> Dict[str, Any]:
        """
        Executes the approved final frozen evaluation once on the held-out test partition.

        Safeguards:
        - Completely frozen: zero parameter tuning.
        - Background strictly remains the normal training exemplars.
        - Evaluates test anomalies and nominal baseline rows across all machines.
        """
        test_path = self.config.test_sensor_csv
        if not os.path.exists(test_path):
            raise FileNotFoundError(f"Test dataset not found at: {test_path}")

        df_test = pd.read_csv(test_path)
        logger.info("Executing final frozen evaluation on test partition (%d total rows)...", len(df_test))

        # Select a balanced evaluation cohort from the test set:
        # Sample anomalous test rows from degraded machines (M102, M104, M107, M109)
        # and nominal test rows from healthy machines (M101, M103, M105, etc.)
        test_anomalies = df_test[df_test["is_anomaly"] == 1]
        test_normal = df_test[df_test["is_anomaly"] == 0]

        # Stratified test sample: 10 anomalies per faulted machine (40) + 5 normal per machine (50) = 90
        sampled_rows = []
        for m_id in ["M102", "M104", "M107", "M109"]:
            m_anom = test_anomalies[test_anomalies["machine_id"] == m_id]
            if len(m_anom) > 0:
                sampled_rows.append(m_anom.iloc[np.linspace(10, len(m_anom) - 10, min(10, len(m_anom)), dtype=int)])

        for m_id in self.config.stratified_machines:
            m_norm = test_normal[test_normal["machine_id"] == m_id]
            if len(m_norm) > 0:
                sampled_rows.append(m_norm.iloc[np.linspace(10, len(m_norm) - 10, min(5, len(m_norm)), dtype=int)])

        eval_test_df = pd.concat(sampled_rows, axis=0, ignore_index=True)

        logger.info("Evaluating frozen test cohort of %d samples...", len(eval_test_df))
        test_cohort_results = self.evaluate_cohort(
            df=eval_test_df,
            cohort_name="frozen_test_cohort",
            sample_limit=len(eval_test_df)
        )

        return test_cohort_results

    def execute_full_evaluation_pipeline(self) -> Dict[str, Any]:
        """
        Executes the complete evaluation workflow:
        1. Validation benchmark.
        2. Validation archetypes & waterfall plots.
        3. Validation cohort aggregation.
        4. Final frozen test evaluation.
        5. Saves unified results to reports/phase2/shap_explainability/shap_evaluation_results.json.
        """
        logger.info("Starting Phase 2 Step 6 Full Evaluation Pipeline...")

        # 1. Benchmark on validation data
        benchmark = self.run_development_benchmark(num_warmup=5, num_eval_samples=25)

        # 2. Validation archetypes
        archetypes, archetype_plots = self.evaluate_validation_archetypes()

        # 3. Validation cohort
        val_df = pd.read_csv(self.config.val_sensor_csv)
        val_cohort = self.evaluate_cohort(val_df, cohort_name="validation_cohort", sample_limit=80)

        # 4. Final frozen test evaluation
        frozen_test = self.run_final_frozen_test_evaluation()

        unified_results = {
            "pipeline_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "benchmark": benchmark,
            "validation_archetypes": archetypes,
            "archetype_plots": archetype_plots,
            "validation_cohort": val_cohort,
            "frozen_test_evaluation": frozen_test
        }

        os.makedirs(os.path.dirname(os.path.abspath(self.config.results_json_path)), exist_ok=True)
        with open(self.config.results_json_path, "w", encoding="utf-8") as f:
            json.dump(unified_results, f, indent=2)

        logger.info("Saved unified evaluation results to %s", self.config.results_json_path)
        return unified_results
