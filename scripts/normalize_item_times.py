import argparse
import csv
import json
import math
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


ITEM_TIME_COLUMN_PATTERN = re.compile(r"^item_(\d+)_time_ms$")


def parse_float(value: str) -> Optional[float]:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except Exception:
        return None


def detect_item_orders_from_header(header: List[str]) -> List[int]:
    orders: List[int] = []
    for name in header:
        match = ITEM_TIME_COLUMN_PATTERN.match(name)
        if match:
            orders.append(int(match.group(1)))
    return sorted(set(orders))


def extract_item_times(
    row: Dict[str, str],
    item_orders: List[int],
    has_json_fallback: bool,
) -> Dict[int, Optional[float]]:
    values: Dict[int, Optional[float]] = {}
    for order in item_orders:
        values[order] = parse_float(row.get(f"item_{order}_time_ms", ""))

    if has_json_fallback:
        json_text = (row.get("item_time_ms_by_order_json") or "").strip()
        if json_text:
            try:
                payload = json.loads(json_text)
                if isinstance(payload, dict):
                    for key, value in payload.items():
                        try:
                            order = int(key)
                        except Exception:
                            continue
                        if order not in values:
                            values[order] = parse_float(str(value))
                        elif values[order] is None:
                            values[order] = parse_float(str(value))
            except Exception:
                pass
    return values


def minmax(values: List[Optional[float]]) -> List[Optional[float]]:
    valid = [value for value in values if value is not None]
    if not valid:
        return [None for _ in values]
    lower = min(valid)
    upper = max(valid)
    if upper <= lower:
        return [0.0 if value is not None else None for value in values]
    return [
        ((value - lower) / (upper - lower)) if value is not None else None
        for value in values
    ]


def zscore(values: List[Optional[float]]) -> List[Optional[float]]:
    valid = [value for value in values if value is not None]
    if not valid:
        return [None for _ in values]
    mean = sum(valid) / len(valid)
    variance = sum((value - mean) ** 2 for value in valid) / len(valid)
    std = math.sqrt(variance)
    if std == 0:
        return [0.0 if value is not None else None for value in values]
    return [((value - mean) / std) if value is not None else None for value in values]


def value_or_blank(value: Optional[float], digits: int = 6) -> str:
    if value is None:
        return ""
    return f"{value:.{digits}f}"


def color_for_norm(norm_value: Optional[float]) -> str:
    if norm_value is None:
        return "#f8fafc"
    ratio = min(1.0, max(0.0, norm_value))
    start = (241, 245, 249)
    end = (15, 118, 110)
    r = int(start[0] + (end[0] - start[0]) * ratio)
    g = int(start[1] + (end[1] - start[1]) * ratio)
    b = int(start[2] + (end[2] - start[2]) * ratio)
    return f"rgb({r},{g},{b})"


