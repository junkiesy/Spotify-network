"""
Utility script to augment `combined_artist_details_extended_with_categories_and_labels.csv`
with the `record_label` column sourced from `data_with_labels.csv`, matched on artist ID.
"""

import pandas as pd
from pathlib import Path


def main() -> None:
    root = Path(__file__).parent
    data_with_labels = root / "data_with_labels.csv"
    combined = root / "combined_artist_details_extended_with_categories_and_labels.csv"

    if not data_with_labels.exists():
        raise FileNotFoundError(f"Missing input file: {data_with_labels}")
    if not combined.exists():
        raise FileNotFoundError(f"Missing input file: {combined}")

    df_labels = pd.read_csv(data_with_labels)
    df_combined = pd.read_csv(combined)

    # Align column names so we can merge on the artist ID.
    if "id.x" not in df_labels.columns:
        raise KeyError("Expected column 'id.x' not found in data_with_labels.csv")
    df_labels = df_labels.rename(columns={"id.x": "id"})

    # Keep only the ID and record_label to avoid accidental column overrides.
    df_labels = df_labels[["id", "record_label"]]

    # Merge, preserving all existing combined rows.
    merged = df_combined.merge(df_labels, on="id", how="left")

    # Reorder to keep record_label at the end for readability.
    cols = [c for c in df_combined.columns if c != "record_label"]
    if "record_label" in merged.columns:
        cols.append("record_label")
    merged = merged[cols]

    output = root / "combined_artist_details_extended_with_categories_and_labels_with_labels.csv"
    merged.to_csv(output, index=False)

    print(f"Augmented file written to: {output}")
    print(f"Rows: {len(merged):,}, Columns: {len(merged.columns)}")


if __name__ == "__main__":
    main()

