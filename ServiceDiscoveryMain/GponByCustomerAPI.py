#!/usr/bin/env python3
"""
REST API serving the latest 'GPONServices_ByCustomer.csv' report produced
by the Tejas/Nokia GPON service-discovery pipeline (see push_data() /
insert_data_by_customer() in the collector script). Reads directly from the
CSV file on disk - does NOT query SQL Server, and does not re-run the
discovery pipeline. It just serves whatever the most recent CSV contains.

The report filename embeds the exact generation date/time
(e.g. "24_Jul(03-15PM)GPONServices_ByCustomer.csv"), so this always finds
the most recently modified file matching the pattern rather than a fixed
name.

Run:
    pip install fastapi uvicorn pandas
    uvicorn gpon_customer_api:app --host 0.0.0.0 --port 8001

Then, for example:
    GET http://<host>:8001/gpon-services-by-customer
    GET http://<host>:8001/gpon-services-by-customer?olt_hostname=ALPRBASWGPR001
    GET http://<host>:8001/gpon-services-by-customer?ont_serial=CAT2438V2V7
    GET http://<host>:8001/gpon-services-by-customer?node_ip=172.16.4.74&format=csv
"""

import glob
import io
import os
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse

REPORTS_DIR = r"E:\PycharmProjects\ServiceDiscoveryMain\Reports"
FILE_PATTERN = "*GPONServices_ByCustomer.csv"


app = FastAPI(title="GPON Services By Customer API", version="1.0")

# in-memory cache keyed on (file path, mtime) so the CSV isn't re-read from
# disk on every request - only when a newer file shows up
_cache = {"path": None, "mtime": None, "df": None}


def get_latest_report_file() -> Optional[str]:
    pattern = os.path.join(REPORTS_DIR, FILE_PATTERN)
    files = [f for f in glob.glob(pattern) if os.path.isfile(f)]
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def load_report_df() -> pd.DataFrame:
    latest_file = get_latest_report_file()
    if latest_file is None:
        raise HTTPException(
            status_code=404,
            detail=f"No report file found matching {FILE_PATTERN} in {REPORTS_DIR}",
        )

    mtime = os.path.getmtime(latest_file)
    if _cache["path"] == latest_file and _cache["mtime"] == mtime:
        return _cache["df"]

    df = pd.read_csv(latest_file)
    _cache.update({"path": latest_file, "mtime": mtime, "df": df})
    return df


def filter_df(
    df: pd.DataFrame,
    olt_hostname: Optional[str],
    ont_serial: Optional[str],
    node_ip: Optional[str],
    package: Optional[str],
) -> pd.DataFrame:
    # note: this CSV is grouped by Package/OLT Hostname/ONT Serial Number,
    # so columns like 'Node IP' may hold a comma-joined combination of
    # values for a group rather than a single value - contains-match
    # handles that correctly, an exact match would not
    if olt_hostname:
        df = df[df["OLT Hostname"].astype(str).str.contains(olt_hostname, case=False, na=False)]
    if ont_serial:
        df = df[df["ONT Serial Number"].astype(str).str.contains(ont_serial, case=False, na=False)]
    if node_ip:
        df = df[df["Node IP"].astype(str).str.contains(node_ip, case=False, na=False)]
    if package:
        df = df[df["Package"].astype(str).str.contains(package, case=False, na=False)]
    return df


@app.get("/gpon-services-by-customer")
def get_gpon_services_by_customer(
    olt_hostname: Optional[str] = Query(None, description="Filter by OLT hostname (partial match)"),
    ont_serial: Optional[str] = Query(None, description="Filter by ONT serial number (partial match)"),
    node_ip: Optional[str] = Query(None, description="Filter by OLT/Node IP (partial match)"),
    package: Optional[str] = Query(None, description="Filter by Package (partial match)"),
    format: str = Query("json", pattern="^(json|csv)$", description="Response format: 'json' or 'csv'"),
):
    df = load_report_df()
    df = filter_df(df, olt_hostname, ont_serial, node_ip, package)

    if df.empty:
        raise HTTPException(status_code=404, detail="No matching records found")

    if format == "csv":
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=gpon_services_by_customer.csv"},
        )
        

    df = df.astype(object).where(pd.notnull(df), None)

    return JSONResponse(content=df.to_dict(orient="records"))


@app.get("/health")
def health():
    latest = get_latest_report_file()
    return {"status": "ok", "latest_file": latest}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)