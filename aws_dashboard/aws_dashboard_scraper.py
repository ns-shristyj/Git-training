
import boto3
import logging
import os          # <-- Needed for os.getenv()
import json        # <-- Needed for json.loads()
# No dotenv import needed
from google.oauth2 import service_account
import googleapiclient.discovery
from collections import defaultdict

# --- Configuration from Environment Variables ---
# Read configuration directly from environment variables set in the YAML
spreadsheet_id = os.getenv('GOOGLE_SPREADSHEET_ID')
sheet_name = os.getenv('GOOGLE_SHEET_NAME')
service_account_json_string = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
aws_region = os.getenv('AWS_REGION', 'us-west-2') # Read region from env, default if not set

# --- Validate Configuration ---
# Ensure critical environment variables are set
if not spreadsheet_id:
    raise ValueError("FATAL: Environment variable 'GOOGLE_SPREADSHEET_ID' is not set.")
if not sheet_name:
    raise ValueError("FATAL: Environment variable 'GOOGLE_SHEET_NAME' is not set.")
if not service_account_json_string:
    raise ValueError("FATAL: Environment variable 'GOOGLE_SERVICE_ACCOUNT_JSON' is not set.")
# Boto3 will implicitly check for AWS creds (AWS_ACCESS_KEY_ID, etc.)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info(f"Script starting. Target Sheet ID: {spreadsheet_id}, Sheet Name: '{sheet_name}', AWS Region: {aws_region}")

# --- Parse Service Account JSON ---
# This block parses the JSON string passed via the environment variable
try:
    service_account_info = json.loads(service_account_json_string)
    logging.info("Successfully parsed service account JSON from environment variable.")
except json.JSONDecodeError as e:
    logging.error(f"Failed to parse GOOGLE_SERVICE_ACCOUNT_JSON: {e}")
    raise ValueError("FATAL: Invalid JSON content in GOOGLE_SERVICE_ACCOUNT_JSON environment variable.") from e

# --- Google Sheets API Setup ---
# This block authenticates using the parsed JSON info
try:
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info, # Pass the dictionary parsed from JSON
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    service = googleapiclient.discovery.build('sheets', 'v4', credentials=credentials)
    logging.info("Successfully authenticated with Google Sheets API using service account info.")
except Exception as e:
    logging.error(f"Failed to authenticate or build Google Sheets service: {e}")
    raise e # Re-raise the exception to fail the GitHub Action job

# --- Google Sheets Helper Functions ---
# These functions now use the global 'service', 'spreadsheet_id', 'sheet_name'

def clearSheet(sheetName=sheet_name, spreadsheetID=spreadsheet_id):
    """ Clears all data from the specified sheet (A:Z range). """
    global service # Ensure using the global service object
    if not service:
        logging.error("Google Sheets service is not available. Cannot clear sheet.")
        return None
    try:
        range_ = f'{sheetName}!A:Z'
        request = service.spreadsheets().values().clear(
            spreadsheetId=spreadsheetID, range=range_, body={})
        response = request.execute()
        logging.info(f"Cleared data from sheet: '{sheetName}'")
        return response
    except Exception as e:
        logging.error(f"Failed to clear sheet '{sheetName}': {e}")
        # Consider raising e in Actions to indicate failure
        return None

def get_column_letter(column_number):
    """ Convert a 1-based column number to a letter (e.g., 1 -> 'A', 27 -> 'AA'). """
    result = ''
    while column_number > 0:
        column_number, remainder = divmod(column_number - 1, 26) # Corrected typo
        result = chr(65 + remainder) + result
    return result

def get_column_from_letter(letter, offset):
    """ Get the column letter by adding the offset to the given letter's number. """
    if not letter or not letter.isalpha():
        logging.error(f"Invalid start column letter provided: '{letter}'")
        return None
    try:
        start_col_num = 0
        for char in letter.upper():
            start_col_num = start_col_num * 26 + (ord(char) - ord('A') + 1)
        target_col_num = start_col_num + offset
        return get_column_letter(target_col_num)
    except Exception as e:
        logging.error(f"Error calculating column letter from letter '{letter}' with offset {offset}: {e}")
        return None

