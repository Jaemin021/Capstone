def compute_variance_score(variance_value: float) -> float:
    raise NotImplementedError


def compute_citc_score(citc_value: float) -> float:
    raise NotImplementedError


def compute_missing_score(missing_rate: float) -> float:
    raise NotImplementedError


def compute_overall_post_score(
    variance_score: float,
    citc_score: float,
    missing_score: float
) -> float:
    return round((variance_score + citc_score + missing_score) / 3, 2)