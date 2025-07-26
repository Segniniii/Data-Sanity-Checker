from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
import os
from typing import List, Optional
import json

# Initialize the FastAPI application
app = FastAPI()

# Configure CORS (Cross-Origin Resource Sharing) middleware.
# This allows requests from any origin ("*") to access the API, which is useful for development.
# For production, it's recommended to restrict `allow_origins` to specific domains.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,  # Allows credentials (e.g., cookies, authorization headers) to be sent
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)

# Define the absolute path to the 'Frontend' directory.
# This ensures that the static files (HTML, CSS, JS) are correctly served regardless of where the script is run.
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Frontend'))
print(f"Serving static files from: {frontend_dir}")

# Mount the static files directory.
# Files in the 'frontend_dir' will be accessible under the "/static" URL path.
# For example, if `index.html` is in `Frontend`, it can be accessed via `/static/index.html`.
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """
    Serves the main HTML page (`index.html`) from the Frontend directory.
    This is the default endpoint for the web application.
    """
    index_path = os.path.join(frontend_dir, "index.html")
    print(f"Attempting to serve: {index_path}")
    # Check if the index.html file exists to prevent a FileNotFoundError.
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="index.html not found. Check frontend_dir path.")
    # Read and return the HTML content.
    with open(index_path, "r") as f:
        return HTMLResponse(content=f.read())

