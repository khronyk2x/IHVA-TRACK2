from typing import Dict, List, Any
import re
from collections import Counter

class ClinicalEvaluationMetrics:
    """Computes NLP evaluation metrics for generated clinical documentation and entities."""

    @staticmethod
    def calculate_token_f1(reference: str, hypothesis: str) -> Dict[str, float]:
        """Calculates token-level precision, recall, and F1 score."""
        ref_tokens = re.findall(r'\w+', reference.lower())
        hyp_tokens = re.findall(r'\w+', hypothesis.lower())

        if not ref_tokens or not hyp_tokens:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

        ref_counts = Counter(ref_tokens)
        hyp_counts = Counter(hyp_tokens)

        overlap = sum((ref_counts & hyp_counts).values())
        if overlap == 0:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

        precision = overlap / len(hyp_tokens)
        recall = overlap / len(ref_tokens)
        f1 = 2 * (precision * recall) / (precision + recall)

        return {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4)
        }

    @staticmethod
    def calculate_entity_coverage(extracted_entities: List[str], ground_truth_entities: List[str]) -> Dict[str, float]:
        """Evaluates named entity extraction recall against expected ground-truth list."""
        if not ground_truth_entities:
            return {"coverage": 1.0, "matched": 0, "total_expected": 0}

        extracted_set = {e.lower() for e in extracted_entities}
        gt_set = {e.lower() for e in ground_truth_entities}

        matched = len(extracted_set.intersection(gt_set))
        coverage = matched / len(gt_set) if gt_set else 0.0

        return {
            "coverage": round(coverage, 4),
            "matched": matched,
            "total_expected": len(gt_set)
        }
