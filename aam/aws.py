import os

import boto3

from aam.config import CONFIG


def get_accounts(sso_profile_name: str) -> list[dict]:
    session = boto3.Session(profile_name=sso_profile_name)
    return get_organisation_accounts()


def get_organisation_accounts(include_suspended: bool = True) -> list[dict]:
    """Get a list of accounts in the organization."""
    a = os.environ

    sts_connection = boto3.client('sts')
    acct_b = sts_connection.assume_role(
        RoleArn=CONFIG["organization_list_role_arn"],
        RoleSessionName="aam_cross_acct_describe_org"
    )

    # create service client using the assumed role credentials, e.g. S3
    org_client = boto3.client('organizations',
        aws_access_key_id=acct_b['Credentials']['AccessKeyId'],
        aws_secret_access_key=acct_b['Credentials']['SecretAccessKey'],
        aws_session_token=acct_b['Credentials']['SessionToken'],
    )

    response = org_client.list_accounts()
    accounts = response["Accounts"]
    while "NextToken" in response:
        response = org_client.list_accounts(NextToken=response["NextToken"])
        accounts.extend(response["Accounts"])
    if not include_suspended:
        accounts = [account for account in accounts if account["Status"] != "SUSPENDED"]
    return accounts
