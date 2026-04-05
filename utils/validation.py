from config import RULE_PENALTY_WEIGHTS
from dictionaries.terms import TERM_DICTIONARY


def validate_feature_alignment():
    errors = []

    all_categories = set(TERM_DICTIONARY.keys()) | set(RULE_PENALTY_WEIGHTS.keys())

    for category in all_categories:
        dict_features = set(TERM_DICTIONARY.get(category, {}).keys())
        weight_features = set(RULE_PENALTY_WEIGHTS.get(category, {}).keys())

        missing_in_weights = dict_features - weight_features
        missing_in_dict = weight_features - dict_features

        if missing_in_weights:
            errors.append(
                f"[{category}] TERM_DICTIONARY에만 있고 RULE_PENALTY_WEIGHTS에 없는 feature: {missing_in_weights}"
            )

        if missing_in_dict:
            errors.append(
                f"[{category}] RULE_PENALTY_WEIGHTS에만 있고 TERM_DICTIONARY에 없는 feature: {missing_in_dict}"
            )

    if errors:
        raise ValueError("\n".join(errors))

    print("✅ feature alignment OK")