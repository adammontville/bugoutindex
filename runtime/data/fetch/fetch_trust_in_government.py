# BugOutIndex
# Copyright (C) 2025 Your Name or Organization
#
# This file is dual-licensed under the AGPL-3.0 and a commercial license.
#
# You may use, modify, and distribute this software under the terms of the
# GNU Affero General Public License v3.0 as published by the Free Software Foundation.
#
# For proprietary or commercial use, please contact: your-email@example.com
"""
Module Description:
Provides data related to trust in government.
"""
import os
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.abspath(os.path.join(_HERE, ".."))


def fetch():
    """Fetch the most recent Trust in Government score from the Edelman dataset."""
    candidates = [
        os.path.join(_DATA_DIR, "edelman-trust-barometer-us.csv"),
        "data/edelman-trust-barometer-us.csv",
        "runtime/data/edelman-trust-barometer-us.csv",
    ]
    file_path = next((p for p in candidates if os.path.exists(p)), candidates[0])

    try:
        df = pd.read_csv(file_path)
        df.columns = df.columns.str.strip().str.lower()
        government_row = df[df["institution"].str.lower() == "government"]
        # Pick the most recent year column present in the dataset.
        year_cols = [c for c in df.columns if c.isdigit()]
        latest_year = max(year_cols)
        trust_score = government_row[latest_year].values[0]
        return {"status": "success", "fetched_at": latest_year,
                "data": {"trust_in_government": round(float(trust_score), 2)}}
    except KeyError as e:
        return {"status": "error", "message": f"Column missing: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# def fetch():
#     """Fetch the latest Trust in Government data."""
#     print("Fetching Trust in Government...")
#     # Data is manually updated from Edelman Trust Barometer (see https://www.edelman.com/trust/25years)
#     return {"status": "success", "fetched_at": "2025-01-01T00:00:00Z", "data": {"trust": 2.00}}