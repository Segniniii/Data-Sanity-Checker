# Standard library imports
import io
import json
import logging
import os
from typing import List, Optional

# Third-party imports
import numpy as np
import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# --- Logging Configuration ---
# Configures the basic logging for the application.
# Level: INFO means informational messages, warnings, and errors will be logged.
# Format: Defines how log messages will appear (timestamp - logger name - level - message).
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__) # Creates a logger instance for this module (main.py)

# --- Application Configuration (using Environment Variables) ---
# Environment variables allow configuring the application without changing the code,
# which is essential for different deployment environments (development, testing, production).
# In a production environment, these variables should be set explicitly (e.g., in Docker compose, Kubernetes, or hosting provider settings).

# Allowed CORS origins:
# "*" allows all origins (useful for development, but INSECURE for production).
# For production, replace "*" with specific domains: e.g., "https://yourfrontend.com,https://anotherdomain.com"
ALLOWED_ORIGINS_STR = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = [o.strip() for o in ALLOWED_ORIGINS_STR.split(',')]
if "*" in ALLOWED_ORIGINS:
    logger.warning("CORS 'allow_origins' is set to '*', which is insecure for production. Please configure specific origins.")

# Data Quality Check Thresholds:
# Percentage of missing values in a column to trigger a 'Missing Data' alert.
MISSING_VALUE_THRESHOLD = float(os.getenv("MISSING_VALUE_THRESHOLD", "5.0")) # Default: 5%

# Bias Check Thresholds (for Imbalance and Disparity):
# If one value makes up >90% of data in a sensitive attribute, it's considered dominant.
DOMINANT_IMBALANCE_THRESHOLD = float(os.getenv("DOMINANT_IMBALANCE_THRESHOLD", "90.0")) # Default: 90%
# If one value makes up <10% of data in a sensitive attribute (and there are other values), it's considered rare.
RARE_IMBALANCE_THRESHOLD = float(os.getenv("RARE_IMBALANCE_THRESHOLD", "10.0")) # Default: 10%
# Percentage point difference in outcome averages between groups to trigger a 'Disparity' alert.
DISPARITY_THRESHOLD = float(os.getenv("DISPARITY_THRESHOLD", "20.0")) # Default: 20%
# Disparate Impact Ratio threshold (commonly known as the "80% rule").
# If DIR is below this, it indicates potential adverse impact.
DIR_THRESHOLD = float(os.getenv("DIR_THRESHOLD", "0.8")) # Default: 0.8 (80%)

# --- FastAPI Application Initialization ---
app = FastAPI(
    title="Data Sanity Checker API", # Title for API docs (e.g., /docs)
    description="API for uploading tabular data to perform quality and bias checks.",
    version="0.1.0"
)

# --- CORS Middleware Configuration ---
# Cross-Origin Resource Sharing (CORS) allows web browsers to make requests
# from a different domain (the frontend) to this API domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # List of allowed origins (controlled by env var)
    allow_credentials=True,         # Allow cookies, authorization headers etc.
    allow_methods=["*"],            # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],            # Allow all request headers
)

# --- Static Files Serving ---
# Calculates the absolute path to the 'Frontend' directory.
# This ensures that HTML, CSS, and JS files are served correctly regardless of where the app is run.
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Frontend'))
logger.info(f"Serving static files from: {frontend_dir}")

# Mounts the 'Frontend' directory to be served as static files under the "/static" URL path.
# E.g., Frontend/style.css will be accessible at /static/style.css.
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/", response_class=HTMLResponse, summary="Serve the main frontend application")
async def read_root():
    """
    Serves the main HTML page (`index.html`) from the Frontend directory.
    This is the default endpoint for the web application, serving the UI.
    """
    index_path = os.path.join(frontend_dir, "index.html")
    logger.info(f"Attempting to serve: {index_path}")
    # Checks if index.html exists to prevent a FileNotFoundError.
    if not os.path.exists(index_path):
        logger.error(f"index.html not found at {index_path}. Please ensure Frontend directory is correctly structured.")
        raise HTTPException(status_code=404, detail="Frontend HTML file not found. Check server configuration.")
    # Reads and returns the HTML content.
    with open(index_path, "r") as f:
        return HTMLResponse(content=f.read())