def write_csv(path: Path, header: List[str], rows: List[List[str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(header)
        writer.writerows(rows)


def write_heatmap_html(
    path: Path,
    item_orders: List[int],
    records: List[Tuple[str, str, Dict[int, Optional[float]], Dict[int, Optional[float]]]],
) -> None:
    table_rows: List[str] = []
    for response_id, respondent_id, raw_map, norm_map in records:
        cells = []
        for order in item_orders:
            raw = raw_map.get(order)
            norm = norm_map.get(order)
            color = color_for_norm(norm)
            label = "-" if raw is None else f"{raw:.0f}ms"
            title = (
                f"Q{order} | {respondent_id} | "
                + (f"raw={raw:.3f} ms, norm={norm:.3f}" if raw is not None and norm is not None else "no data")
            )
            cells.append(
                f'<td title="{title}" style="background:{color};text-align:center;padding:6px 8px;border:1px solid #e2e8f0;">{label}</td>'
            )
        table_rows.append(
            "<tr>"
            + f'<td style="padding:6px 8px;border:1px solid #e2e8f0;white-space:nowrap;">{respondent_id}</td>'
            + f'<td style="padding:6px 8px;border:1px solid #e2e8f0;white-space:nowrap;">{response_id}</td>'
            + "".join(cells)
            + "</tr>"
        )

    item_headers = "".join(
        f'<th style="padding:6px 8px;border:1px solid #e2e8f0;">Q{order}</th>'
        for order in item_orders
    )
    html = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <title>Item Time Heatmap</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      margin: 20px;
      color: #0f172a;
    }}
    .legend {{
      margin: 12px 0 18px 0;
      font-size: 13px;
      color: #334155;
    }}
    .bar {{
      width: 240px;
      height: 12px;
      background: linear-gradient(to right, rgb(241,245,249), rgb(15,118,110));
      border: 1px solid #cbd5e1;
      display: inline-block;
      vertical-align: middle;
      margin: 0 8px;
    }}
    table {{
      border-collapse: collapse;
      font-size: 12px;
    }}
    th {{
      background: #f1f5f9;
      position: sticky;
      top: 0;
    }}
  </style>
</head>
<body>
  <h2>문항별 응답시간 정규화 Heatmap (응답자별 Min-Max)</h2>
  <div class="legend">빠름 <span class="bar"></span> 느림</div>
  <table>
    <thead>
      <tr>
        <th style="padding:6px 8px;border:1px solid #e2e8f0;">respondent_id</th>
        <th style="padding:6px 8px;border:1px solid #e2e8f0;">response_id</th>
        {item_headers}
      </tr>
    </thead>
    <tbody>
      {''.join(table_rows)}
    </tbody>
  </table>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalize per-item response times from response-features CSV."
    )
    parser.add_argument(
        "input_csv",
        nargs="?",
        default="sa1.csv",
        help="Path to response-features CSV",
    )
    args = parser.parse_args()

    input_path = Path(args.input_csv)
    if not input_path.exists():
        raise SystemExit(f"[error] file not found: {input_path}")

    with input_path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None:
            raise SystemExit("[error] empty csv")
        rows = list(reader)
        header = reader.fieldnames

    item_orders = detect_item_orders_from_header(header)
    has_json_fallback = "item_time_ms_by_order_json" in header

    if not item_orders and not has_json_fallback:
        raise SystemExit(
            "[error] item time columns not found. "
            "Download the updated response-features CSV after backend patch."
        )

    records: List[Tuple[str, str, Dict[int, Optional[float]], Dict[int, Optional[float]]]] = []
    discovered_orders = set(item_orders)
    raw_rows: List[Tuple[str, str, Dict[int, Optional[float]]]] = []

    for row in rows:
        response_id = (row.get("response_id") or "").strip()
        respondent_id = (row.get("respondent_id") or "").strip()
        values = extract_item_times(row, item_orders, has_json_fallback)
        for key, value in values.items():
            if value is not None:
                discovered_orders.add(key)
        raw_rows.append((response_id, respondent_id, values))

    item_orders = sorted(discovered_orders)
    for response_id, respondent_id, values in raw_rows:
        ordered_values = [values.get(order) for order in item_orders]
        row_minmax = minmax(ordered_values)
        row_minmax_map = {order: row_minmax[index] for index, order in enumerate(item_orders)}
        value_map = {order: values.get(order) for order in item_orders}
        records.append((response_id, respondent_id, value_map, row_minmax_map))

    stem = input_path.with_suffix("")
    raw_matrix_path = stem.with_name(stem.name + "_item_time_matrix_ms.csv")
    minmax_matrix_path = stem.with_name(stem.name + "_item_time_matrix_minmax_by_respondent.csv")
    zscore_matrix_path = stem.with_name(stem.name + "_item_time_matrix_zscore_by_respondent.csv")
    long_path = stem.with_name(stem.name + "_item_time_long_normalized.csv")
    heatmap_path = stem.with_name(stem.name + "_item_time_heatmap.html")

    matrix_header = ["response_id", "respondent_id"] + [f"item_{order}_time_ms" for order in item_orders]
    matrix_rows: List[List[str]] = []
    minmax_rows: List[List[str]] = []
    zscore_rows: List[List[str]] = []
    long_rows: List[List[str]] = []

    for response_id, respondent_id, raw_map, minmax_map in records:
        raw_values = [raw_map.get(order) for order in item_orders]
        z_values = zscore(raw_values)
        matrix_rows.append(
            [response_id, respondent_id] + [value_or_blank(raw_map.get(order), 3) for order in item_orders]
        )
        minmax_rows.append(
            [response_id, respondent_id] + [value_or_blank(minmax_map.get(order), 6) for order in item_orders]
        )
        zscore_rows.append(
            [response_id, respondent_id] + [value_or_blank(z_values[index], 6) for index in range(len(item_orders))]
        )

        for index, order in enumerate(item_orders):
            raw = raw_values[index]
            long_rows.append(
                [
                    response_id,
                    respondent_id,
                    str(order),
                    value_or_blank(raw, 3),
                    value_or_blank(minmax_map.get(order), 6),
                    value_or_blank(z_values[index], 6),
                ]
            )

    write_csv(raw_matrix_path, matrix_header, matrix_rows)
    write_csv(minmax_matrix_path, matrix_header, minmax_rows)
    write_csv(zscore_matrix_path, matrix_header, zscore_rows)
    write_csv(
        long_path,
        [
            "response_id",
            "respondent_id",
            "item_order",
            "item_time_ms",
            "item_time_minmax_by_respondent",
            "item_time_zscore_by_respondent",
        ],
        long_rows,
    )
    write_heatmap_html(heatmap_path, item_orders, records)

    print("[done] input:", input_path)
    print("[done] respondents:", len(records))
    print("[done] item columns:", len(item_orders))
    print("[out ]", raw_matrix_path)
    print("[out ]", minmax_matrix_path)
    print("[out ]", zscore_matrix_path)
    print("[out ]", long_path)
    print("[out ]", heatmap_path)


if __name__ == "__main__":
    main()
