# 📊 Data Sanity Checker

A comprehensive, open-source web-based tool designed to help AI startups and data professionals analyze data quality and detect potential ethical biases in tabular datasets. Easily upload your CSV or Excel files to gain instant, actionable insights into data integrity, missing values, duplicates, and critical bias metrics across sensitive attributes.

**Built with FastAPI (Python) for the backend and pure JavaScript, HTML, CSS for a responsive frontend.**

## ✨ Key Features

### 💎 Data Quality Analysis
* **Missing Values Detection & Quantification**: Accurately identifies columns with missing data, providing both count and percentage for quick assessment. Alerts if a column exceeds a configurable missing value threshold (default: 5%).
* **Duplicate Row Detection**: Pinpoints and quantifies exact duplicate entries across the entire dataset, flagging potential data integrity issues.
* **Automated Data Type Analysis**: Automatically infers and displays the data type for each column, aiding in schema validation.
* **Comprehensive Statistical Summary**: Generates descriptive statistics (mean, median, standard deviation, min, max, quartiles) for all numeric columns.
* **Categorical Data Distribution Analysis**: Provides frequency counts and percentages for unique values in low-cardinality and categorical columns, crucial for understanding data spread.

### ⚖️ Bias Detection
* **Sensitive Attribute Analysis**: Enables checks for representational imbalances within user-defined sensitive (protected) characteristics (e.g., 'Gender', 'Race', 'AgeGroup').
* **Group Distribution Imbalance Flagging**: Alerts if any single category within a sensitive attribute is overwhelmingly dominant (e.g., >90%) or critically rare (e.g., <10%), highlighting potential underrepresentation or overrepresentation.
* **Outcome Disparity Detection**: Identifies significant differences in the average outcome (target variable) across various groups within a sensitive attribute. Flags disparities exceeding a configurable percentage point threshold (default: 20%).
* **NEW: Disparate Impact Ratio (DIR)**: Calculates the Disparate Impact Ratio, a crucial fairness metric, by comparing the 'favorable outcome' rate of an 'unprivileged' group against a 'privileged' reference group. Flags potential adverse impact if the ratio falls below a configurable threshold (default: 0.8 or 80%). This helps identify if a process or dataset disproportionately harms specific groups.

### 🌐 User Experience
* **Intuitive Drag & Drop Interface**: Simplifies file uploads for CSV and Excel formats.
* **Interactive Visualizations**: Leverages Chart.js to render clear, interactive bar charts for data distributions, missing values, and bias patterns.
* **Comprehensive Downloadable Reports**: Generates and allows download of a self-contained HTML report summarizing all data quality and bias findings for offline review and sharing.
* **Real-time Analysis & Feedback**: Provides immediate status updates and displays results swiftly after data processing.

---

## 📸 Screenshots
<img width="666" height="697" alt="image" src="https://github.com/user-attachments/assets/8fe0b120-36ba-4c82-884c-21d9f45e889d" />

*Figure 1: Data Upload and Analysis Input Interface*

<img width="656" height="369" alt="image" src="https://github.com/user-attachments/assets/160777a8-2b36-4dbe-aede-8cc3efc6be91" />

*Figure 2: Example of a Detailed Analysis Report including Bias Flags and Data Quality Checks*

---

## 📋 Prerequisites

* **Python 3.11+**: The backend is built with FastAPI and requires a compatible Python version.
* **Docker Desktop**: Recommended for easy setup and consistent environment management.
* A modern web browser (Chrome, Firefox, Safari, Edge).

---

## 🛠️ Installation & Setup (Local)

To get the Data Sanity Checker up and running on your local machine using Docker:

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/Segniniii/Data-Sanity-Checker.git
    cd Data-Sanity-Checker
    ```

2.  **Build the Docker Image:**
    Ensure Docker Desktop is running. This step builds the application's Docker image, bundling all dependencies (Python, FastAPI, Pandas) and your frontend code into a single, portable unit.
    ```bash
    docker build -t data-sanity-checker .
    ```

3.  **Run the Docker Container:**
    This command starts a new container from your built image, mapping port `8000` on your host machine to port `8000` inside the container.
    ```bash
    docker run -p 8000:8000 --name data-sanity-app --rm data-sanity-checker
    ```
    * `--name data-sanity-app`: Assigns a name to your running container.
    * `--rm`: Automatically removes the container when it exits, keeping your system clean.

    *(Optional: If you prefer to run without Docker, ensure you have Python 3.11+ and the dependencies from `requirements.txt` installed in a virtual environment. Then, navigate to the `Backend` directory and run `uvicorn main:app --reload`)*

---

## 🚀 Usage

1.  **Access the Application:**
    Open your web browser and navigate to: `http://127.0.0.1:8000`

2.  **Upload Your Data:**
    * Drag and drop your CSV or Excel file directly into the designated upload area.
    * Alternatively, click the "Choose File" button to select a file from your system.

