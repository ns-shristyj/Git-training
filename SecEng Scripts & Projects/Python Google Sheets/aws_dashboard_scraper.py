""" 
    This script will scrape security info from the 'audit' account console and create a csv file of the findings.
    NOTE: Specify the target AWS region below where client is declared (line 18)
    Author: Woodrow Davidson
"""

import boto3
import logging
import csv
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_security_hub_findings():
    """Retrieves current, active findings from Security Hub with added logging."""
    
    client = boto3.client("securityhub", region_name="us-west-2")
    findings_list = []
    
    standard_ids = [
        "standards/cis-aws-foundations-benchmark/v/3.0.0",
        "standards/nist-800-53/v/5.0.0"
    ]

    paginator = client.get_paginator("get_findings")
    
    filters = {
        "ComplianceAssociatedStandardsId": [{"Value": standard_id, "Comparison": "EQUALS"} for standard_id in standard_ids],
        "ComplianceStatus": [{"Value": "FAILED", "Comparison": "EQUALS"}],
        "WorkflowStatus": [{"Value": "NEW", "Comparison": "EQUALS"}, {"Value": "IN_PROGRESS", "Comparison": "EQUALS"}],
        "RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}],
    } 
    
    for page in paginator.paginate(Filters=filters, PaginationConfig={"PageSize": 100}):
        for finding in page["Findings"]:
            findings_list.append(finding)
    return findings_list


def extract_finding_details(finding):
    """Extract relevant details from a Security Hub finding."""
    
    account_id = finding.get("AwsAccountId", "N/A")
    account_name = finding.get("AwsAccountName", "N/A")
    control_id = finding.get("Compliance", {}).get("SecurityControlId", "N/A")
    resource_type = finding.get("Resources", [{}])[0].get("Type", "N/A")
    resource_id = finding.get("Resources", [{}])[0].get("Id", "N/A")
    severity_label = finding.get("Severity", {}).get("Label", "N/A")
    title = finding.get("Title", "N/A")
    description = finding.get("Description", "N/A")
    first_observed = finding.get("CreatedAt", "N/A")
    last_observed = finding.get("UpdatedAt", "N/A")
    remediation_recommendation = finding.get("Remediation", {}).get("Recommendation", {}).get("Text", "N/A")
    remediation_url = finding.get("Remediation", {}).get("Recommendation", {}).get("Url", "N/A")
    return {
        "Account ID": account_id,
        "Account Name": account_name,
        "Control ID": control_id,
        "Resource Type": resource_type,
        "Resource ID": resource_id,
        "Severity": severity_label,
        "Title": title,
        "Description": description,
        "First Observed": first_observed,
        "Last Observed": last_observed,
        "Remediation": remediation_recommendation,
        "Remediation URL": remediation_url,
    }

def export_to_csv(findings_list, filename="security_hub_report.csv"):
    """Export list of dictionaries to CSV."""
    
    if not findings_list:
        logging.info("No data to export.")
        return
    keys = findings_list[0].keys()
    with open(filename, mode="w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=keys)
        writer.writeheader()
        writer.writerows(findings_list)
    logging.info(f"CSV report saved as {filename}")

if __name__ == "__main__":
    logging.info("Starting Security Hub findings retrieval...")
    findings = get_security_hub_findings()
    logging.info(f"Retrieved {len(findings)} findings.")

    extracted_data = []
    for finding in findings:
        details = extract_finding_details(finding)
        extracted_data.append(details)

    logging.info("Finished extracting details. Exporting to CSV...")
    export_to_csv(extracted_data)
    logging.info("CSV export complete.")
