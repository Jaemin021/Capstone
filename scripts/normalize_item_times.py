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


def escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def pearson(values_a: List[Optional[float]], values_b: List[Optional[float]]) -> Optional[float]:
    pairs = [
        (a, b)
        for a, b in zip(values_a, values_b)
        if a is not None and b is not None
    ]
    if len(pairs) < 2:
        return None

    a_values = [pair[0] for pair in pairs]
    b_values = [pair[1] for pair in pairs]
    mean_a = sum(a_values) / len(a_values)
    mean_b = sum(b_values) / len(b_values)
    numerator = sum((a - mean_a) * (b - mean_b) for a, b in pairs)
    denom_a = math.sqrt(sum((a - mean_a) ** 2 for a in a_values))
    denom_b = math.sqrt(sum((b - mean_b) ** 2 for b in b_values))
    if denom_a == 0 or denom_b == 0:
        return None
    return numerator / (denom_a * denom_b)


def to_points(
    values: List[Optional[float]],
    width: int,
    height: int,
    padding_left: int,
    padding_right: int,
    padding_top: int,
    padding_bottom: int,
) -> str:
    n = len(values)
    if n == 0:
        return ""

    x_span = max(1, width - padding_left - padding_right)
    y_span = max(1, height - padding_top - padding_bottom)

    points: List[str] = []
    for index, value in enumerate(values):
        if value is None:
            continue
        x = padding_left if n == 1 else padding_left + (x_span * index / (n - 1))
        clipped = min(1.0, max(0.0, value))
        y = padding_top + (1.0 - clipped) * y_span
        points.append(f"{x:.2f},{y:.2f}")
    return " ".join(points)


