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
import pandas as pd

def fetch():
    """Fetch the 2025 Trust in Government score from the Edelman dataset."""
    file_path = "data/edelman-trust-barometer-us.csv"

    try:
        df = pd.read_csv(file_path)
        df.columns = df.columns.str.strip().str.lower()
        government_row = df[df["institution"] == "Government"]
        trust_score = government_row["2025"].values[0]
        return {"status": "success", "data": {"trust_in_government": round(float(trust_score), 2)}}
    except KeyError as e:
        return {"status": "error", "message": f"Column missing: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# def fetch():
#     """Fetch the latest Trust in Government data."""
#     print("Fetching Trust in Government...")
#     # Data is manually updated from Edelman Trust Barometer (see https://www.edelman.com/trust/25years)
#     return {"status": "success", "fetched_at": "2025-01-01T00:00:00Z", "data": {"trust": 2.00}}