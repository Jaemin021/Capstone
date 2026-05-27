# backend/services/item_construct_embedding_service.py

from services.embedding_service import get_embedding, cosine_similarity


def build_construct_text(survey, normal_items):
    parts = []

    if survey.construct_name:
        parts.append(f"Construct name: {survey.construct_name}")

    if survey.construct_description:
        parts.append(f"Construct description: {survey.construct_description}")

    if not parts:
        parts.append(f"Survey title: {survey.title}")

    parts.append("Original survey items:")
    for item in normal_items:
        parts.append(f"- {item.question_text}")

    return "\n".join(parts)


def calculate_embedding_construct_features_from_vectors(
    target_item_id,
    item_vectors,
    construct_vec,
):
    target_vec = item_vectors.get(target_item_id)
    if target_vec is None:
        raise ValueError(f"target embedding missing for item_id={target_item_id}")

    construct_similarity = cosine_similarity(target_vec, construct_vec)
    item_sims = []

    for other_item_id, other_vec in item_vectors.items():
        if other_item_id == target_item_id:
            continue
        item_sims.append(cosine_similarity(target_vec, other_vec))

    if item_sims:
        mean_item_similarity = sum(item_sims) / len(item_sims)
        max_item_similarity = max(item_sims)
        min_item_similarity = min(item_sims)
    else:
        mean_item_similarity = 0.0
        max_item_similarity = 0.0
        min_item_similarity = 0.0

    embedding_features = {
        "construct_similarity": construct_similarity,
        "mean_item_similarity": mean_item_similarity,
        "max_item_similarity": max_item_similarity,
        "min_item_similarity": min_item_similarity,
        "comparison_item_count": len(item_sims),
    }

    embedding_score = (
        construct_similarity * 0.6 +
        mean_item_similarity * 0.4
    ) * 10

    return {
        "embedding_features": embedding_features,
        "embedding_score": round(embedding_score, 3),
    }


def evaluate_embedding_construct_features(target_item, survey, normal_items):
    target_vec = get_embedding(target_item.question_text)

    construct_text = build_construct_text(survey, normal_items)
    construct_vec = get_embedding(construct_text)

    item_vectors = {}
    for item in normal_items:
        item_vectors[item.item_id] = get_embedding(item.question_text)

    return calculate_embedding_construct_features_from_vectors(
        target_item_id=target_item.item_id,
        item_vectors=item_vectors,
        construct_vec=construct_vec,
    )
