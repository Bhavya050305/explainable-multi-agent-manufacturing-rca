# ManuMind AI — Phase 2 Step 5: Failure-Risk Prediction Feasibility & Target Reassessment Report

**Project Title:** ManuMind AI: Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Institution:** RMK Engineering College — Department of Artificial Intelligence and Data Science  
**Component:** Phase 2 Step 5 — Comparative Failure-Risk Prediction Feasibility & System Architecture Design  
**Date:** November 2026  
**Status:** **APPROVED & FORMALLY CLOSED AS FEASIBILITY ASSESSMENT**  

---

## 1. Executive Summary

This report delivers the comprehensive engineering feasibility audit and formal architectural reassessment for **Phase 2 Step 5: Failure-Risk Prediction** in the ManuMind AI platform.

The original Step 5 specification proposed training comparative supervised regressors (Random Forest and XGBoost) to forecast a continuous future failure risk $R_{\text{target}}(t) = \text{failure\_risk}(t + H)$ at a 24-hour horizon ($H = 288$ timesteps at 5-minute telemetry intervals).

Following rigorous mathematical evaluation, chronological partition boundary purging, and in-memory statistical verification against [`sensor_readings.csv`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/data/raw/sensor_readings.csv) (40,000 readings across 10 machines), this audit issues an unequivocal technical NO-GO recommendation against training supervised Random Forest and XGBoost regressors on continuous failure risk under the existing chronological experimental partition. Formal project-level acceptance of this recommendation has been granted.

Instead, Phase 2 Step 5 is formally closed as an **Independent Feasibility Assessment & Health-Monitoring Architecture Design**. The supervisory system preserves and reuses the verified Phase 2 anomaly detection engines (Model 1 Isolation Forest and Model 2 LSTM Autoencoder) as the empirical telemetry foundation for Phase 3 multi-agent health tracking.

---

## 2. Correction of Tree-Regression Mathematical Claims

The mathematical behavior of Random Forest and XGBoost regressors under extreme distribution shift must be rigorously distinguished based on their distinct algorithmic formulations.

### 2.1 Random Forest Regressor: Strict Convex Hull Ceiling
In scikit-learn's `RandomForestRegressor`, each individual decision tree partitions the $d$-dimensional input feature space into $K$ disjoint hyper-rectangles (leaf nodes) $R_k$. The prediction for an arbitrary input vector $x$ is the sample mean of the training target values belonging to the leaf containing $x$:
$$\hat{y}_{\text{tree}}(x) = \frac{1}{|S_k|} \sum_{i \in S_k} y_i, \quad \text{for } x \in R_k, \quad S_k = \{i : x_i \in R_k\}$$
Because the ensemble prediction is the arithmetic average of $B$ independent trees:
$$\hat{y}_{\text{RF}}(x) = \frac{1}{B} \sum_{b=1}^B \hat{y}^{(b)}(x)$$
The predicted output $\hat{y}_{\text{RF}}(x)$ is a convex combination of training targets. Consequently, the prediction is strictly bounded by the extreme values observed in the training partition:
$$\min_{i \in \text{Train}} y_i \le \hat{y}_{\text{RF}}(x) \le \max_{i \in \text{Train}} y_i \quad \forall x \in \mathbb{R}^d$$
Under the project's chronological split (Train: steps 0–2799), the maximum ground-truth training target risk across all machines is strictly **$0.2090$**. Standard Random Forest predictions are mathematically bounded within $[0.0000, 0.2090]$ and cannot output values in the range $(0.2090, 0.9000]$ present during the test partition.

