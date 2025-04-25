""" 
    This script retrieves specific failed, active findings from AWS Security Hub 
    (CIS 3.0.0 and NIST 800-53 v5 standards) in a specified region, 
    extracts relevant details, and writes the data to a specified Google Sheet.
    NOTE: Specify the target AWS region below where the securityhub client is declared (line ~56)
    Author: Bradley Chavis & Woodrow Davidson, Integration by AI Assistant
"""
import boto3
import logging
import os
from google.oauth2 import service_account
import googleapiclient.discovery
from collections import defaultdict # Keep defaultdict if needed elsewhere, otherwise remove if unused.

# Path to the downloaded JSON key file from environment variable
keyfile_path = os.getenv('FILE_PATH')
if not keyfile_path:
    raise ValueError("Environment variable 'FILE_PATH' not set. Please create a .env file.")
if not os.path.exists(keyfile_path):
     raise FileNotFoundError(f"Service account key file not found at: {keyfile_path}")

# The ID of the spreadsheet
spreadsheet_id = '1uvC8izOY3z-E7skDw3kjkRPOgdwRT76ZFNNbmdQjWXo' 
# The name of the tab within the spreadsheet
sheet_name = 'Sheet1' 

if not spreadsheet_id or not sheet_name:
    print("WARNING: 'spreadsheet_id' or 'sheet_name' is not set. Please edit the script.")

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Google Sheets API Setup ---
try:
    credentials = service_account.Credentials.from_service_account_file(
        keyfile_path,
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    # Create a Google Sheets API service
    service = googleapiclient.discovery.build('sheets', 'v4', credentials=credentials)
    logging.info("Successfully authenticated with Google Sheets API.")
except Exception as e:
    logging.error(f"Failed to authenticate or build Google Sheets service: {e}")

# --- Google Sheets Helper Functions ---
def clearSheet(sheetName, spreadsheetID):
    """ Clears all data from the specified sheet (A:Z range). """
    if not service:
        logging.error("Google Sheets service is not available. Cannot clear sheet.")
        return None
    try:
        range_ = f'{sheetName}!A:Z' # Clear columns A through Z
        request = service.spreadsheets().values().clear(
            spreadsheetId=spreadsheetID,
            range=range_,
            body={}
        )
        response = request.execute()
        logging.info(f"Cleared data from sheet: '{sheetName}' in spreadsheet ID: {spreadsheetID}")
        return response
    except Exception as e:
        logging.error(f"Failed to clear sheet '{sheetName}': {e}")
        return None

def get_column_letter(column_number):
    """ Convert a 1-based column number to a letter (e.g., 1 -> 'A', 27 -> 'AA'). """
    result = ''
    while column_number > 0:
        column_number, remainder = divmod(column_number - 1, 26)
        result = chr(65 + remainder) + result
    return result

def get_column_from_letter(letter, offset):
     """ Get the column letter by adding the offset to the given letter's number. """
     # Ensure letter is valid before proceeding
     if not letter or not letter.isalpha():
         logging.error(f"Invalid start column letter provided: '{letter}'")
         return None # Or raise an error
     try:
         # Convert start letter to its 1-based column number
         start_col_num = 0
         for char in letter.upper():
             start_col_num = start_col_num * 26 + (ord(char) - ord('A') + 1)
         
         # Calculate the target column number
         target_col_num = start_col_num + offset
         
         return get_column_letter(target_col_num)
     except Exception as e:
         logging.error(f"Error calculating column letter from letter '{letter}' with offset {offset}: {e}")
         return None

def writeToSheet(sheetName, data, spreadsheetID, startRow=1, startColumn="A"):
    """ Write the data (list of lists) to the specified sheet. """
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

        # Calculate the end column letter
        # Offset is num_cols - 1 because if start is A and there's 1 col, end is A (offset 0)
        # If start is A and there are 2 cols, end is B (offset 1)
        endColumn = get_column_from_letter(startColumn, num_cols - 1)
        if not endColumn: # Handle error from get_column_from_letter
             logging.error("Could not determine end column. Aborting write operation.")
             return None
             
        endRow = startRow + num_rows - 1 # End row is start row + number of rows - 1

        range_ = f"{sheetName}!{startColumn}{startRow}:{endColumn}{endRow}"
        logging.info(f"Preparing to write {num_rows} rows and {num_cols} columns to range: {range_}")

        # Update values in the spreadsheet
        request = service.spreadsheets().values().update(
            spreadsheetId=spreadsheetID,
            range=range_,
            body={'values': data},
            valueInputOption='RAW' # Use 'USER_ENTERED' if you need Sheets to parse formulas/dates etc.
        )
        response = request.execute()
        logging.info(f"Successfully wrote data to sheet: '{sheetName}'")
        return response
    except Exception as e:
        logging.error(f"Failed to write data to sheet '{sheetName}': {e}")
        return None

# --- AWS Security Hub Functions ---
def get_security_hub_findings():
    """Retrieves current, active findings from Security Hub for specific standards."""
    # *** REPLACE "us-west-2" with your target AWS region if different ***
    client = boto3.client("securityhub", region_name="us-west-2") 
    findings_list = []
    
    # Specify the standards you are interested in
    standard_ids = [
        "standards/cis-aws-foundations-benchmark/v/3.0.0",
        "standards/nist-800-53/v/5.0.0"
    ]
    paginator = client.get_paginator("get_findings")
    
    # Create filters based on the Compliance.AssociatedStandards.StandardsId field
    filters = {
        "ComplianceAssociatedStandardsId": [{"Value": standard_id, "Comparison": "EQUALS"} for standard_id in standard_ids],
        "ComplianceStatus": [{"Value": "FAILED", "Comparison": "EQUALS"}],
        "WorkflowStatus": [{"Value": "NEW", "Comparison": "EQUALS"}, {"Value": "IN_PROGRESS", "Comparison": "EQUALS"}],
        "RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}],
    }
    
    logging.info(f"Retrieving findings with filters: {filters}")
    
    try:
        for page in paginator.paginate(Filters=filters, PaginationConfig={"PageSize": 100}):
            for finding in page["Findings"]:
                result = extract_finding_details(finding)
                findings_list.append(result)

            
    except client.exceptions.InvalidAccessException as e:
         logging.error(f"Security Hub Error: Invalid Access - Check permissions or if Security Hub is enabled in region. Details: {e}")
         # Optionally re-raise or exit
         raise e
    except Exception as e:
        logging.error(f"An error occurred while fetching Security Hub findings: {e}")
        # Optionally re-raise or exit
        raise e
        
    return findings_list
'''
def detectDup(findings_list, currentFinding):
    for finding in findings_list:
        if  currentFinding[0] == finding[0] and 
            currentFinding[2] == finding[2] and 
            currentFinding[4] == finding[4] and
            currentFinding[5] == finding[5] and
            currentFinding[9] == finding[9] and
            currentFinding[10] == finding[10]:
            return True
    return False

for finding in page['FINDINGS']:
    result = func() # Call your function to get the finding details

    # Check if the result is NOT a duplicate before appending
    if not detectDup(findings_list, result):
        findings_list.append(result)
'''


def extract_finding_details(finding):
    """Extract relevant details from a Security Hub finding."""
    
    # Safely get nested values using .get() with default values
    compliance = finding.get("Compliance", {})
    resources = finding.get("Resources", [{}]) # Handle cases where Resources might be missing/empty
    resource = resources[0] if resources else {}
    severity = finding.get("Severity", {})
    remediation = finding.get("Remediation", {})
    recommendation = remediation.get("Recommendation", {})

    # Extract Compliance related fields, including SecurityControlId if available
    control_id = compliance.get("SecurityControlId", "N/A")
    # Sometimes the standard/control is nested differently, check ProductFields as a fallback
    if control_id == "N/A":
         product_fields = finding.get("ProductFields", {})
         control_id = product_fields.get("ControlId", product_fields.get("RuleId", "N/A")) # Check common alternative field names
    # Remediation details
    remediation_text = recommendation.get("Text", "N/A")
    remediation_url = recommendation.get("Url", "N/A")
    return [finding.get("AwsAccountId", "N/A"),
            finding.get("AwsAccountName", "N/A"),
            control_id,
            resource.get("Type", "N/A"),
            resource.get("Id", "N/A"),
            resource.get("Region", finding.get("Region", "N/A")),
            severity.get("Label", "N/A"),
            finding.get("Title", "N/A"),
            finding.get("Description", "N/A"),
            finding.get("FirstObservedAt", "N/A"),
            finding.get("LastObservedAt", "N/A"),
            remediation_text,
            remediation_url,
            finding.get("Id", "N/A")
           ]

# --- Main Execution ---

if __name__ == "__main__":
    
    if not service:
        logging.error("Google Sheets service setup failed. Exiting.")
    elif not spreadsheet_id or not sheet_name:
         logging.error("Spreadsheet ID or Sheet Name is not configured in the script. Exiting.")
    else:
        logging.info("Starting Security Hub findings retrieval...")
        findings = get_security_hub_findings()
        logging.info(f"Retrieved {len(findings)} findings.")

        headers = ["Account ID","Account Name", "Control ID", "Resource Type", "Resource ID", "Region", "Severity", "Title",
                 "Description", "First Observed", "Last Observed", "Remediation", "Remediation URL", "Finding ID"]
        findings.insert(0, headers)
        
        clearSheet(sheet_name, spreadsheet_id)

        writeToSheet(sheet_name, findings, spreadsheet_id)