def write_line_trends_html(
    path: Path,
    item_orders: List[int],
    records: List[Tuple[str, str, Dict[int, Optional[float]], Dict[int, Optional[float]]]],
) -> None:
    palette = [
        "#0ea5e9",
        "#22c55e",
        "#f97316",
        "#e11d48",
        "#8b5cf6",
        "#14b8a6",
        "#f59e0b",
        "#3b82f6",
        "#84cc16",
        "#a855f7",
        "#ef4444",
        "#06b6d4",
        "#10b981",
        "#fb7185",
        "#6366f1",
        "#2dd4bf",
    ]

    width = 1120
    height = 430
    p_left = 64
    p_right = 28
    p_top = 18
    p_bottom = 46
    plot_w = width - p_left - p_right
    plot_h = height - p_top - p_bottom

    lines_svg: List[str] = []
    legend_rows: List[str] = []
    respondent_values: List[Tuple[str, List[Optional[float]]]] = []

    for idx, (_, respondent_id, _, norm_map) in enumerate(records):
        values = [norm_map.get(order) for order in item_orders]
        respondent_values.append((respondent_id, values))
        color = palette[idx % len(palette)]
        points = to_points(values, width, height, p_left, p_right, p_top, p_bottom)
        if points:
            lines_svg.append(
                f'<polyline fill="none" stroke="{color}" stroke-width="1.8" opacity="0.45" points="{points}" />'
            )
        legend_rows.append(
            f'<div class="legend-item"><span class="swatch" style="background:{color};"></span>{escape_html(respondent_id)}</div>'
        )

    mean_values: List[Optional[float]] = []
    for order in item_orders:
        valid = [norm_map.get(order) for _, _, _, norm_map in records if norm_map.get(order) is not None]
        if not valid:
            mean_values.append(None)
        else:
            mean_values.append(sum(valid) / len(valid))
    mean_points = to_points(mean_values, width, height, p_left, p_right, p_top, p_bottom)
    if mean_points:
        lines_svg.append(
            f'<polyline fill="none" stroke="#111827" stroke-width="3.2" opacity="0.95" points="{mean_points}" />'
        )

    y_ticks = [0.0, 0.25, 0.5, 0.75, 1.0]
    y_grid = []
    for t in y_ticks:
        y = p_top + (1.0 - t) * plot_h
        y_grid.append(
            f'<line x1="{p_left}" y1="{y:.2f}" x2="{width - p_right}" y2="{y:.2f}" stroke="#e2e8f0" stroke-width="1" />'
        )
        y_grid.append(
            f'<text x="{p_left - 10}" y="{y + 4:.2f}" text-anchor="end" font-size="12" fill="#475569">{t:.2f}</text>'
        )

    x_ticks = []
    for idx, order in enumerate(item_orders):
        x = p_left if len(item_orders) == 1 else p_left + (plot_w * idx / (len(item_orders) - 1))
        x_ticks.append(
            f'<line x1="{x:.2f}" y1="{p_top}" x2="{x:.2f}" y2="{height - p_bottom}" stroke="#f1f5f9" stroke-width="1" />'
        )
        x_ticks.append(
            f'<text x="{x:.2f}" y="{height - p_bottom + 20}" text-anchor="middle" font-size="11" fill="#475569">Q{order}</text>'
        )

    pair_corr: List[float] = []
    for i in range(len(respondent_values)):
        for j in range(i + 1, len(respondent_values)):
            corr = pearson(respondent_values[i][1], respondent_values[j][1])
            if corr is not None:
                pair_corr.append(corr)
    avg_corr_text = "-" if not pair_corr else f"{(sum(pair_corr) / len(pair_corr)):.3f}"
    min_corr_text = "-" if not pair_corr else f"{min(pair_corr):.3f}"
    max_corr_text = "-" if not pair_corr else f"{max(pair_corr):.3f}"

    small_cards = []
    card_w = 340
    card_h = 170
    for idx, (respondent_id, values) in enumerate(respondent_values):
        color = palette[idx % len(palette)]
        pts = to_points(values, card_w, card_h, 34, 16, 16, 30)
        card_grid = []
        for t in [0.0, 0.5, 1.0]:
            y = 16 + (1.0 - t) * (card_h - 46)
            card_grid.append(
                f'<line x1="34" y1="{y:.2f}" x2="{card_w - 16}" y2="{y:.2f}" stroke="#eef2f7" stroke-width="1" />'
            )
        card_x_ticks = []
        for i2, order in enumerate(item_orders):
            x = 34 if len(item_orders) == 1 else 34 + (card_w - 50) * i2 / (len(item_orders) - 1)
            if i2 == 0 or i2 == len(item_orders) - 1 or i2 % 5 == 0:
                card_x_ticks.append(
                    f'<text x="{x:.2f}" y="{card_h - 10}" text-anchor="middle" font-size="9" fill="#64748b">Q{order}</text>'
                )
        small_cards.append(
            f"""
            <div class="card">
              <div class="card-title">{escape_html(respondent_id)}</div>
              <svg width="{card_w}" height="{card_h}" viewBox="0 0 {card_w} {card_h}">
                {''.join(card_grid)}
                <polyline fill="none" stroke="{color}" stroke-width="2" points="{pts}" />
                {''.join(card_x_ticks)}
              </svg>
            </div>
            """
        )

    html = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <title>Item Time Line Trends</title>
  <style>
    body {{
      margin: 20px;
      font-family: Arial, sans-serif;
      color: #0f172a;
    }}
    h2 {{
      margin: 0 0 8px 0;
    }}
    .sub {{
      color: #475569;
      font-size: 13px;
      margin-bottom: 14px;
    }}
    .summary {{
      display: flex;
      gap: 20px;
      font-size: 13px;
      margin-bottom: 12px;
    }}
    .chart-wrap {{
      border: 1px solid #e2e8f0;
      border-radius: 10px;
      padding: 10px 10px 4px 10px;
      background: #ffffff;
    }}
    .legend {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 6px 10px;
      margin-top: 10px;
      font-size: 12px;
    }}
    .legend-item {{
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .swatch {{
      display: inline-block;
      width: 10px;
      height: 10px;
      margin-right: 6px;
      vertical-align: middle;
      border-radius: 2px;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
      gap: 12px;
      margin-top: 18px;
    }}
    .card {{
      border: 1px solid #e2e8f0;
      border-radius: 10px;
      padding: 8px;
      background: #ffffff;
    }}
    .card-title {{
      font-size: 12px;
      color: #334155;
      margin-bottom: 4px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
  </style>
</head>
<body>
  <h2>문항별 정규화 응답시간 선그래프 (응답자별)</h2>
  <div class="sub">X축: 문항(Q1..Qn), Y축: 응답자 내부 Min-Max 정규화 시간(0~1)</div>
  <div class="summary">
    <div><b>응답자 수:</b> {len(records)}</div>
    <div><b>문항 수:</b> {len(item_orders)}</div>
    <div><b>평균 추세 상관(피어슨):</b> {avg_corr_text}</div>
    <div><b>최소/최대 상관:</b> {min_corr_text} / {max_corr_text}</div>
  </div>
  <div class="chart-wrap">
    <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">
      {''.join(y_grid)}
      {''.join(x_ticks)}
      <rect x="{p_left}" y="{p_top}" width="{plot_w}" height="{plot_h}" fill="none" stroke="#cbd5e1" stroke-width="1" />
      {''.join(lines_svg)}
    </svg>
  </div>
  <div class="legend">
    <div class="legend-item"><span class="swatch" style="background:#111827;"></span>전체 평균 추세</div>
    {''.join(legend_rows)}
  </div>
  <h3 style="margin-top:22px;">개별 응답자 추세</h3>
  <div class="cards">
    {''.join(small_cards)}
  </div>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")


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
    parser.add_argument(
        "--output-dir",
        default="",
        help="Directory for generated files (default: <input_dir>/test_outputs/item_time)",
    )
    args = parser.parse_args()

    input_path = Path(args.input_csv)
    if not input_path.exists():
        raise SystemExit(f"[error] file not found: {input_path}")

    if args.output_dir:
        output_dir = Path(args.output_dir)
        if not output_dir.is_absolute():
            output_dir = (Path.cwd() / output_dir).resolve()
    else:
        output_dir = (input_path.parent / "test_outputs" / "item_time").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

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

    stem_name = input_path.stem
    raw_matrix_path = output_dir / f"{stem_name}_item_time_matrix_ms.csv"
    minmax_matrix_path = output_dir / f"{stem_name}_item_time_matrix_minmax_by_respondent.csv"
    zscore_matrix_path = output_dir / f"{stem_name}_item_time_matrix_zscore_by_respondent.csv"
    long_path = output_dir / f"{stem_name}_item_time_long_normalized.csv"
    heatmap_path = output_dir / f"{stem_name}_item_time_heatmap.html"
    line_trend_path = output_dir / f"{stem_name}_item_time_line_trends.html"

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
    write_line_trends_html(line_trend_path, item_orders, records)

    print("[done] input:", input_path)
    print("[done] respondents:", len(records))
    print("[done] item columns:", len(item_orders))
    print("[done] output_dir:", output_dir)
    print("[out ]", raw_matrix_path)
    print("[out ]", minmax_matrix_path)
    print("[out ]", zscore_matrix_path)
    print("[out ]", long_path)
    print("[out ]", heatmap_path)
    print("[out ]", line_trend_path)


if __name__ == "__main__":
    main()