### 2.2 XGBoost Regressor: Additive Boosting and Residual Accumulation
In contrast to Random Forests, XGBoost constructs an additive ensemble of trees:
$$\hat{y}_{\text{XGB}}^{(T)}(x) = \hat{y}_0 + \sum_{t=1}^T \eta f_t(x)$$
where $\eta$ is the shrinkage learning rate, $\hat{y}_0$ is the base margin, and each tree $f_t(x)$ fits the negative gradient (residuals) of the loss function. The optimal leaf weight $w_j^*$ at node $j$ is computed as:
$$w_j^* = -\frac{\sum_{i \in I_j} g_i}{\sum_{i \in I_j} h_i + \lambda}$$
Because leaf weights accumulate across boosting rounds and optimize residual gradients, **XGBoost predictions are not mathematically constrained to lie within the raw training target interval $[\min(y_{\text{train}}), \max(y_{\text{train}})]$**. Under specific loss objectives, base margins, or tree structures, an additive boosted model can theoretically output predictions outside the training target range.

### 2.3 Retained Practical Conclusion on Tree-Based Models
While XGBoost is not strictly bounded by the raw training maximum, both tree-based models are **not recommended under the current experimental design**:
1. Decision trees partition space using axis-aligned orthogonal splits. When test inputs exhibit severe progressive degradation (e.g., vibration $> 5\text{ g}$, temperature $> 70^\circ\text{C}$), tree partitioners route these samples to the extreme boundary leaves established during training rather than extrapolating a continuous slope.
2. The training partition contains zero representative degradation data for $H = 288$ ($0.0\%$ fault inputs), and less than $6.8\%$ for shorter horizons.
3. The test-to-training maximum target ratio of **4.31×** ($\max R_{\text{train}} = 0.2090$ vs $\max R_{\text{test}} = 0.9000$) causes severe under-prediction and high variance during severe machine breakdown.

---

## 3. Dataset Autocorrelation & Noise Verification

An independent in-memory inspection of [`data/raw/sensor_readings.csv`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/data/raw/sensor_readings.csv) was performed across the verified healthy baseline period (steps 0 to 2599) for all 6 healthy machines (M101, M103, M105, M106, M108, M110).

### 3.1 Empirical Autocorrelation of Baseline Telemetry
We computed the lag-1 empirical autocorrelation $\rho = \text{Corr}(x_t, x_{t-1})$:

| Sensor Channel | Mean Lag-1 Autocorrelation ($\rho$) | Range Across Healthy Fleet | Underlying Generation Dynamics |
| :--- | :---: | :---: | :--- |
| **Vibration** | $+0.0182$ | $[-0.0069, +0.0466]$ | Consistent with i.i.d. Gaussian noise ($\sigma \approx 0.22\text{ g}$) |
| **Pressure** | $+0.0025$ | $[-0.0198, +0.0113]$ | Consistent with i.i.d. Gaussian noise ($\sigma \approx 0.12\text{ bar}$) |
| **Current** | $+0.0081$ | $[-0.0029, +0.0259]$ | Consistent with i.i.d. Gaussian noise ($\sigma \approx 0.70\text{ A}$) |
| **RPM** | $+0.0034$ | $[-0.0188, +0.0428]$ | Consistent with i.i.d. Gaussian noise ($\sigma \approx 7.46\text{ RPM}$) |
| **Temperature** | **$+0.7069$** | $[+0.6872, +0.7303]$ | Exhibits significant thermal inertia / persistence ($\sigma \approx 2.21^\circ\text{C}$) |

### 3.2 Clarification on Robustness Experiment E4
- The parameter $\rho = 0.65$ originated exclusively in the **proposed robustness experiment E4 (Autoregressive Noise Perturbation)** documented in [`reports/phase2/dataset_realism_experiment_plan.json`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/dataset_realism_experiment_plan.json).
- **Status of E4:** E4 is a proposed, unexecuted robustness experiment. It has not been executed against the models, and its synthetic noise formulation is not present in the raw baseline sensor readings (with the exception of natural thermal persistence observed in temperature).

---

## 4. Complete Five-Horizon Comparative Analysis