def writeToSheet(data, sheetName=sheet_name, spreadsheetID=spreadsheet_id, startRow=1, startColumn="A"):
    """ Write the data (list of lists) to the specified sheet. """
    global service # Ensure using the global service object
    if not service:
        logging.error("Google Sheets service is not available. Cannot write to sheet.")
        return None
    if not data:
        logging.warning(f"No data provided to write to sheet '{sheetName}'.")
        return None
    try:
        num_rows = len(data)
        num_cols = len(data[0]) if num_rows > 0 else 0
        if num_cols == 0:
            logging.warning(f"Data to write to sheet '{sheetName}' has zero columns.")
            return None

        endColumn = get_column_from_letter(startColumn, num_cols - 1)
        if not endColumn:
            logging.error("Could not determine end column. Aborting write operation.")
            return None

        endRow = startRow + num_rows - 1
        range_ = f"{sheetName}!{startColumn}{startRow}:{endColumn}{endRow}"
        logging.info(f"Preparing to write {num_rows} rows and {num_cols} columns to range: {range_}")

        request = service.spreadsheets().values().update(
            spreadsheetId=spreadsheetID, range=range_, body={'values': data},
            valueInputOption='RAW') # Or 'USER_ENTERED'
        response = request.execute()
        logging.info(f"Successfully wrote data to sheet: '{sheetName}'")
        return response
    except Exception as e:
        logging.error(f"Failed to write data to sheet '{sheetName}': {e}")
        # Consider raising e in Actions to indicate failure
        return None

# --- AWS Security Hub Functions ---
# This uses the AWS credentials automatically found by boto3 from env vars

def get_security_hub_findings():
    """Retrieves current, active findings from Security Hub for specific standards."""
    global aws_region # Use region defined at top
    # Boto3 automatically uses credentials from env vars:
    # AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN (if present)
    client = boto3.client("securityhub", region_name=aws_region)
    findings_list = []

    # Define the standard ARNs you care about (adjust as needed)
    # Note: Ensure these ARNs match the region being queried (aws_region)
    standard_arns = [
        f"arn:aws:securityhub:{aws_region}::standards/cis-aws-foundations-benchmark/v/1.2.0", # Example, adjust version/region
        f"arn:aws:securityhub:{aws_region}::standards/cis-aws-foundations-benchmark/v/3.0.0", # Example, adjust version/region
        f"arn:aws:securityhub:{aws_region}::standards/nist-800-53/v/5.0.0" # Example, adjust version/region
        # You might need to adjust the exact ARN format based on AWS documentation and your specific enabled standards
    ]
    logging.info(f"Filtering for standards: {standard_arns}")

    paginator = client.get_paginator("get_findings")
    filters = {
        "ComplianceStatus": [{"Value": "FAILED", "Comparison": "EQUALS"}],
        "WorkflowStatus": [{"Value": "NEW", "Comparison": "EQUALS"}],
        "RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}],
    }
    logging.info(f"Retrieving findings with filters: {filters}")
    try:
        page_iterator = paginator.paginate(Filters=filters, PaginationConfig={"PageSize": 100})
        relevant_findings_count = 0
        processed_findings = 0
        for page_num, page in enumerate(page_iterator):
            findings_in_page = page.get("Findings", [])
            page_size = len(findings_in_page)
            processed_findings += page_size
            logging.info(f"Processing page {page_num + 1} with {page_size} findings...")
            for finding in findings_in_page:
                # Check if the finding is associated with ANY of the desired standards
                # This check is crucial as the main filter might be broad
                compliance_data = finding.get("Compliance", {})
                associated_standards = compliance_data.get("AssociatedStandards", [])
                is_relevant = False
                if associated_standards: # Check if list exists and is not empty
                     is_relevant = any(std.get("StandardsId") in standard_arns for std in associated_standards)
                else:
                    # Fallback check? Sometimes control ID might be in GeneratorId or ProductFields
                    generator_id = finding.get("GeneratorId", "")
                    # Example check (needs refinement based on your specific standards):
                    # if "cis-aws-foundations-benchmark" in generator_id: is_relevant = True
                    logging.debug(f"Finding {finding.get('Id')} has no 'AssociatedStandards'. GeneratorId: {generator_id}")


                if is_relevant:
                    findings_list.append(finding)
                    relevant_findings_count += 1
                # else:
                    # Optional: Log skipped findings if needed for debugging
                    # logging.debug(f"Skipping finding {finding.get('Id')} as it doesn't match desired standards.")

        logging.info(f"Processed {processed_findings} total findings. Found {relevant_findings_count} relevant findings matching standards.")
    except client.exceptions.InvalidAccessException as e:
         logging.error(f"Security Hub Error: Invalid Access - Check permissions or if Security Hub is enabled in region '{aws_region}'. Details: {e}")
         raise e
    except Exception as e:
        logging.error(f"An error occurred while fetching Security Hub findings: {e}")
        raise e
    return findings_list

