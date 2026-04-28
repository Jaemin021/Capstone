import math
import models

EPS = 0.03
MIN_POPULATION_RESPONSES = 3


def calculate_time_share_vector(item_logs, survey_items):
    time_map = {
        log.item_id: log.item_time_ms or 0
        for log in item_logs
    }

    ordered_items = sorted(survey_items, key=lambda x: x.item_order)

    ordered_times = [
        time_map.get(item.item_id, 0)
        for item in ordered_items
    ]

    total_time = sum(ordered_times)

    if total_time <= 0:
        return [0] * len(ordered_times)

    return [
        item_time / total_time
        for item_time in ordered_times
    ]


def mean_vector(vectors):
    if not vectors:
        return []

    length = len(vectors[0])

    return [
        sum(vector[i] for vector in vectors) / len(vectors)
        for i in range(length)
    ]


def std_vector(vectors, mean):
    if not vectors or not mean:
        return []

    result = []

    for i in range(len(mean)):
        variance = (
            sum((vector[i] - mean[i]) ** 2 for vector in vectors)
            / len(vectors)
        )

        std = math.sqrt(variance)
        result.append(max(std, EPS))

    return result


def deviation(current, mean, std):
    if not current or not mean or not std:
        return None

    z_scores = [
        abs(current_value - mean_value) / std_value
        for current_value, mean_value, std_value in zip(current, mean, std)
    ]

    if not z_scores:
        return None

    return sum(z_scores) / len(z_scores)


def calculate_population_features(db, survey_id, response_id):
    survey_items = db.query(models.SurveyItem).filter_by(
        survey_id=survey_id
    ).all()

    responses = db.query(models.Response).filter_by(
        survey_id=survey_id,
        is_completed=True
    ).all()

    population_vectors = []

    for response in responses:
        if response.response_id == response_id:
            continue

        item_logs = db.query(models.ResponseItemLog).filter_by(
            response_id=response.response_id
        ).all()

        if item_logs:
            vector = calculate_time_share_vector(
                item_logs=item_logs,
                survey_items=survey_items
            )
            population_vectors.append(vector)

    if len(population_vectors) < MIN_POPULATION_RESPONSES:
        return {
            "time_curve_deviation": None,
            "population_sample_count": len(population_vectors)
        }

    mean = mean_vector(population_vectors)
    std = std_vector(population_vectors, mean)

    current_logs = db.query(models.ResponseItemLog).filter_by(
        response_id=response_id
    ).all()

    current_vector = calculate_time_share_vector(
        item_logs=current_logs,
        survey_items=survey_items
    )

    time_curve_deviation = deviation(
        current=current_vector,
        mean=mean,
        std=std
    )

    return {
        "time_curve_deviation": time_curve_deviation,
        "population_sample_count": len(population_vectors)
    }