We evaluated candidate forecasting horizons across five operational intervals:
- $H = 12$ steps ($1.0\text{ hour}$)
- $H = 36$ steps ($3.0\text{ hours}$)
- $H = 72$ steps ($6.0\text{ hours}$)
- $H = 144$ steps ($12.0\text{ hours}$)
- $H = 288$ steps ($24.0\text{ hours}$)

### 4.1 Comparative Horizon Evaluation Table

| Horizon $H$ | Equivalent Lead Time | Usable Train Samples | Usable Val Samples | Usable Test Samples | Degradation Steps in Train Input | % Degradation in Train Input (Denominator) | Train Target Range $[\min, \max]$ | Val Target Range $[\min, \max]$ | Test Target Range $[\min, \max]$ | Test-to-Training Max Target Ratio $\frac{\max(R_{\text{test}})}{\max(R_{\text{train}})}$ |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **$H = 12$** | $1.0\text{ h}$ | 27,880 (2,788/m) | 5,880 (588/m) | 5,880 (588/m) | 188 steps | **6.74%** ($188 / 2,788$) | $[0.0000, 0.2090]$ | $[0.0200, 0.5120]$ | $[0.0200, 0.9000]$ | **4.31×** |
| **$H = 36$** | $3.0\text{ h}$ | 27,640 (2,764/m) | 5,640 (564/m) | 5,640 (564/m) | 164 steps | **5.93%** ($164 / 2,764$) | $[0.0000, 0.2090]$ | $[0.0200, 0.5120]$ | $[0.0200, 0.9000]$ | **4.31×** |
| **$H = 72$** | $6.0\text{ h}$ | 27,280 (2,728/m) | 5,280 (528/m) | 5,280 (528/m) | 128 steps | **4.69%** ($128 / 2,728$) | $[0.0000, 0.2090]$ | $[0.0200, 0.5120]$ | $[0.0200, 0.9000]$ | **4.31×** |
| **$H = 144$** | $12.0\text{ h}$ | 26,560 (2,656/m) | 4,560 (456/m) | 4,560 (456/m) | 56 steps | **2.11%** ($56 / 2,656$) | $[0.0000, 0.2090]$ | $[0.0200, 0.5120]$ | $[0.0200, 0.9000]$ | **4.31×** |
| **$H = 288$** | $24.0\text{ h}$ | 25,120 (2,512/m) | 3,120 (312/m) | 3,120 (312/m) | 0 steps | **0.00%** ($0 / 2,512$) | $[0.0000, 0.2090]$ | $[0.0200, 0.5120]$ | $[0.0200, 0.9000]$ | **4.31×** |

*Note on Percentages:* The percentage of degradation steps in the training input is computed as $\frac{\max(0, (2800 - H) - 2600)}{2800 - H} \times 100\%$, where the denominator represents the exact number of usable training input steps per machine after enforcing strictly purged partition boundaries.

*Note on 4.31× Ratio:* The value 4.31× represents the **test-to-training maximum target ratio** ($\frac{\max(R_{\text{test}})}{\max(R_{\text{train}})} = \frac{0.9000}{0.2090}$). It quantifies the target boundary expansion resulting from chronological truncation, and is not a complete metric of multivariate distribution shift (such as Wasserstein distance).

---

## 5. Synthetic Fault Dynamics & Input Degradation Window

