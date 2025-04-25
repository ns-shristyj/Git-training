import boto3
import logging
import os
from google.oauth2 import service_account
import googleapiclient.discovery
# Remove defaultdict if not used elsewhere: from collections import defaultdict

# --- [ Previous code remains unchanged: Keyfile path, Spreadsheet details, Logging, Google API Setup, Helper Functions ] ---
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
service = None # Initialize service to None
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
    # Depending on requirements, you might want to exit here if service fails
    # exit(1)

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

# *** Function Definition for extract_finding_details needs to be before get_security_hub_findings ***
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
         # Check common alternative field names like 'ControlId' or 'RuleId' (specific to some providers like Prowler)
         control_id = product_fields.get("ControlId", product_fields.get("RuleId", "N/A"))

    # Remediation details
    remediation_text = recommendation.get("Text", "N/A")
    remediation_url = recommendation.get("Url", "N/A")

    # Get Account Name (try 'AwsAccountName' first, fallback to lookup if needed - requires extra permissions)
    # For simplicity, we'll just use the provided field if available.
    account_name = finding.get("AwsAccountName", "N/A") # Added Account Name extraction


    return [finding.get("AwsAccountId", "N/A"),
            account_name, # Use the extracted account name
            control_id,
            resource.get("Type", "N/A"),
            resource.get("Id", "N/A"),
            resource.get("Region", finding.get("Region", "N/A")), # Use resource region first, then finding region
            severity.get("Label", "N/A"),
            finding.get("Title", "N/A"),
            finding.get("Description", "N/A"),
            finding.get("FirstObservedAt", "N/A"),
            finding.get("LastObservedAt", "N/A"),
            remediation_text,
            remediation_url,
            finding.get("Id", "N/A") # Finding ID itself
           ]


def get_security_hub_findings():
    """Retrieves current, active findings from Security Hub for specific standards, ensuring uniqueness."""
    # *** REPLACE "us-west-2" with your target AWS region if different ***
    client = boto3.client("securityhub", region_name="us-west-2")
    unique_findings_list = []
    seen_combinations = set() # Keep track of unique combinations encountered

    # Specify the standards you are interested in
    standard_ids = [
        "standards/cis-aws-foundations-benchmark/v/3.0.0",
        "standards/nist-800-53/v/5.0.0"
    ]
    paginator = client.get_paginator("get_findings")

    # Define filters
    filters = {
        # Use ComplianceAssociatedStandardsId for filtering by standard subscription ARN
        "ComplianceAssociatedStandardsId": [{"Value": f"arn:aws:securityhub:{client.meta.region_name}::standards/{std_path}", "Comparison": "PREFIX"} for std_path in standard_ids],
        "ComplianceStatus": [{"Value": "FAILED", "Comparison": "EQUALS"}],
        "WorkflowStatus": [{"Value": "NEW", "Comparison": "EQUALS"}, {"Value": "NOTIFIED", "Comparison": "EQUALS"}], # Adjusted to include NOTIFIED as well
        "RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}],
    }

    logging.info(f"Retrieving findings with filters: {filters}")

    try:
        for page in paginator.paginate(Filters=filters, PaginationConfig={"PageSize": 100}):
            for finding in page["Findings"]:
                result = extract_finding_details(finding) # Extract details first

                # Create a tuple of the elements that define uniqueness
                # Indices: 0=AccountID, 2=ControlID, 4=ResourceID, 5=ResourceRegion,
                #          9=FirstObserved, 10=LastObserved
                # Consider if First/Last Observed should truly define uniqueness.
                # If not, remove result[9] and result[10] from the tuple.
                unique_key = (
                    result[0],  # Account ID
                    result[2],  # Control ID
                    result[4],  # Resource ID
                    result[5],  # Resource Region
                    result[9],  # First Observed At
                    result[10] # Last Observed At
                )

                # Check if this combination has been seen before
                if unique_key not in seen_combinations:
                    # If not seen, add the full result to our list
                    unique_findings_list.append(result)
                    # And add the unique key to the set to mark it as seen
                    seen_combinations.add(unique_key)
                # else: # Optional: Log if a duplicate was skipped
                #    logging.debug(f"Skipping duplicate finding for key: {unique_key}")


    except client.exceptions.InvalidAccessException as e:
         logging.error(f"Security Hub Error: Invalid Access - Check permissions or if Security Hub is enabled in region. Details: {e}")
         # Optionally re-raise or exit
         raise e # Re-raising to stop execution if permissions are wrong
    except Exception as e:
        logging.error(f"An error occurred while fetching Security Hub findings: {e}")
        # Optionally re-raise or exit
        raise e # Re-raising to stop execution on other errors

    logging.info(f"Collected {len(unique_findings_list)} unique findings after processing.")
    return unique_findings_list

# --- Main Execution ---

if __name__ == "__main__":

    if not service:
        logging.error("Google Sheets service setup failed. Exiting.")
    elif not spreadsheet_id or not sheet_name:
         logging.error("Spreadsheet ID or Sheet Name is not configured in the script. Exiting.")
    else:
        logging.info("Starting Security Hub findings retrieval...")
        # This will now contain the de-duplicated list
        findings = get_security_hub_findings()
        logging.info(f"Retrieved {len(findings)} unique findings.")

        # Proceed only if findings were retrieved successfully
        if findings is not None: # Check if findings list is valid (not None in case of early error return)
            headers = ["Account ID","Account Name", "Control ID", "Resource Type", "Resource ID", "Region", "Severity", "Title",
                       "Description", "First Observed", "Last Observed", "Remediation", "Remediation URL", "Finding ID"]

            # Prepare data for sheet: Add headers only if there are findings
            data_to_write = []
            if findings: # Check if the list is not empty
                 data_to_write = [headers] + findings
            else:
                 data_to_write = [headers] # Write only headers if no findings found
                 logging.info("No unique findings found matching the criteria.")


            # Clear the sheet before writing
            clear_response = clearSheet(sheet_name, spreadsheet_id)

            if clear_response is not None: # Proceed only if clearing was successful
                 # Write the unique findings (with headers) to the sheet
                 writeToSheet(sheet_name, data_to_write, spreadsheet_id)
            else:
                 logging.error("Aborting write operation because clearing the sheet failed.")
        else:
             logging.error("Could not retrieve findings. Aborting write operation.")
