# Technical Documentation: Conversor de Planilha para Salesforce

## 1. Application Overview

The Conversor de Planilha para Salesforce is a Flask-based web application that transforms CSV, Excel and TXT files into leads in Salesforce. The application handles file uploads, data transformation, and direct integration with Salesforce's API to create leads with proper mapping and validation.

## 2. System Architecture

### 2.1 Core Components

1. **Web Interface (Flask)**: Provides the upload form and feedback on conversion process
2. **Data Processing Engine**: Transforms uploaded files to Salesforce-compatible format
3. **Salesforce API Integration**: Authenticates and communicates with Salesforce API
4. **Error Handling System**: Logs and reports issues at each step

### 2.2 Directory Structure

```text
conversor_planilha/
├── A converter/             # Directory for storing files to be processed
├── logs/                    # Application logs
├── scripts/                 # Processing scripts
├── src/                     # Core application code
│   ├── services/            # Salesforce API services
│   └── utils/               # Utility functions and helpers
├── static/                  # Web assets (CSS, JS)
├── templates/               # HTML templates
└── app.py                   # Main Flask application
```

## 3. Salesforce Integration

### 3.1 Authentication Process

The application uses OAuth 2.0 to authenticate with Salesforce. Authentication is handled by the `salesforce_auth.py` module, which:

1. Reads credentials from environment variables
2. Makes an OAuth 2.0 request to Salesforce
3. Obtains an access token
4. Caches token for reuse during the session
5. Handles token refresh when expired

```python
# Key environment variables required:
# SALESFORCE_CLIENT_ID
# SALESFORCE_CLIENT_SECRET
# SALESFORCE_USERNAME
# SALESFORCE_PASSWORD
# SALESFORCE_SECURITY_TOKEN
```

### 3.2 API Version

The application uses Salesforce API version 63.0 (configured in app.py):

```python
os.environ['SALESFORCE_API_VERSION'] = '63.0'
```

### 3.3 Environment Selection

The application supports both Sandbox and Production environments, configurable through the UI. The environment selection affects:

1. Authentication endpoints
2. API endpoints
3. Logging context

## 4. Data Processing Flow

### 4.1 File Upload Process

1. User uploads CSV, XLS, or XLSX file and selects environment
2. File is validated for format and saved to temporary location
3. File extension determines processing route:
   - CSV: Direct processing
   - XLS/XLSX: Conversion to CSV before processing

### 4.2 Data Transformation

1. The application applies multiple transformation steps:
   - Column remapping to match Salesforce field names
   - Data cleaning (phone numbers, email addresses)
   - Validation of required fields
   - Format correction (name capitalization, etc.)

2. AI mapping assistance:
   - When field mapping isn't obvious, the application uses AI to suggest mappings
   - AI mapping logic is in `llm.py` using OpenAI API

### 4.3 Salesforce Lead Creation

1. Processed data is sent to Salesforce in batches
2. Each lead creation is tracked and logged
3. Errors are handled and reported back to the user
4. Retry mechanisms handle temporary API issues

### 4.4 Results Processing and Display

1. The application processes results from Salesforce API calls:
   - Success/failure status is tracked for each lead
   - Result statistics are aggregated (total, successful, failed)
   - A detailed list of failures with error messages is maintained

2. Results handling includes special cases:
   - When the API returns `success=true` but no individual leads show success, the system adjusts counts for consistency
   - Frontend includes mechanisms to correct display issues via JavaScript
   - Session data is preserved to show results on redirect

3. User feedback components:
   - Visual indicators (icons, colors) for success/failure status
   - Detailed statistics on processed leads
   - List of failed leads with error messages
   - JavaScript-based corrections for inconsistent states

## 5. Critical Functions and Files

### 5.1 Key Files

1. **`app.py`**: Main application and route handlers
2. **`src/services/salesforce_api.py`**: Core Salesforce API integration
3. **`src/services/salesforce_auth.py`**: Authentication with Salesforce
4. **`src/utils/csv_helper.py`**: CSV processing utilities
5. **`scripts/process_new_leads.py`**: Lead transformation logic
6. **`static/js/resultado_fix.js`**: Ensures consistent display of results page
7. **`static/js/salesforce_result_fix.js`**: Corrects inconsistencies in Salesforce results display
8. **`static/css/resultado_success_fix.css`**: Styling for result page success/error states

### 5.2 Critical Functions

1. **`create_lead_in_salesforce()`**: Creates a single lead in Salesforce
2. **`create_leads_from_csv()`**: Processes a CSV file and creates multiple leads
3. **`get_salesforce_access_token()`**: Handles authentication with Salesforce
4. **`fix_salesforce_lead_csv()`**: Ensures CSV data meets Salesforce requirements
5. **`resultado()`**: Reconstructs and displays processing results from session data

## 6. Lead Owner Assignment

The application supports three methods for assigning lead ownership:

1. **Automatic Assignment**: Uses Salesforce's lead assignment rules (default)
2. **Custom Owner ID**: Allows specifying a direct Owner ID for all leads created
3. **Assignment Rules**: If no owner is specified, Salesforce uses its default assignment rules

Owner IDs must be valid 15 or 18-character Salesforce IDs starting with "00".

## 7. Important Notes and Limitations

### 7.1 Salesforce Field Compatibility

- The Lead object in Salesforce does not have a Description field
- Custom fields must be referenced with __c suffix (e.g., `CPF__c`)
- Required fields (LastName, Company) are filled with default values if missing

### 7.2 API Limits

Salesforce enforces API limits that may affect bulk operations:

- Daily API call limits depend on your Salesforce edition
- Batch size limits affect how many leads can be created in one request

### 7.3 File Size Limits

- Maximum file upload size: 16MB
- Recommended maximum records per file: 2000 (for reliable processing)

## 8. Troubleshooting Common Issues

### 8.1 Authentication Failures

If authentication fails:

1. Verify environment variables are set correctly
2. Check Salesforce user permissions
3. Verify security token is current
4. Check network connectivity to Salesforce endpoints

### 8.2 Field Errors

If field errors occur:

1. Verify field mappings match your Salesforce organization's fields
2. Check for custom field naming (should include __c suffix)
3. Ensure required fields are populated
4. Verify field data types match Salesforce expectations

### 8.3 Owner ID Issues

If lead assignment errors occur:

1. Use automatic assignment instead of custom Owner IDs
2. Verify the Owner ID exists in your Salesforce org
3. Check that the owner has permission to own leads
4. Verify ID format (15 or 18 characters, starts with "00")

### 8.4 Result Display Issues

If result page shows incorrect status or lead counts:

1. Check for session expiration (results data may be lost)
2. Verify browser JavaScript is enabled (required for display corrections)
3. If "Nenhum processamento encontrado" appears, try:
   - Clearing browser cache and cookies
   - Checking server logs to confirm data was properly saved to session
   - Verifying that `salesforce_results` is being properly saved in the session
4. For inconsistent success/failure indicators:
   - The application includes self-correction mechanisms in JavaScript
   - Check browser console for any JavaScript errors

## 9. Configuration and Environment Variables

The application requires these environment variables:

```env
SALESFORCE_CLIENT_ID=your_client_id
SALESFORCE_CLIENT_SECRET=your_client_secret
SALESFORCE_USERNAME=your_username
SALESFORCE_PASSWORD=your_password
SALESFORCE_SECURITY_TOKEN=your_security_token
SALESFORCE_API_VERSION=63.0
SALESFORCE_SANDBOX_URL=https://test.salesforce.com
SALESFORCE_PRODUCTION_URL=https://login.salesforce.com
OPENAI_ROUTER_API_KEY=your_openai_key (optional, for AI mapping assistance)
```

## 10. Recovery and Rollback Procedures

In case of critical issues, follow these recovery steps:

1. **Configuration Rollback**: Keep backup of .env file for quick restoration
2. **Code Rollback**: The application is version controlled; revert to last stable commit
3. **Dependency Isolation**: The application uses requirements.txt to pin dependencies
4. **Data Protection**: Uploaded files are preserved in the A converter directory

## 11. Results Handling Mechanism

The application employs a sophisticated multi-layer approach to handle Salesforce processing results:

### 11.1 Backend Result Processing

1. **Initial Result Processing**:
   - Salesforce API returns a tuple of `(success, message_or_results)`
   - Success is a boolean indicating if the overall operation succeeded
   - `message_or_results` contains either an error message (string) or a list of results (one per lead)

2. **Statistical Analysis**:
   - The app calculates:
     - Number of successful leads: `num_success = sum(1 for r in message_or_results if r.get('success', False))`
     - Number of failed leads: `num_errors = len(message_or_results) - num_success`

3. **Inconsistency Handling**:
   - The app detects and corrects inconsistent states:
   - When `success=True` but `num_success=0`, it adjusts count to `num_success=1`
   - This ensures UI display consistency when Salesforce reports general success but no individual leads show success

4. **Session Storage**:
   - Two key objects are stored in the session:
     - `salesforce_results`: Raw results from Salesforce API
     - `result`: Formatted data for UI display with statistics

### 11.2 Frontend Result Handling

1. **Result Page Logic** (`/resultado` route):
   - First attempts to load `result` from session
   - If not found, tries to reconstruct from `salesforce_results`
   - Considers processing successful if any data was received from Salesforce

2. **JavaScript Corrections**:
   - `resultado_fix.js`: Basic display corrections and event handling
   - `salesforce_result_fix.js`: Advanced detection and fixes for UI inconsistencies
   - Both scripts work together to ensure the user sees the correct status

3. **CSS Enhancements**:
   - `resultado_success_fix.css`: Ensures visibility of messages and provides visual cues
   - Uses animations and color-coding to indicate processing status

This multi-layered approach ensures that users receive accurate feedback about their lead imports, even in cases where API responses contain inconsistencies or edge cases.