### 5.1 Generator Onset Mechanics
In [`ml/data_generator/generate_sensor_data.py`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/ml/data_generator/generate_sensor_data.py#L70), fault dynamics are introduced at a fixed step index:
$$\text{fault\_start} = \text{int}(\text{steps} \times 0.65) = 2600$$
For faulted machines (M102, M104, M107, M109), sensor values prior to step 2600 are drawn from nominal baseline Gaussian distributions with shift-factor adjustments.

### 5.2 Training Input Truncation for $H = 288$
Under strictly purged partition boundaries:
- Training inputs span timesteps $t \in [0, 2511]$.
- Training targets span timesteps $t + 288 \in [288, 2799]$.

Because training inputs terminate at step 2511, they end **89 steps prior to synthetic fault activation at step 2600**. Consequently, the training input partition for $H = 288$ contains zero timesteps of the intended physical degradation progression.

Rather than claiming that predictive modeling is mathematically impossible across all conceivable formulations, this audit establishes that **the intended synthetic degradation progression is absent from the $H = 288$ training inputs**. Consequently, supervised models trained strictly on this window lack the representative progressive fault data required to learn the progression dynamics designed in the synthetic generator.

---

## 6. Differentiated Analysis of Sensor Signals & Pseudoreplication

### 6.1 Sample Moments (Means & Standard Deviations)
Comparing the 10,048 training input readings from future-faulted machines against the 15,072 readings from permanently healthy machines (steps 0 to 2511):
- **Vibration ($\text{g}$):** Faulted $\mu = 1.8046, \; \sigma = 0.2177$ vs Healthy $\mu = 1.8019, \; \sigma = 0.2264$ ($\Delta \mu = +0.0027$)
- **Temperature ($^\circ\text{C}$):** Faulted $\mu = 47.9725, \; \sigma = 2.1904$ vs Healthy $\mu = 47.9758, \; \sigma = 2.2094$ ($\Delta \mu = -0.0033$)
- **Pressure ($\text{bar}$):** Faulted $\mu = 6.2031, \; \sigma = 0.1213$ vs Healthy $\mu = 6.2013, \; \sigma = 0.1211$ ($\Delta \mu = +0.0018$)
- **Current ($\text{A}$):** Faulted $\mu = 14.5258, \; \sigma = 0.7189$ vs Healthy $\mu = 14.5191, \; \sigma = 0.7028$ ($\Delta \mu = +0.0067$)
- **RPM:** Faulted $\mu = 1799.9235, \; \sigma = 7.4527$ vs Healthy $\mu = 1800.0165, \; \sigma = 7.4607$ ($\Delta \mu = -0.0930$)

### 6.2 Pseudoreplication & Exploratory Hypothesis Testing
The 25,120 training input observations originate from repeated measurements across **only 10 physical machines** (4 future-faulted, 6 healthy). In experimental statistics, treating repeated longitudinal measurements from a small number of experimental units as independent samples constitutes **pseudoreplication** (Hurlbert, 1984).

Standard hypothesis tests on the pooled observations yield:
- **Vibration:** Welch $t = 0.9728 \; (p = 0.3307)$; Mann-Whitney $p = 0.0992$
- **Temperature:** Welch $t = -0.1180 \; (p = 0.9061)$; Mann-Whitney $p = 0.9932$
- **Pressure:** Welch $t = 1.1988 \; (p = 0.2306)$; Mann-Whitney $p = 0.2557$
- **Current:** Welch $t = 0.7310 \; (p = 0.4648)$; Mann-Whitney $p = 0.4156$
- **RPM:** Welch $t = -0.9683 \; (p = 0.3329)$; Mann-Whitney $p = 0.3213$

**Exploratory Status:** Because of within-machine clustering and temporal correlation, these p-values must be interpreted strictly as **exploratory observational evidence** indicating that baseline means and standard deviations do not exhibit large obvious separations, rather than rigorous inferential proof of zero predictive information.

### 6.3 Input-to-Target Predictive Correlation
Measuring the linear and rank correlation between training inputs $x(t)$ and targets $R(t + 288)$ across all 25,120 training samples confirms negligible association:
- **Vibration:** Pearson $r = -0.0053$, Spearman $\rho = -0.0058$
- **Temperature:** Pearson $r = -0.0556$, Spearman $\rho = -0.0317$
- **Pressure:** Pearson $r = -0.0053$, Spearman $\rho = -0.0041$
- **Current:** Pearson $r = -0.0137$, Spearman $\rho = -0.0095$
- **RPM:** Pearson $r = +0.0035$, Spearman $\rho = +0.0040$

---

## 7. Verified Anomaly Model Benchmark Metrics

To support Phase 3 multi-agent health tracking, the platform relies on the previously trained, calibrated, and independently audited Phase 2 anomaly models.

### 7.1 Model 1: Isolation Forest (Point-Level Telemetry)
- **Reference:** [`reports/phase2/isolation_forest/isolation_forest_evaluation.md`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/isolation_forest/isolation_forest_evaluation.md)
- **Evaluation Partition:** Untouched Test Partition ($N = 6,000$ points across steps 3400–3999 for 10 machines).
- **Threshold:** $\tau_{\text{IF}} = 0.0269$ (score offset calibrated on normal validation readings).
- **Confusion Matrix:** $\text{TN} = 3,359, \quad \text{FP} = 241, \quad \text{FN} = 0, \quad \text{TP} = 2,400$
- **Benchmark Metrics:**
  - $\text{F1-Score} = \mathbf{0.9522}$ ($95.22\%$)
  - $\text{Precision} = \mathbf{0.9087}$ ($90.87\%$)
  - $\text{Recall} = \mathbf{1.0000}$ ($100.0\%$)
  - $\text{Accuracy} = \mathbf{0.9598}$ ($95.98\%$)
  - $\text{Specificity} = \mathbf{0.9331}$ ($93.31\%$)
  - $\text{ROC-AUC} = \mathbf{0.9979}$
  - $\text{PR-AUC} = \mathbf{0.9965}$

### 7.2 Model 2: LSTM Autoencoder (Sequence-Level Telemetry)
- **Reference:** [`reports/phase2/lstm_autoencoder/lstm_autoencoder_evaluation.md`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/lstm_autoencoder/lstm_autoencoder_evaluation.md)
- **Evaluation Partition:** Untouched Test Partition ($N = 580$ overlapping sequences of window length 30, step size 10 across 10 machines).
- **Threshold:** $\tau_{\text{LSTM}} = 0.901464$ (reconstruction MSE at 99th percentile of normal validation sequences).
- **Confusion Matrix:** $\text{TN} = 344, \quad \text{FP} = 4, \quad \text{FN} = 0, \quad \text{TP} = 232$
- **Benchmark Metrics:**
  - $\text{F1-Score} = \mathbf{0.9915}$ ($99.15\%$)
  - $\text{Precision} = \mathbf{0.9831}$ ($98.31\%$)
  - $\text{Recall} = \mathbf{1.0000}$ ($100.0\%$)
  - $\text{Accuracy} = \mathbf{0.9931}$ ($99.31\%$)
  - $\text{Specificity} = \mathbf{0.9885}$ ($98.85\%$)
  - $\text{ROC-AUC} = \mathbf{1.0000}$
  - $\text{PR-AUC} = \mathbf{1.0000}$

---

## 8. Preserved Architecture Status & Operational Guardrails

### 8.1 Status of System Components

```
+---------------------------------------------------------------------------------------------------+
|                                 MANUMIND AI SYSTEM COMPONENT STATUS                               |
+----------------------------------------+-------------------+--------------------------------------+
| Subsystem / Component                  | Status            | Verification Basis                   |
+----------------------------------------+-------------------+--------------------------------------+
| Model 1: Isolation Forest              | IMPLEMENTED &     | Tested on untouched test partition   |
|                                        | VERIFIED          | (Point F1 = 0.9522, ROC-AUC = 0.9979) |
+----------------------------------------+-------------------+--------------------------------------+
| Model 2: LSTM Autoencoder              | IMPLEMENTED &     | Tested on untouched test partition   |
|                                        | VERIFIED          | (Seq F1 = 0.9915, ROC-AUC = 1.0000)  |
+----------------------------------------+-------------------+--------------------------------------+
| Multi-Sensor Score Fusion              | PROPOSED DESIGN   | Unvalidated design specification     |
|                                        | (REQUIRES AUDIT)  | for Phase 3 LangGraph agent tracking |
+----------------------------------------+-------------------+--------------------------------------+
| Dynamic Health Index Calculation       | PROPOSED DESIGN   | Unvalidated composite heuristic      |
|                                        | (REQUIRES AUDIT)  | requiring empirical plant tuning     |
+----------------------------------------+-------------------+--------------------------------------+
| Trend-Based Time-to-Threshold (TTT)    | PROPOSED DESIGN   | Unvalidated linear extrapolation     |
|                                        | (REQUIRES AUDIT)  | monitoring heuristic (NOT RUL)       |
+----------------------------------------+-------------------+--------------------------------------+
| Supervised Failure-Risk Tree Model     | CLOSED (NO-GO)    | Rejected due to severe temporal      |
|                                        | (APPROVED CLOSURE)| shift and absence of representative  |
|                                        |                   | representative degradation           |
|                                        |                   | progression in the training inputs   |
+----------------------------------------+-------------------+--------------------------------------+
```

### 8.2 Operational Guardrails
1. **Anomaly scores are NOT calibrated failure probabilities.** Anomaly scores quantify distance from nominal baseline operation (via isolation path length or reconstruction error), not the calibrated probability of functional breakdown.
2. **Trend-based time-to-threshold is an unvalidated monitoring heuristic.** While rolling slope estimation ($\frac{d}{dt}\text{Score}$) provides operational situational awareness, it must not be represented as a certified mathematical Remaining Useful Life (RUL) predictor.
3. **Phase 2 Anomaly Detection models are preserved intact.** Serialized model weights ([`isolation_forest.joblib`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/ml/models_store/isolation_forest.joblib), [`lstm_autoencoder.keras`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/ml/models_store/lstm_autoencoder.keras)), fitted scalers ([`sensor_scaler.joblib`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/ml/models_store/sensor_scaler.joblib)), and decision thresholds remain unchanged.

---

## 9. Future Dataset Requirements for Supervised Failure Prediction

To enable valid supervised failure-risk or Remaining Useful Life (RUL) regression modeling in future work, the telemetry dataset must satisfy:
1. **Multi-Trajectory Fleet Run-to-Failure Data:** An illustrative initial planning target of 30–50 complete run-to-failure operational episodes per failure mode (rather than a universal statistically established minimum), enabling entire machine lifecycles to be assigned to Train, Validation, and Test partitions without chronological truncation. The actual sample size should be determined using formal power analysis, expected degradation variability, and the intended evaluation design.
2. **De-confounded Machine Allocations:** Multiple physical machines experiencing the same failure mechanisms under varying load and ambient conditions, eliminating the 100% confounding between machine identity and fault mode.
3. **Physics-Based Degradation Precursors:** Data generation that simulates progressive physical damage accumulation (e.g., Paris-Erdogan crack propagation, Arrhenius thermal aging, or Archard mechanical wear) so that measurable precursors exist prior to functional breakdown.

---

## 10. References

- Hurlbert, S. H. (1984). Pseudoreplication and the design of ecological field experiments. *Ecological Monographs*, 54(2), 187-211.
- Liu, F. T., Ting, K. M., & Zhou, Z. H. (2008). Isolation forest. In *Eighth IEEE International Conference on Data Mining* (pp. 413-422). IEEE.

---

## Audit Sign-off

- **Audit Finding:** Supervised Random Forest and XGBoost regression of continuous future risk is not recommended under the current synthetic dataset and chronological evaluation design.
- **Action Taken:** Phase 2 Step 5 is formally approved and closed as an Independent Feasibility Assessment and Health-Monitoring Architecture Design.
- **Repository Integrity:** Models, datasets, database records, and completed Steps 0–4 remain 100% intact and preserved.
