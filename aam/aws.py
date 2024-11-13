from typing import Type

import boto3
import botocore.client


def get_accounts(sso_profile_name: str) -> list[dict]:
    session = boto3.Session(profile_name=sso_profile_name)
    org_client = session.client("organizations")
    return get_organisation_accounts(org_client)


def get_organisation_accounts(org_client: Type[botocore.client.BaseClient],
                              include_suspended: bool = True) -> list[dict]:
    """Get a list of accounts in the organization."""
    response = org_client.list_accounts()
    accounts = response["Accounts"]
    while "NextToken" in response:
        response = org_client.list_accounts(NextToken=response["NextToken"])
        accounts.extend(response["Accounts"])
    if not include_suspended:
        accounts = [account for account in accounts if account["Status"] != "SUSPENDED"]
    return accounts
