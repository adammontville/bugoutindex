from processing.normalize import normalize_metric

def calculate_category_score(metrics, weights):
    """Calculate the weighted score for a category."""
    return sum(normalize_metric(metrics[m], *weights[m]) * weights[m][2] for m in metrics)

