def normalize_metric(raw_value, min_value, max_value):
    """Normalize a raw value to a 0-100 scale."""
    if max_value == min_value:
        return 0  # Avoid division by zero
    return (1 - ((raw_value - min_value) / (max_value - min_value))) * 100