@app.post("/analyze-data/", summary="Analyze uploaded data for quality and bias")
async def analyze_data(
    file: UploadFile = File(..., description="The tabular data file (CSV or Excel) to analyze."),
    sensitive_attributes: Optional[str] = Form(None, description="JSON string of sensitive column names (e.g., '[\"gender\", \"ethnicity\"]'). Used for bias checks."),
    outcome_column: Optional[str] = Form(None, description="Name of the outcome/target column. Used for bias disparity and impact checks."),
    favorable_outcome_value: Optional[str] = Form(None, description="Value in the outcome column representing a 'favorable' result (e.g., 'Approved', '1', 'True'). Required for Disparate Impact Ratio."),
    privileged_group_value: Optional[str] = Form(None, description="Value in sensitive attribute columns representing the 'privileged' group (e.g., 'Male', 'White'). Required for Disparate Impact Ratio.")
):
    """
    Receives an uploaded dataset (CSV or Excel), performs comprehensive data quality checks,
    and identifies potential biases related to specified sensitive attributes and an outcome column.
    
    A structured JSON report detailing findings, including missing values, duplicates,
    column statistics, and bias flags (Imbalance, Disparity, Disparate Impact Ratio), is returned.
    """
    logger.debug(f"Received file: '{file.filename}'")
    logger.debug(f"Sensitive attributes (raw): '{sensitive_attributes}'")
    logger.debug(f"Outcome column (raw): '{outcome_column}'")
    logger.debug(f"Favorable outcome value (raw): '{favorable_outcome_value}'")
    logger.debug(f"Privileged group value (raw): '{privileged_group_value}'")
    
    # Initialize the report structure. This ensures a consistent response format,
    # and prevents issues if certain checks are skipped or encounter errors.
    report = {
        "message": f"File '{file.filename}' processed successfully! Initiating quality and bias checks.",
        "file_details": {},
        "summary_alerts": [], # High-level alerts for critical issues
        "quality_checks": {
            "missing_values": {},
            "duplicate_rows": 0,
            "column_data_types": {},
            "column_statistics": {},
            "unique_values_preview": {}
        },
        "bias_flags": {} # Detailed bias findings
    }

    try:
        # Read the contents of the uploaded file.
        contents = await file.read()
        file_size_mb = len(contents) / (1024 * 1024)
        logger.info(f"Processing uploaded file '{file.filename}' of size {file_size_mb:.2f} MB.")

        # Determine file type and read into a pandas DataFrame.
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        elif file.filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            logger.warning(f"Unsupported file type uploaded: {file.filename}")
            raise HTTPException(status_code=400, detail="Unsupported file type. Please upload a CSV or Excel file.")

        # Populate basic file details in the report.
        report["file_details"]["rows"] = len(df)
        report["file_details"]["columns"] = len(df.columns)
        report["file_details"]["column_names"] = df.columns.tolist()

        logger.info(f"File '{file.filename}' read successfully. Shape: {df.shape}")

        # --- Data Quality Checks ---

        # 1. Missing Values Analysis
        # Calculates the count and percentage of missing values for each column.
        # Adds an alert to `summary_alerts` if a column has more than the defined threshold (MISSING_VALUE_THRESHOLD).
        missing_data = df.isnull().sum()
        missing_percentage = (df.isnull().sum() / len(df)) * 100
        for col in df.columns:
            if missing_data[col] > 0:
                report["quality_checks"]["missing_values"][col] = {
                    "count": int(missing_data[col]), # Convert numpy.int64 to standard int
                    "percentage": round(float(missing_percentage[col]), 2) # Convert numpy.float64 to standard float
                }
                if missing_percentage[col] > MISSING_VALUE_THRESHOLD:
                    report["summary_alerts"].append({
                        "type": "Missing Data",
                        "column": col,
                        "message": f"'{col}' has {missing_percentage[col]:.2f}% missing values, exceeding threshold of {MISSING_VALUE_THRESHOLD}%."
                    })
                    logger.warning(f"Missing data alert: '{col}' has {missing_percentage[col]:.2f}% missing values.")

        # 2. Duplicate Rows Detection
        # Counts the total number of exact duplicate rows in the dataset.
        # Adds an alert to `summary_alerts` if any duplicate rows are found.
        duplicate_rows_count = df.duplicated().sum()
        report["quality_checks"]["duplicate_rows"] = int(duplicate_rows_count) # Convert to standard int
        if duplicate_rows_count > 0:
            report["summary_alerts"].append({
                "type": "Duplicate Rows",
                "message": f"{int(duplicate_rows_count)} exact duplicate rows detected."
            })
            logger.warning(f"Duplicate rows alert: {int(duplicate_rows_count)} duplicates found.")
        
        # 3. Column Data Types and Basic Statistics
        # Iterates through each column to determine its data type and calculate descriptive statistics
        # for numeric columns. Also provides a preview of unique values for categorical/low-cardinality columns.
        for col in df.columns:
            dtype = str(df[col].dtype)
            report["quality_checks"]["column_data_types"][col] = dtype

            # Calculate descriptive statistics for numeric columns.
            if pd.api.types.is_numeric_dtype(df[col]):
                desc_stats = df[col].describe().to_dict()
                # Ensure all numeric stats are properly serialized to float, handling potential numpy types (e.g., np.int64, np.float64)
                report["quality_checks"]["column_statistics"][col] = {
                    k: float(v) if pd.api.types.is_numeric_dtype(type(v)) else v
                    for k, v in desc_stats.items()
                }
            
            # Capture unique values preview for columns with a reasonable number of unique entries.
            unique_count = df[col].nunique()
            # Thresholds: either less than 50 unique values or unique values make up less than 50% of total rows.
            if unique_count > 0 and (unique_count < 50 or unique_count / len(df) < 0.5):
                preview_dict = df[col].value_counts().head(10).to_dict()
                cleaned_preview_dict = {}
                for key, value in preview_dict.items():
                    # Handle keys (can be numbers, strings, NaNs). Convert NaN keys to string "NaN" for JSON.
                    cleaned_key = str(key) if pd.isna(key) else key 
                    # Handle values (counts, often numpy.int64). Convert to standard Python int/float.
                    cleaned_value = int(value) if pd.api.types.is_integer_dtype(type(value)) else \
                                    float(value) if pd.api.types.is_numeric_dtype(type(value)) else value
                    cleaned_preview_dict[cleaned_key] = cleaned_value
                report["quality_checks"]["unique_values_preview"][col] = cleaned_preview_dict


        # --- Bias Flagging Logic ---
        # This section analyzes potential biases based on user-defined sensitive attributes and an outcome column.

        parsed_sensitive_attributes: List[str] = []
        if sensitive_attributes:
            try:
                # Attempt to parse the sensitive attributes from a JSON string provided by the frontend.
                parsed_sensitive_attributes = json.loads(sensitive_attributes)
                # Clean and filter the list to ensure valid, non-empty string attribute names.
                parsed_sensitive_attributes = [str(s).strip() for s in parsed_sensitive_attributes if str(s).strip()]
            except json.JSONDecodeError as e:
                # If the JSON string is malformed, log an error and add it to the report for frontend display.
                error_message = f"Could not parse sensitive attributes. Please ensure it's a valid JSON array of strings (e.g., '[\"Gender\", \"Race\"]'). Error: {e}"
                report["bias_flags"]["_error"] = [{"type": "Input Error", "message": error_message}]
                logger.error(f"Error parsing sensitive_attributes: '{sensitive_attributes}'. Error: {e}", exc_info=True)
                parsed_sensitive_attributes = [] # Reset to empty to prevent further processing errors

        # Identify sensitive attributes present in the DataFrame and those that are missing.
        available_sensitive_attributes = [attr for attr in parsed_sensitive_attributes if attr in df.columns]
        missing_sensitive_attributes = [attr for attr in parsed_sensitive_attributes if attr not in df.columns]

        # Add information about missing sensitive attribute columns to the report.
        if missing_sensitive_attributes:
            if "_info" not in report["bias_flags"]:
                report["bias_flags"]["_info"] = []
            message = f"The following sensitive attributes were not found in your data: {', '.join(missing_sensitive_attributes)}. Please check column names."
            report["bias_flags"]["_info"].append({"type": "Missing Columns", "message": message})
            logger.warning(f"Sensitive attributes not found in data: {missing_sensitive_attributes}")

        # Iterate through each available sensitive attribute to perform bias checks.
        for attr in available_sensitive_attributes:
            report["bias_flags"][attr] = [] # Initialize list for current attribute's bias flags

            # 1. Distribution Imbalance Check for Categorical Sensitive Attributes
            # Checks if any single category within a sensitive attribute is overwhelmingly dominant
            # or extremely rare, which could indicate imbalance leading to bias.
            if pd.api.types.is_object_dtype(df[attr]) or pd.api.types.is_string_dtype(df[attr]):
                value_counts = df[attr].value_counts(normalize=True) * 100
                value_counts = value_counts.dropna() # Exclude NaN from imbalance check

                if len(value_counts) > 0:
                    for val, percent in value_counts.items():
                        # Ensure value is converted to string for consistency in JSON, handle potential NaN values.
                        val_str = str(val) if pd.isna(val) else val
                        # Ensure percentage is a standard float.
                        percent_float = round(float(percent), 2)
                        
                        if percent_float >= DOMINANT_IMBALANCE_THRESHOLD:
                            message = f"Value '{val_str}' makes up {percent_float:.2f}% of data in '{attr}', exceeding dominant threshold of {DOMINANT_IMBALANCE_THRESHOLD}%. This significant imbalance could lead to bias."
                            report["bias_flags"][attr].append({"type": "Imbalance", "message": message})
                            report["summary_alerts"].append({"type": "Bias Imbalance", "column": attr, "group": val_str, "message": f"'{attr}' is {percent_float:.2f}% '{val_str}'. Significant imbalance."})
                            logger.warning(f"Bias Imbalance (Dominant) alert for '{attr}': '{val_str}' at {percent_float:.2f}%.")
                        elif percent_float <= RARE_IMBALANCE_THRESHOLD and len(value_counts) > 1: # Only flag as rare if there are other values
                            message = f"Value '{val_str}' makes up {percent_float:.2f}% of data in '{attr}', below rare threshold of {RARE_IMBALANCE_THRESHOLD}%. This rare representation could lead to bias if not handled."
                            report["bias_flags"][attr].append({"type": "Imbalance", "message": message})
                            report["summary_alerts"].append({"type": "Bias Imbalance", "column": attr, "group": val_str, "message": f"'{attr}' is {percent_float:.2f}% '{val_str}'. Rare representation."})
                            logger.warning(f"Bias Imbalance (Rare) alert for '{attr}': '{val_str}' at {percent_float:.2f}%.")
                else:
                    message = f"Sensitive attribute '{attr}' contains only missing values or no unique non-null categories for imbalance check."
                    report["bias_flags"][attr].append({"type": "Info", "message": message})
                    logger.info(message)
            else:
                message = f"'{attr}' is a numeric column. Basic imbalance checks are performed for categorical attributes. More complex bias checks for numeric attributes are beyond the scope of this tool."
                report["bias_flags"][attr].append({"type": "Info", "message": message})
                logger.info(message)

            # 2. Simple Disparity in Outcome Check
            # This check analyzes if there's a significant difference in the average outcome
            # across different groups within a sensitive attribute.
            if outcome_column and outcome_column in df.columns:
                outcome_col_numeric = outcome_column + '_numeric'
                # If favorable_outcome_value is provided and outcome is not numeric,
                # map the favorable value to 1.0, others to 0.0 (for binary classification outcomes).
                if favorable_outcome_value and not pd.api.types.is_numeric_dtype(df[outcome_column]):
                    favorable_val_lower = str(favorable_outcome_value).strip().lower()
                    
                    def map_outcome_to_binary(val):
                        val_str = str(val).strip().lower()
                        if val_str == favorable_val_lower:
                            return 1.0
                        # Treat non-favorable non-null values as 0.0, and actual NaN values from original data as pd.NA.
                        return 0.0 if not pd.isna(val) else pd.NA 

                    df[outcome_col_numeric] = df[outcome_column].apply(map_outcome_to_binary)
                    # Convert to numeric, coercing any remaining errors to NaN.
                    df[outcome_col_numeric] = pd.to_numeric(df[outcome_col_numeric], errors='coerce')
                else:
                    # If no favorable_outcome_value or already numeric, just convert to numeric directly.
                    df[outcome_col_numeric] = pd.to_numeric(df[outcome_column], errors='coerce')

                # Filter out rows with missing values in either the sensitive attribute or the numeric outcome column.
                temp_filtered_df = df.dropna(subset=[attr, outcome_col_numeric])
                
                # Proceed with disparity check only if there's sufficient data and more than one distinct group.
                if not temp_filtered_df.empty and len(temp_filtered_df[attr].unique()) > 1:
                    group_means = temp_filtered_df.groupby(attr)[outcome_col_numeric].mean().dropna()

                    if len(group_means) > 1: # Ensure there are at least two groups to compare.
                        max_mean = float(group_means.max()) # Convert numpy.float64 to standard float
                        min_mean = float(group_means.min()) # Convert numpy.float64 to standard float
                        disparity = abs(max_mean - min_mean) * 100 # Calculate percentage difference

                        if disparity >= DISPARITY_THRESHOLD: # Configurable threshold for flagging disparity
                            message = f"Significant outcome disparity detected in '{outcome_column}' across '{attr}' groups. Max average: {max_mean:.2f}, Min average: {min_mean:.2f}. Difference: {disparity:.2f} percentage points, exceeding threshold of {DISPARITY_THRESHOLD}%."
                            report["bias_flags"][attr].append({"type": "Disparity", "message": message})
                            report["summary_alerts"].append({"type": "Bias Disparity", "column": attr, "outcome": outcome_column, "message": f"'{attr}' shows {disparity:.2f} percentage points disparity in '{outcome_column}'."})
                            logger.warning(f"Bias Disparity alert for '{attr}' and '{outcome_column}': {disparity:.2f}% difference.")
                        else:
                            message = f"Outcome disparity in '{outcome_column}' across '{attr}' groups is {disparity:.2f} percentage points, which is below the alert threshold of {DISPARITY_THRESHOLD}%."
                            report["bias_flags"][attr].append({"type": "Info", "message": message})
                            logger.info(message)
                    else:
                        message = f"Not enough distinct groups in '{attr}' to check for outcome disparity with '{outcome_column}' after filtering missing values."
                        report["bias_flags"][attr].append({"type": "Info", "message": message})
                        logger.info(message)
                else:
                    message = f"Not enough data or distinct groups in '{attr}' (after handling missing values) to perform outcome disparity check with '{outcome_column}'."
                    report["bias_flags"][attr].append({"type": "Info", "message": message})
                    logger.info(message)

            elif outcome_column and outcome_column not in df.columns:
                message = f"Outcome column '{outcome_column}' not found in the data. Cannot perform disparity check."
                report["bias_flags"][attr].append({"type": "Missing Columns", "message": message})
                logger.warning(message)


            # --- NEW: Disparate Impact Ratio (DIR) Check ---
            # This check assesses fairness by comparing the rate of 'favorable outcomes'
            # between an 'unprivileged' group and a 'privileged' group.
            # A DIR significantly below 1.0 (e.g., < 0.8) suggests potential adverse impact.
            # Requires: a specified outcome_column, a favorable_outcome_value (to define 'success'),
            # and a privileged_group_value (to define the reference group).
            if outcome_column and outcome_column in df.columns and favorable_outcome_value and privileged_group_value:
                # Ensure the created numeric outcome column contains only binary values (0 or 1), ignoring NaNs.
                binary_values = df[outcome_col_numeric].dropna().unique()
                if np.all(np.isin(binary_values, [0.0, 1.0])): # Check if all non-NaN values are 0.0 or 1.0
                    privileged_val_str = str(privileged_group_value).strip()
                    
                    df_filtered = df.dropna(subset=[attr, outcome_col_numeric])

                    if not df_filtered.empty:
                        # Convert sensitive attribute to string for consistent comparison and handling of NaNs.
                        df_filtered[attr + '_str'] = df_filtered[attr].astype(str).str.strip()

                        all_groups = df_filtered[attr + '_str'].unique()
                        
                        if privileged_val_str not in all_groups:
                            report["bias_flags"][attr].append({
                                "type": "DIR Info",
                                "message": f"Privileged group value '{privileged_val_str}' not found in column '{attr}'. Cannot calculate Disparate Impact Ratio."
                            })
                            logger.warning(f"Privileged group value '{privileged_val_str}' not found in '{attr}'. Skipping DIR.")
                            continue # Skip DIR calculation for this attribute if privileged group is missing

                        # Calculate selection rates (proportion of favorable outcomes) for each group.
                        selection_rates = {}
                        for group in all_groups:
                            group_df = df_filtered[df_filtered[attr + '_str'] == group]
                            if not group_df.empty:
                                total_in_group = len(group_df)
                                favorable_outcomes = group_df[group_df[outcome_col_numeric] == 1.0].shape[0]
                                selection_rates[group] = float(favorable_outcomes / total_in_group) if total_in_group > 0 else 0.0
                            else:
                                selection_rates[group] = 0.0
                        
                        privileged_rate = selection_rates.get(privileged_val_str, 0.0) # Get rate for privileged group

                        if privileged_rate == 0:
                            report["bias_flags"][attr].append({
                                "type": "DIR Warning",
                                "message": f"Privileged group '{privileged_val_str}' has a 0% selection rate in '{outcome_column}'. Disparate Impact Ratio cannot be meaningfully calculated."
                            })
                            logger.warning(f"Privileged group '{privileged_val_str}' has 0% selection rate. Cannot calculate meaningful DIR.")
                        else:
                            # Prepare details for the DIR summary in the report.
                            dir_details = {"privileged_group": privileged_val_str, "selection_rates": {}}
                            
                            # Calculate DIR for each unprivileged group compared to the privileged group.
                            for group, rate in selection_rates.items():
                                dir_details["selection_rates"][str(group)] = round(rate * 100, 2) # Store selection rates as percentages
                                
                                if group != privileged_val_str: # Only compare unprivileged groups to the privileged one
                                    dir_val = rate / privileged_rate # Calculate the ratio
                                    dir_details[f"DIR_vs_{str(group)}"] = round(float(dir_val), 2) # Store ratio, ensure float
                                    
                                    if dir_val < DIR_THRESHOLD: # If ratio is below threshold, flag as adverse impact.
                                        message = f"Disparate Impact Ratio for '{group}' vs '{privileged_val_str}' in '{attr}' is {dir_val:.2f} (below threshold {DIR_THRESHOLD}). This indicates potential adverse impact."
                                        report["bias_flags"][attr].append({"type": "Bias Disparate Impact", "group_comparison": f"{group} vs {privileged_val_str}", "ratio": round(float(dir_val), 2), "message": message})
                                        report["summary_alerts"].append({
                                            "type": "Bias Disparate Impact",
                                            "column": attr,
                                            "group_unprivileged": str(group),
                                            "group_privileged": privileged_val_str,
                                            "ratio": round(float(dir_val), 2),
                                            "message": f"Disparate Impact for '{group}' vs '{privileged_val_str}' in '{attr}' is {dir_val:.2f} (below {DIR_THRESHOLD})."
                                        })
                                        logger.warning(f"Disparate Impact alert: {message}")
                            
                            # Add the overall DIR calculation summary to the report for this sensitive attribute.
                            # Ensure this is appended ONCE per sensitive attribute, after all group comparisons.
                            report["bias_flags"][attr].append({"type": "DIR Summary", "details": dir_details})

                else:
                    message = f"Outcome column '{outcome_column}' is not binary (0/1) after processing with 'Favorable Outcome Value'. Disparate Impact Ratio requires a binary outcome."
                    report["bias_flags"][attr].append({"type": "DIR Info", "message": message})
                    logger.info(f"Outcome column '{outcome_column}' is not binary (0/1) for DIR check.")
            else:
                # If outcome_column is present but favorable_outcome_value or privileged_group_value are missing.
                if outcome_column and outcome_column in df.columns: 
                    report["bias_flags"][attr].append({
                        "type": "DIR Info",
                        "message": f"To calculate Disparate Impact Ratio for '{attr}', please provide both 'Favorable Outcome Value' and 'Privileged Group Value'."
                    })
                    logger.info(f"Missing favorable_outcome_value or privileged_group_value for DIR check on '{attr}'.")

        # --- TEMPORARY DEBUGGING SECTION ---
        # This section is for debugging the "null" response from the server.
        # It attempts to serialize the `report` dictionary to a JSON string directly
        # before FastAPI's own serialization. If this step fails with a TypeError,
        # it indicates a non-JSON-serializable object is still present in the `report`.
        # This block can be removed in production once stability is confirmed.
        try:
            json_dump_test = json.dumps(report, indent=2)
            logger.debug(f"Successfully serialized report to JSON string (for debug). First 500 chars: {json_dump_test[:500]}...")
        except TypeError as e:
            logger.error(f"FATAL: Report contains non-JSON-serializable data! Error: {e}", exc_info=True)
            # Re-raise the TypeError to be caught by the outer try-except block,
            # which will then return a 500 Internal Server Error to the client
            # and log the full traceback.
            raise e 
        # --- END TEMPORARY DEBUGGING SECTION ---

        return report # Return the final structured report as a JSON response.

    except HTTPException as e:
        # Re-raise HTTPExceptions directly, as these are expected application-level errors
        # (e.g., 400 Bad Request for unsupported file type).
        logger.warning(f"HTTPException caught: {e.detail}", exc_info=True)
        raise e
    except pd.errors.EmptyDataError:
        # Handle specific error for empty or malformed data files.
        logger.error(f"Empty data error for file: {file.filename}")
        raise HTTPException(status_code=400, detail="The uploaded file appears to be empty or contains no data. Please upload a valid CSV or Excel file.")
    except Exception as e:
        # Catch any other unexpected errors during processing.
        # Log the full traceback for server-side debugging.
        logger.error(f"Unhandled server error during file processing for '{file.filename}': {str(e)}", exc_info=True)
        # For security, return a generic 500 error to the client, hiding internal details.
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred. Please check server logs for details. (Error type: {type(e).__name__})")