@app.post("/analyze-data/")
async def analyze_data(
    file: UploadFile = File(...),  # The uploaded data file (CSV or Excel)
    sensitive_attributes: Optional[str] = Form(None),  # JSON string of sensitive columns (e.g., "gender", "ethnicity")
    outcome_column: Optional[str] = Form(None)  # Name of the outcome/target column for bias checks
):
    """
    Receives an uploaded dataset (CSV or Excel), performs comprehensive data quality checks
    and identifies potential biases related to specified sensitive attributes and an outcome column.
    Returns a structured JSON report detailing findings.
    """
    print(f"DEBUG: Backend received sensitive_attributes (raw): {sensitive_attributes}")
    print(f"DEBUG: Backend received outcome_column (raw): {outcome_column}")
    
    # Initialize the report structure. This ensures a consistent response format,
    # and prevents issues if certain checks are skipped or encounter errors.
    report = {
        "message": f"File '{file.filename}' processed successfully! Initiating quality and bias checks.",
        "file_details": {},
        "summary_alerts": [],  # High-level alerts for critical issues
        "quality_checks": {
            "missing_values": {},
            "duplicate_rows": 0,
            "column_data_types": {},
            "column_statistics": {},
            "unique_values_preview": {}
        },
        "bias_flags": {}
    }

    try:
        # Read the contents of the uploaded file.
        contents = await file.read()

        # Determine file type and read into a pandas DataFrame.
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        elif file.filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            # Raise an HTTPException for unsupported file types.
            raise HTTPException(status_code=400, detail="Unsupported file type. Please upload a CSV or Excel file.")

        # Populate basic file details in the report.
        report["file_details"]["rows"] = len(df)
        report["file_details"]["columns"] = len(df.columns)
        report["file_details"]["column_names"] = df.columns.tolist()

        print(f"File '{file.filename}' received and read successfully! Shape: {df.shape}")

        # --- Data Quality Checks ---

        # 1. Missing Values Analysis
        # Calculates the count and percentage of missing values for each column.
        # Adds an alert to `summary_alerts` if a column has more than 5% missing values.
        missing_data = df.isnull().sum()
        missing_percentage = (df.isnull().sum() / len(df)) * 100
        for col in df.columns:
            if missing_data[col] > 0:
                report["quality_checks"]["missing_values"][col] = {
                    "count": int(missing_data[col]),
                    "percentage": round(float(missing_percentage[col]), 2)
                }
                if missing_percentage[col] > 5:  # Configurable threshold for alert
                    report["summary_alerts"].append({
                        "type": "Missing Data",
                        "column": col,
                        "message": f"'{col}' has {missing_percentage[col]:.2f}% missing values."
                    })

        # 2. Duplicate Rows Detection
        # Counts the total number of exact duplicate rows in the dataset.
        # Adds an alert to `summary_alerts` if any duplicate rows are found.
        duplicate_rows_count = df.duplicated().sum()
        report["quality_checks"]["duplicate_rows"] = int(duplicate_rows_count)
        if duplicate_rows_count > 0:
            report["summary_alerts"].append({
                "type": "Duplicate Rows",
                "message": f"{int(duplicate_rows_count)} exact duplicate rows detected."
            })
        
        # 3. Column Data Types and Basic Statistics
        # Iterates through each column to determine its data type and calculate descriptive statistics
        # for numeric columns. Also provides a preview of unique values for categorical/low-cardinality columns.
        for col in df.columns:
            dtype = str(df[col].dtype)
            report["quality_checks"]["column_data_types"][col] = dtype

            # Calculate descriptive statistics for numeric columns.
            if pd.api.types.is_numeric_dtype(df[col]):
                desc_stats = df[col].describe().to_dict()
                # Ensure all numeric stats are properly serialized to float.
                report["quality_checks"]["column_statistics"][col] = {k: float(v) if pd.api.types.is_numeric_dtype(type(v)) else v for k, v in desc_stats.items()}
            
            # Capture unique values preview for columns with a reasonable number of unique entries.
            unique_count = df[col].nunique()
            # Thresholds: either less than 50 unique values or unique values make up less than 50% of total rows.
            if unique_count > 0 and (unique_count < 50 or unique_count / len(df) < 0.5):
                report["quality_checks"]["unique_values_preview"][col] = df[col].value_counts().head(10).to_dict()

        # --- Bias Flagging Logic ---
        # This section analyzes potential biases based on user-defined sensitive attributes and an outcome column.

        # Parse sensitive attributes from the incoming JSON string.
        parsed_sensitive_attributes: List[str] = []
        if sensitive_attributes:
            try:
                parsed_sensitive_attributes = json.loads(sensitive_attributes)
                # Ensure attributes are stripped of whitespace and are strings.
                parsed_sensitive_attributes = [str(s).strip() for s in parsed_sensitive_attributes] 
            except json.JSONDecodeError:
                # Handle cases where sensitive_attributes is not a valid JSON string.
                report["bias_flags"]["_error"] = [{"type": "Input Error", "message": "Could not parse sensitive attributes. Please ensure it's a valid JSON array of strings."}]
                print(f"Error parsing sensitive_attributes: {sensitive_attributes}")
                parsed_sensitive_attributes = [] # Reset to empty to prevent further errors

        # Identify sensitive attributes present in the DataFrame and those that are missing.
        available_sensitive_attributes = [
            attr for attr in parsed_sensitive_attributes if attr in df.columns
        ]
        missing_sensitive_attributes = [
            attr for attr in parsed_sensitive_attributes if attr not in df.columns
        ]

        # Add information about missing sensitive attribute columns to the report.
        if missing_sensitive_attributes:
            if "_info" not in report["bias_flags"]:
                report["bias_flags"]["_info"] = []
            report["bias_flags"]["_info"].append({
                "type": "Missing Columns",
                "message": f"The following sensitive attributes were not found in your data: {', '.join(missing_sensitive_attributes)}. Please check column names."
            })

        # Iterate through each available sensitive attribute to perform bias checks.
        for attr in available_sensitive_attributes:
            report["bias_flags"][attr] = [] # Initialize list for current attribute's bias flags

            # 1. Distribution Imbalance Check for Categorical Sensitive Attributes
            # Checks if any single category within a sensitive attribute is overwhelmingly dominant
            # or extremely rare, which could indicate imbalance leading to bias.
            if pd.api.types.is_object_dtype(df[attr]) or pd.api.types.is_string_dtype(df[attr]):
                value_counts = df[attr].value_counts(normalize=True) * 100
                value_counts = value_counts.dropna() # Exclude NaN from imbalance check

                dominant_threshold = 90  # If one value makes up >90%
                rare_threshold = 10      # If one value makes up <10%

                if len(value_counts) > 0:
                    for val, percent in value_counts.items():
                        if percent >= dominant_threshold:
                            report["bias_flags"][attr].append({
                                "type": "Imbalance",
                                "message": f"Value '{val}' makes up {percent:.2f}% of data in '{attr}'. This significant imbalance could lead to bias."
                            })
                            report["summary_alerts"].append({
                                "type": "Bias Imbalance",
                                "column": attr,
                                "group": str(val),
                                "message": f"'{attr}' is {percent:.2f}% '{val}'. Significant imbalance."
                            })
                        elif percent <= rare_threshold and len(value_counts) > 1: # Only flag as rare if there are other values
                            report["bias_flags"][attr].append({
                                "type": "Imbalance",
                                "message": f"Value '{val}' makes up {percent:.2f}% of data in '{attr}'. This rare representation could lead to bias if not handled."
                            })
                            report["summary_alerts"].append({
                                "type": "Bias Imbalance",
                                "column": attr,
                                "group": str(val),
                                "message": f"'{attr}' is {percent:.2f}% '{val}'. Rare representation."
                            })
                else:
                    report["bias_flags"][attr].append({
                        "type": "Info",
                        "message": f"Sensitive attribute '{attr}' contains only missing values or no unique non-null categories for imbalance check."
                    })
            else:
                report["bias_flags"][attr].append({
                    "type": "Info",
                    "message": f"'{attr}' is a numeric column. Basic imbalance checks are performed for categorical attributes. More complex bias checks for numeric attributes are beyond the scope of this tool."
                })

            # 2. Simple Disparity in Outcome Check
            # This check analyzes if there's a significant difference in the average outcome
            # across different groups within a sensitive attribute.
            if outcome_column and outcome_column in df.columns:
                # Attempt to convert the outcome column to a numeric type if it's not already.
                # Handles boolean-like strings ('true', 'false', '1', '0') and other coercible types.
                if not pd.api.types.is_numeric_dtype(df[outcome_column]) and not pd.api.types.is_bool_dtype(df[outcome_column]):
                    if pd.api.types.is_object_dtype(df[outcome_column]) or pd.api.types.is_string_dtype(df[outcome_column]):
                        temp_outcome_series = df[outcome_column].astype(str).str.lower()
                        unique_str_outcomes = temp_outcome_series.dropna().unique()

                        if 'true' in unique_str_outcomes or 'false' in unique_str_outcomes:
                            df[outcome_column + '_numeric'] = temp_outcome_series.map({'true': 1, 'false': 0, '1': 1, '0': 0}).astype(float)
                        else:
                            df[outcome_column + '_numeric'] = pd.to_numeric(df[outcome_column], errors='coerce')
                    else:
                        df[outcome_column + '_numeric'] = pd.to_numeric(df[outcome_column], errors='coerce')
                else:
                    df[outcome_column + '_numeric'] = df[outcome_column].astype(float)

                outcome_col_numeric = outcome_column + '_numeric'
                
                # Filter out rows with missing values in either the sensitive attribute or the numeric outcome column.
                temp_filtered_df = df.dropna(subset=[attr, outcome_col_numeric])
                
                # Proceed with disparity check only if there's sufficient data and more than one distinct group.
                if not temp_filtered_df.empty and len(temp_filtered_df[attr].unique()) > 1:
                    group_means = temp_filtered_df.groupby(attr)[outcome_col_numeric].mean().dropna()

                    if len(group_means) > 1: # Ensure there are at least two groups to compare.
                        max_mean = group_means.max()
                        min_mean = group_means.min()
                        disparity = abs(max_mean - min_mean) * 100 # Calculate percentage difference

                        disparity_threshold = 20 # Configurable threshold for flagging disparity

                        if disparity >= disparity_threshold:
                            report["bias_flags"][attr].append({
                                "type": "Disparity",
                                "message": f"Significant outcome disparity detected in '{outcome_column}' across '{attr}' groups. Max average: {max_mean:.2f}, Min average: {min_mean:.2f}. Difference: {disparity:.2f} percentage points."
                            })
                            report["summary_alerts"].append({
                                "type": "Bias Disparity",
                                "column": attr,
                                "outcome": outcome_column,
                                "message": f"'{attr}' shows {disparity:.2f} percentage points disparity in '{outcome_column}'."
                            })
                    else:
                        report["bias_flags"][attr].append({
                            "type": "Info",
                            "message": f"Not enough distinct groups in '{attr}' to check for outcome disparity with '{outcome_column}'."
                        })
                else:
                    report["bias_flags"][attr].append({
                        "type": "Info",
                        "message": f"Not enough data or distinct groups in '{attr}' to perform outcome disparity check."
                    })

            elif outcome_column and outcome_column not in df.columns:
                # Inform if the specified outcome column is not found.
                report["bias_flags"][attr].append({
                    "type": "Missing Columns",
                    "message": f"Outcome column '{outcome_column}' not found in the data."
                })

        return report

    except HTTPException as e:
        # Re-raise HTTPExceptions directly, as they are already structured for FastAPI.
        raise e
    except Exception as e:
        # Catch any other unexpected errors during processing, log them, and return a 500 status.
        print(f"Server error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")