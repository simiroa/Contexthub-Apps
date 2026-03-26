from __future__ import annotations


def safe_float(value: str) -> float | None:
    try:
        return float(str(value).strip())
    except Exception:
        return None


class VersusUpScoringService:
    def recalculate_scores(self, state, cell_value) -> None:
        scores = {product.id: 0.0 for product in state.products}
        reasons = {product.id: [] for product in state.products}
        for criterion in state.criteria:
            if criterion.type != "number" or not criterion.include_in_score:
                continue
            numeric_values: list[tuple[str, float]] = []
            for product in state.products:
                value = safe_float(cell_value(product.id, criterion.id))
                if value is not None:
                    numeric_values.append((product.id, value))
            if not numeric_values:
                continue
            values = [item[1] for item in numeric_values]
            min_value = min(values)
            max_value = max(values)
            span = max_value - min_value
            for product_id, value in numeric_values:
                normalized = 1.0 if span == 0 else (value - min_value) / span
                if criterion.direction == "low":
                    normalized = 1.0 - normalized
                weighted = normalized * criterion.weight
                scores[product_id] += weighted
                reasons[product_id].append(f"{criterion.label}: {value}{criterion.unit} -> {weighted:.2f}")
        state.scores = scores
        state.score_reasons = reasons
