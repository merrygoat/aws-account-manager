import boto3
import nicegui.ui as ui

from aam.config import CONFIG


def get_organization_accounts(org_id: str, include_suspended: bool = True) -> list[dict]:
    """Get a list of accounts in the organization."""

    org_role_arns = CONFIG["organization_list_role_arns"]
    if org_id not in org_role_arns:
        ui.notify("Selected organization id not found in 'organization_list_role_arns' section in config.yaml")
        return 0

    sts_connection = boto3.client('sts')
    acct_b = sts_connection.assume_role(
        RoleArn=org_role_arns[org_id],
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