3.  **Configure Analysis Parameters (Optional but Recommended for Bias Checks):**
    * **Sensitive Attributes**: Enter a comma-separated list of column names that represent sensitive characteristics (e.g., `Gender, Race, AgeGroup`). These are used for bias detection.
    * **Outcome/Target Column**: Specify the name of your target or outcome column (e.g., `LoanStatus`, `Hired`, `Prediction`). This is crucial for disparity and disparate impact analysis.
    * **Favorable Outcome Value**: If your Outcome Column is categorical (e.g., "Approved"/"Rejected"), specify which value represents a "favorable" or "positive" outcome (e.g., `Approved`, `1`, `True`). This is **required for Disparate Impact Ratio (DIR)** calculation.
    * **Privileged Group Value**: From your sensitive attribute columns, specify the value that represents the "privileged" group against which other groups will be compared for DIR (e.g., `Male`, `White`). This is also **required for DIR calculation**.

4.  **Analyze:**
    Click the "Analyze Data" button. The application will upload your data, process it, and display the results.

5.  **Review the Report:**
    * View summarized alerts for critical issues.
    * Explore detailed data quality checks (missing values, duplicates, data types, statistics, unique value previews).
    * Examine the "Bias Flags" section for insights into potential group imbalances, outcome disparities, and Disparate Impact Ratios.
    * Interact with dynamic charts illustrating data and bias distributions.
    * Click the "Download Report" button to save a comprehensive HTML summary.

---

## 📁 Project Structure

```
Data-Sanity-Checker/
├── Backend/                    # FastAPI backend application
│   ├── main.py                 # Main FastAPI application logic and API endpoints
│   └── requirements.txt        # Python dependencies for the backend
├── Frontend/                   # Frontend web application (HTML, CSS, JavaScript)
│   ├── index.html              # Main HTML page for the user interface
│   ├── script.js               # JavaScript for frontend logic, API calls, and chart rendering
│   └── style.css               # CSS for styling the web application
├── .dockerignore               # Specifies files/directories to exclude from the Docker build context
├── .gitignore                  # Specifies files/directories to be ignored by Git
└── Dockerfile                  # Instructions for building the Docker image of the application
```

---

## 🔧 Configuration (Environment Variables)

| Environment Variable             | Default Value | Description |
|----------------------------------|----------------|-------------|
| `ALLOWED_ORIGINS`                | `*`            | Allowed frontend domains |
| `MISSING_VALUE_THRESHOLD`        | `5.0`          | Missing value alert threshold (%) |
| `DOMINANT_IMBALANCE_THRESHOLD`   | `90.0`         | Dominance alert threshold (%) |
| `RARE_IMBALANCE_THRESHOLD`       | `10.0`         | Rarity alert threshold (%) |
| `DISPARITY_THRESHOLD`            | `20.0`         | Disparity threshold (%) |
| `DIR_THRESHOLD`                  | `0.8`          | Disparate Impact Ratio alert threshold |

Set them using Docker:
```bash
docker run -p 8000:8000 -e ALLOWED_ORIGINS="http://localhost:3000" -e DIR_THRESHOLD="0.7" --name data-sanity-app-custom data-sanity-checker
```

---

## 📊 Analysis Details

### Data Quality Checks
- **Missing Values**: `(count of nulls / total rows) * 100`
- **Duplicates**: `pandas.DataFrame.duplicated().sum()`
- **Data Types**: `pandas` inference
- **Statistics**: `pandas.Series.describe()`
- **Unique Values**: `value_counts().head(10)` if cardinality < 50 or < 50% of total rows

### Bias Detection
- **Imbalance**: `(group count / total non-nulls) * 100` → flag if > DOMINANT or < RARE thresholds
- **Outcome Disparity**: mean of favorable outcomes per group → alert if difference exceeds threshold
- **Disparate Impact Ratio (DIR)**:
  - SR = favorable / total in group
  - DIR = SR_unprivileged / SR_privileged
  - Alert if DIR < DIR_THRESHOLD

---

## 🤝 Contributing

1. Fork the repo
2. Create a branch: `git checkout -b feature/your-feature`
3. Commit: `git commit -m 'feat: Add new feature'`
4. Push: `git push origin feature/your-feature`
5. Open a PR

Follow:
- PEP8, `black`, `ruff`
- Clear commits
- Update docs
- Write tests if needed

---

## 📝 License

MIT License. See `LICENSE` file.

---

## 🐛 Issues and Support

Check [GitHub Issues](https://github.com/Segniniii/Data-Sanity-Checker/issues)

When reporting:
- Describe the issue
- Steps to reproduce
- Expected vs actual
- Attach logs/screenshots
- Share system info

---

## 🔮 Roadmap

Idk freaking know LMAO, im just building withouth clear path here.

---

## 📚 Dependencies

**Backend**
- FastAPI
- pandas
- numpy
- uvicorn
- openpyxl
- python-multipart

**Frontend**
- Chart.js
- HTML, CSS, JS

---

## 📞 Contact

Email: matiassegnini2455@gmail.com  
GitHub: [Segniniii/Data-Sanity-Checker](https://github.com/Segniniii/Data-Sanity-Checker)

---

⚠️ **Disclaimer**: This tool provides indicators — not definitive conclusions — of bias. Always validate with expert analysis.