def extract_finding_details(finding):
    """Extract relevant details from a Security Hub finding."""
    compliance = finding.get("Compliance", {})
    resources = finding.get("Resources", [{}])
    resource = resources[0] if resources else {}
    severity = finding.get("Severity", {})
    remediation = finding.get("Remediation", {})
    recommendation = remediation.get("Recommendation", {})
    control_id = compliance.get("SecurityControlId", "N/A")
    if control_id == "N/A": # Fallback check
        product_fields = finding.get("ProductFields", {})
        control_id = product_fields.get("ControlId", product_fields.get("RuleId", "N/A"))
    remediation_text = recommendation.get("Text", "N/A")
    remediation_url = recommendation.get("Url", "N/A")
    return {
        "Account ID": finding.get("AwsAccountId", "N/A"),
        "Account Name": finding.get("AwsAccountName", "N/A"), # Often not populated by default
        "Control ID": control_id,
        "Resource Type": resource.get("Type", "N/A"),
        "Resource ID": resource.get("Id", "N/A"),
        "Region": resource.get("Region", finding.get("Region", "N/A")),
        "Severity": severity.get("Label", "N/A"),
        "Title": finding.get("Title", "N/A"),
        "Description": finding.get("Description", "N/A"),
        "First Observed": finding.get("FirstObservedAt", "N/A"),
        "Last Observed": finding.get("LastObservedAt", "N/A"),
        "Remediation": remediation_text,
        "Remediation URL": remediation_url,
        "Finding ID": finding.get("Id", "N/A")
    }

# --- Main Execution ---
if __name__ == "__main__":
    if not service:
         logging.error("Google Sheets service setup failed earlier. Exiting.")
         exit(1) # Exit with non-zero code for Actions failure

    logging.info("Starting Security Hub findings retrieval...")
    findings = get_security_hub_findings()
    # findings list now contains only relevant findings based on standard_arns check

    if findings:
        extracted_data = [extract_finding_details(f) for f in findings]
        logging.info(f"Finished extracting details for {len(extracted_data)} relevant findings.")

        if extracted_data:
            # Define headers in the desired order
            headers = [
                "Account ID", "Account Name", "Control ID", "Resource Type",
                "Resource ID", "Region", "Severity", "Title", "Description",
                "First Observed", "Last Observed", "Remediation",
                "Remediation URL", "Finding ID"
            ]
            sheet_data = [headers] # Start with header row
            for finding_dict in extracted_data:
                # Create row ensuring values align with headers
                row = [str(finding_dict.get(header, "")) for header in headers]
                sheet_data.append(row)

            logging.info("Clearing existing data from Google Sheet...")
            clear_result = clearSheet()
            if clear_result is None:
                 logging.error("Failed to clear sheet. Aborting write.")
                 exit(1) # Exit with non-zero code

            logging.info("Writing new data to Google Sheet...")
            write_result = writeToSheet(sheet_data)
            if write_result is None:
                 logging.error("Failed to write data to sheet.")
                 exit(1) # Exit with non-zero code

            logging.info("Google Sheet update process complete.")
        else:
            # This case might not happen if findings list is not empty, but good to handle
            logging.info("No details could be extracted from the relevant findings.")
            logging.info("Clearing existing data from Google Sheet as no processable findings were found...")
            clear_result = clearSheet()
            if clear_result is None:
                 logging.error("Failed to clear sheet.")
                 exit(1) # Exit with non-zero code

    else:
        # This means get_security_hub_findings() returned an empty list
        logging.info("No relevant findings retrieved based on specified standards. Clearing Google Sheet.")
        clear_result = clearSheet()
        if clear_result is None:
             logging.error("Failed to clear sheet.")
             exit(1) # Exit with non-zero code
        logging.info("Google Sheet cleared as no relevant findings were retrieved.")

    logging.info("Script finished.")
