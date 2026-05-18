# backend/services/item_quality_dictionary.py

AMBIGUOUS_TERMS = [
    "자주", "가끔", "대체로", "적당히", "보통", "많이", "조금",
    "충분히", "가능한 한", "대부분", "일반적으로"
]

NEGATIVE_TERMS = [
    "않다", "아니다", "없다", "못하다"
]

LEADING_TERMS = [
    "당연히", "반드시", "꼭", "확실히"
]

DOUBLE_BARRELED_HINTS = [
    "그리고", "또한", "및", "거나", "또는"
]