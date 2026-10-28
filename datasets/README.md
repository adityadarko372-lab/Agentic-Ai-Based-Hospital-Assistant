# Datasets (optional, Phase 5)

None of these files are needed for the required demo. Raw downloads go to
`datasets/raw/` and prepared files to `datasets/processed/`; both folders are
gitignored and rebuilt by the scripts below.

| Dataset | Used for | Licence | Script |
|---|---|---|---|
| [MedQuAD](https://github.com/abachaa/MedQuAD) (Ben Abacha & Demner-Fushman, 2019) | Health Information Agent (cited general information) | CC BY 4.0 | `datasets/prepare_medquad.py` |
| [CLINC150](https://github.com/clinc/oos-eval) (Larson et al., 2019) | Extra greeting / help / out-of-scope examples for the trained intent classifier | CC BY 3.0 | `model/intent_classifier/build_dataset.py` |

## MedQuAD preparation (measured on 28 Oct 2026)

| Step | Count |
|---|---|
| XML documents in the repository zip (16.2 MB) | 11,274 |
| Question/answer pairs in those files | 47,441 |
| Kept after filtering | 16,181 |
| Kept after removing duplicates | 16,108 |

What is removed and why:
- Pairs with no answer. The A.D.A.M., MedlinePlus Herbs and MedlinePlus Drugs
  collections ship without answers (removed by the dataset authors for copyright).
- Medicine-specific question types (dosage, side effects, interactions, ...) and
  whole topics about medicines (for example "Diabetes Medicines"). Nova Health
  does not give medication advice.
- Stub answers shorter than 80 characters.

The XML is parsed with `defusedxml`, which refuses entity declarations.

## Intent classifier data

`model/intent_classifier/build_dataset.py` fills fixed templates with Nova Health
departments, symptoms, dates and conditions, and adds a sample of CLINC150.
CLINC150 intents that overlap hospital wording (insurance, scheduling, reminders,
reservations) are dropped rather than labelled out of scope. The two test sets
in `model/intent_classifier/test_set*.json` were written by hand and are never
used for training.

## Attribution

- Ben Abacha A, Demner-Fushman D. A question-entailment approach to question
  answering. *BMC Bioinformatics* 20, 511 (2019). CC BY 4.0.
- Larson S, et al. An Evaluation Dataset for Intent Classification and
  Out-of-Scope Prediction. *EMNLP-IJCNLP* 2019. CC BY 3.0.
