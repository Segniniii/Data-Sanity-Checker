from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
import os
from typing import List, Optional
import json
import logging # Import the logging module

# --- Logging Configuration ---
# Configure logging: INFO level for general messages, DEBUG for more verbose
# Format: timestamp - logger_name - log_level - message
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__) # Get a logger for this module

# --- Application Configuration (using Environment Variables) ---
# For production, set these environment variables in your deployment environment.
# Examples:
# ALLOWED_ORIGINS="https://yourfrontend.com,https://anotherdomain.com"
# MISSING_VALUE_THRESHOLD="5.0"
# DOMINANT_IMBALANCE_THRESHOLD="90.0"
# RARE_IMBALANCE_THRESHOLD="10.0"
# DISPARITY_THRESHOLD="20.0"

# Get allowed origins from environment variable, default to all for development
# In production, this should be a comma-separated list like "https://yourfrontenddomain.com"
ALLOWED_ORIGINS_STR = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = [o.strip() for o in ALLOWED_ORIGINS_STR.split(',')]
if "*" in ALLOWED_ORIGINS: # Ensure explicit list if not truly all
    logger.warning("CORS 'allow_origins' is set to '*', which is insecure for production. Please configure specific origins.")

# Thresholds for quality and bias checks, configurable via environment variables
MISSING_VALUE_THRESHOLD = float(os.getenv("MISSING_VALUE_THRESHOLD", "5.0"))
DOMINANT_IMBALANCE_THRESHOLD = float(os.getenv("DOMINANT_IMBALANCE_THRESHOLD", "90.0"))
RARE_IMBALANCE_THRESHOLD = float(os.getenv("RARE_IMBALANCE_THRESHOLD", "10.0"))
DISPARITY_THRESHOLD = float(os.getenv("DISPARITY_THRESHOLD", "20.0"))


# Initialize the FastAPI application
app = FastAPI()

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define the absolute path to the 'Frontend' directory.
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Frontend'))
logger.info(f"Serving static files from: {frontend_dir}")

