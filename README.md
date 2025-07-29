# 📊 Data Sanity Checker

A comprehensive web-based tool for analyzing data quality and detecting potential bias in tabular datasets. Upload your CSV or Excel files to get instant insights into data integrity, missing values, duplicates, and potential bias across sensitive attributes.

## 🚀 Features

### Data Quality Analysis
- **Missing Values Detection**: Identify and visualize missing data patterns  
- **Duplicate Row Detection**: Find exact duplicate entries in your dataset  
- **Data Type Analysis**: Automatic detection and validation of column data types  
- **Statistical Summary**: Comprehensive statistics for numeric columns  
- **Distribution Analysis**: Visual representation of categorical data distributions  

### Bias Detection
- **Sensitive Attribute Analysis**: Check for imbalances in protected characteristics  
- **Outcome Disparity Detection**: Identify significant differences in outcomes across groups  
- **Representation Analysis**: Flag underrepresented or overrepresented groups  
- **Interactive Visualizations**: Charts showing distributions and potential bias patterns  

### User Experience
- **Drag & Drop Interface**: Easy file upload with drag-and-drop support  
- **Interactive Charts**: Powered by Chart.js for clear data visualization  
- **Downloadable Reports**: Generate and download comprehensive HTML reports  
- **Real-time Analysis**: Instant feedback and processing status

<img width="688" height="538" alt="image" src="https://github.com/user-attachments/assets/9c69f0e6-073e-440f-8f50-f43d8217a7b3" />
<img width="621" height="705" alt="image" src="https://github.com/user-attachments/assets/8efdee7b-3f1d-489c-85ed-80f1f86122f5" />


## 📋 Prerequisites

- Python 3.7+  
- Modern web browser (Chrome, Firefox, Safari, Edge)

## 🛠️ Installation

```bash
git clone https://github.com/Segniniii/Data-Sanity-Checker.git
cd Data-Sanity-Checker
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

## 🚀 Usage

```bash
cd Backend
uvicorn main:app --reload
```

Server runs on: http://127.0.0.1:8000

Open browser and go to the app.

**Upload your data:**
- Drag and drop your CSV or Excel file  
- Or click "Choose File"

**Configure analysis (optional):**
- **Sensitive Attributes**: comma-separated column names (e.g., gender, race)  
- **Outcome Column**: specify a target column (e.g., hired, approved)

**Analyze:**
- Click "Analyze Data"

**Review:**
- View alerts  
- Interactive charts  
- Download the report  

## 📁 Project Structure

```
Data-Sanity-Checker/
├── Backend/
│   ├── main.py
│   └── requirements.txt
├── Frontend/
│   ├── index.html
│   ├── script.js
│   └── style.css

```

## 🔧 Configuration

**Backend (main.py):**
- CORS enabled for development  
- Accepts CSV and Excel files  
- Thresholds are adjustable  

**Frontend (script.js):**
- API: http://127.0.0.1:8000/analyze-data/  
- Uses Chart.js  
- Validates file type  

## 📊 Analysis Details

**Quality Checks:**
- Missing values > 5%  
- Duplicate rows  
- Data type mismatches  
- Summary stats for numbers  
- Value counts for categoricals  

**Bias Detection:**
- Imbalance flags if group >90% or <10%  
- Outcome disparity >20% points  
- Highlights underrepresentation  

## 🤝 Contributing

- Fork repo  
- Create branch: `git checkout -b feature/amazing-feature`  
- Commit: `git commit -m 'Add amazing feature'`  
- Push: `git push origin feature/amazing-feature`  
- Open Pull Request  

**Guidelines:**
- Follow PEP 8  
- Use clear commit messages  
- Comment complex logic  
- Add tests  
- Update docs  

## 📝 License

MIT License

## 🐛 Issues and Support

- Check GitHub Issues  
- Or create a new one with:  
  - Problem description  
  - Steps to reproduce  
  - Expected vs actual behavior  
  - System info (OS, Python, browser)

## 🔮 Roadmap

? 

## 📚 Dependencies

**Backend:**  
- FastAPI  
- pandas  
- python-multipart  
- uvicorn  

**Frontend:**  
- Chart.js  
- Vanilla JavaScript  

## 📞 Contact

- Email: matiassegnini2455@gmail.com  
- GitHub Issues & Discussions

> ⚠️ *Note: This tool surfaces signals, not definitive conclusions. Always validate results with expert review.*
