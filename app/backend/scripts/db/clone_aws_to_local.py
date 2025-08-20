#!/usr/bin/env python3
"""
Clone AWS DynamoDB table schemas into DynamoDB Local and optionally copy sample items.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List

import boto3
import botocore


AWS_REGION: str = os.environ.get("AWS_DEFAULT_REGION", "eu-west-2")
LOCAL_ENDPOINT: str = os.environ.get("DYNAMODB_ENDPOINT", "http://localhost:8000")


def aws_client() -> boto3.client:
    return boto3.client("dynamodb", region_name=AWS_REGION)


def local_client() -> boto3.client:
    return boto3.client(
        "dynamodb",
        region_name="us-east-1",
        endpoint_url=LOCAL_ENDPOINT,
        aws_access_key_id="dummy",
        aws_secret_access_key="dummy",
    )


def minimal_create_params(desc: Dict[str, Any]) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "TableName": desc["TableName"],
        "KeySchema": desc["KeySchema"],
        "AttributeDefinitions": desc["AttributeDefinitions"],
        "BillingMode": "PAY_PER_REQUEST",
    }
    gsis: List[Dict[str, Any]] | None = desc.get("GlobalSecondaryIndexes")
    if gsis:
        params["GlobalSecondaryIndexes"] = [
            {
                "IndexName": g["IndexName"],
                "KeySchema": g["KeySchema"],
                "Projection": g["Projection"],
            }
            for g in gsis
        ]
    return params


def ensure_local_table(table_name: str) -> None:
    a = aws_client()
    l = local_client()
    desc = a.describe_table(TableName=table_name)["Table"]
    params = minimal_create_params(desc)
    try:
        l.create_table(**params)
        # wait for ACTIVE
        for _ in range(60):
            st = l.describe_table(TableName=table_name)["Table"]["TableStatus"]
            if st == "ACTIVE":
                break
            time.sleep(0.5)
        print(f"created: {table_name}")
    except botocore.exceptions.ClientError as e:
        if e.response.get("Error", {}).get("Code") == "ResourceInUseException":
            print(f"exists:  {table_name}")
        else:
            raise


def main() -> None:
    a = aws_client()
    tabs = a.list_tables().get("TableNames", [])
    tabs = [t for t in tabs if t.startswith("tradepulse-")]
    for t in tabs:
        ensure_local_table(t)
    print("done")


if __name__ == "__main__":
    main()