# Mount the static files directory.
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """
    Serves the main HTML page (`index.html`) from the Frontend directory.
    This is the default endpoint for the web application.
    """
    index_path = os.path.join(frontend_dir, "index.html")
    logger.info(f"Attempting to serve: {index_path}")
    # Check if the index.html file exists to prevent a FileNotFoundError.
    if not os.path.exists(index_path):
        logger.error(f"index.html not found at {index_path}. Check frontend_dir path.")
        raise HTTPException(status_code=404, detail="index.html not found. Check frontend_dir path or deployment configuration.")
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
    logger.debug(f"Received file: '{file.filename}', sensitive_attributes (raw): '{sensitive_attributes}', outcome_column (raw): '{outcome_column}'")
    
    # Initialize the report structure.
    report = {
        "message": f"File '{file.filename}' processed successfully! Initiating quality and bias checks.",
        "file_details": {},
        "summary_alerts": [],
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
        contents = await file.read()
        file_size_mb = len(contents) / (1024 * 1024)
        logger.info(f"Processing uploaded file '{file.filename}' of size {file_size_mb:.2f} MB.")

        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        elif file.filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            logger.warning(f"Unsupported file type uploaded: {file.filename}")
            raise HTTPException(status_code=400, detail="Unsupported file type. Please upload a CSV or Excel file.")

        report["file_details"]["rows"] = len(df)
        report["file_details"]["columns"] = len(df.columns)
        report["file_details"]["column_names"] = df.columns.tolist()

        logger.info(f"File '{file.filename}' read successfully. Shape: {df.shape}")

        # --- Data Quality Checks ---

        # 1. Missing Values Analysis
        missing_data = df.isnull().sum()
        missing_percentage = (df.isnull().sum() / len(df)) * 100
        for col in df.columns:
            if missing_data[col] > 0:
                report["quality_checks"]["missing_values"][col] = {
                    "count": int(missing_data[col]),
                    "percentage": round(float(missing_percentage[col]), 2)
                }
                if missing_percentage[col] > MISSING_VALUE_THRESHOLD:
                    report["summary_alerts"].append({
                        "type": "Missing Data",
                        "column": col,
                        "message": f"'{col}' has {missing_percentage[col]:.2f}% missing values, exceeding threshold of {MISSING_VALUE_THRESHOLD}%."
                    })
                    logger.warning(f"Missing data alert: '{col}' has {missing_percentage[col]:.2f}% missing values.")

        # 2. Duplicate Rows Detection
        duplicate_rows_count = df.duplicated().sum()
        report["quality_checks"]["duplicate_rows"] = int(duplicate_rows_count)
        if duplicate_rows_count > 0:
            report["summary_alerts"].append({
                "type": "Duplicate Rows",
                "message": f"{int(duplicate_rows_count)} exact duplicate rows detected."
            })
            logger.warning(f"Duplicate rows alert: {int(duplicate_rows_count)} duplicates found.")
        
        # 3. Column Data Types and Basic Statistics
        for col in df.columns:
            dtype = str(df[col].dtype)
            report["quality_checks"]["column_data_types"][col] = dtype

            if pd.api.types.is_numeric_dtype(df[col]):
                desc_stats = df[col].describe().to_dict()
                report["quality_checks"]["column_statistics"][col] = {k: float(v) if pd.api.types.is_numeric_dtype(type(v)) else v for k, v in desc_stats.items()}
            
            unique_count = df[col].nunique()
            if unique_count > 0 and (unique_count < 50 or unique_count / len(df) < 0.5):
                report["quality_checks"]["unique_values_preview"][col] = df[col].value_counts().head(10).to_dict()

        # --- Bias Flagging Logic ---

        parsed_sensitive_attributes: List[str] = []
        if sensitive_attributes:
            try:
                parsed_sensitive_attributes = json.loads(sensitive_attributes)
                parsed_sensitive_attributes = [str(s).strip() for s in parsed_sensitive_attributes if str(s).strip()] # Filter out empty strings
            except json.JSONDecodeError as e:
                error_message = f"Could not parse sensitive attributes. Please ensure it's a valid JSON array of strings (e.g., '[\"Gender\", \"Race\"]'). Error: {e}"
                report["bias_flags"]["_error"] = [{"type": "Input Error", "message": error_message}]
                logger.error(f"Error parsing sensitive_attributes: '{sensitive_attributes}'. Error: {e}", exc_info=True)
                parsed_sensitive_attributes = []

        available_sensitive_attributes = [attr for attr in parsed_sensitive_attributes if attr in df.columns]
        missing_sensitive_attributes = [attr for attr in parsed_sensitive_attributes if attr not in df.columns]

        if missing_sensitive_attributes:
            if "_info" not in report["bias_flags"]:
                report["bias_flags"]["_info"] = []
            message = f"The following sensitive attributes were not found in your data: {', '.join(missing_sensitive_attributes)}. Please check column names."
            report["bias_flags"]["_info"].append({"type": "Missing Columns", "message": message})
            logger.warning(f"Sensitive attributes not found in data: {missing_sensitive_attributes}")

        for attr in available_sensitive_attributes:
            report["bias_flags"][attr] = []

            # 1. Distribution Imbalance Check for Categorical Sensitive Attributes
            if pd.api.types.is_object_dtype(df[attr]) or pd.api.types.is_string_dtype(df[attr]):
                value_counts = df[attr].value_counts(normalize=True) * 100
                value_counts = value_counts.dropna()

                if len(value_counts) > 0:
                    for val, percent in value_counts.items():
                        if percent >= DOMINANT_IMBALANCE_THRESHOLD:
                            message = f"Value '{val}' makes up {percent:.2f}% of data in '{attr}', exceeding dominant threshold of {DOMINANT_IMBALANCE_THRESHOLD}%. This significant imbalance could lead to bias."
                            report["bias_flags"][attr].append({"type": "Imbalance", "message": message})
                            report["summary_alerts"].append({"type": "Bias Imbalance", "column": attr, "group": str(val), "message": f"'{attr}' is {percent:.2f}% '{val}'. Significant imbalance."})
                            logger.warning(f"Bias Imbalance (Dominant) alert for '{attr}': '{val}' at {percent:.2f}%.")
                        elif percent <= RARE_IMBALANCE_THRESHOLD and len(value_counts) > 1:
                            message = f"Value '{val}' makes up {percent:.2f}% of data in '{attr}', below rare threshold of {RARE_IMBALANCE_THRESHOLD}%. This rare representation could lead to bias if not handled."
                            report["bias_flags"][attr].append({"type": "Imbalance", "message": message})
                            report["summary_alerts"].append({"type": "Bias Imbalance", "column": attr, "group": str(val), "message": f"'{attr}' is {percent:.2f}% '{val}'. Rare representation."})
                            logger.warning(f"Bias Imbalance (Rare) alert for '{attr}': '{val}' at {percent:.2f}%.")
                else:
                    message = f"Sensitive attribute '{attr}' contains only missing values or no unique non-null categories for imbalance check."
                    report["bias_flags"][attr].append({"type": "Info", "message": message})
                    logger.info(message)
            else:
                message = f"'{attr}' is a numeric column. Basic imbalance checks are performed for categorical attributes. More complex bias checks for numeric attributes are beyond the scope of this tool."
                report["bias_flags"][attr].append({"type": "Info", "message": message})
                logger.info(message)

            # 2. Simple Disparity in Outcome Check
            if outcome_column and outcome_column in df.columns:
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
                
                temp_filtered_df = df.dropna(subset=[attr, outcome_col_numeric])
                
                if not temp_filtered_df.empty and len(temp_filtered_df[attr].unique()) > 1:
                    group_means = temp_filtered_df.groupby(attr)[outcome_col_numeric].mean().dropna()

                    if len(group_means) > 1:
                        max_mean = group_means.max()
                        min_mean = group_means.min()
                        disparity = abs(max_mean - min_mean) * 100

                        if disparity >= DISPARITY_THRESHOLD:
                            message = f"Significant outcome disparity detected in '{outcome_column}' across '{attr}' groups. Max average: {max_mean:.2f}, Min average: {min_mean:.2f}. Difference: {disparity:.2f} percentage points, exceeding threshold of {DISPARITY_THRESHOLD}."
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

        return report

    except HTTPException as e:
        # Re-raise HTTPExceptions directly
        logger.warning(f"HTTPException caught: {e.detail}", exc_info=True)
        raise e
    except pd.errors.EmptyDataError:
        logger.error(f"Empty data error for file: {file.filename}")
        raise HTTPException(status_code=400, detail="The uploaded file appears to be empty or contains no data.")
    except Exception as e:
        # Catch any other unexpected errors, log them, and return a generic 500 status.
        logger.error(f"Unhandled server error during file processing for '{file.filename}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while processing your file. Please try again or contact support if the issue persists.")