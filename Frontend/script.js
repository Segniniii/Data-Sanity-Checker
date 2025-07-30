// Helper function to create a Chart.js bar chart dynamically.
// This function is globally accessible and used to render various data distributions.
function createBarChart(canvasId, labels, data, title, backgroundColor) {
    // Get the 2D rendering context of the canvas HTML element.
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    // If a Chart.js instance already exists on this canvas, destroy it.
    // This is crucial to prevent duplicate charts and ensure the chart is redrawn
    // with new data every time the analysis is run.
    if (Chart.getChart(canvasId)) {
        Chart.getChart(canvasId).destroy();
    }
    
    // Create a new Chart.js bar chart with specified data and options.
    new Chart(ctx, {
        type: 'bar', // Defines the chart type as a bar chart.
        data: {
            labels: labels, // Labels for the X-axis (e.g., column names, unique values).
            datasets: [{
                label: title, // Label for the dataset, usually serving as the chart title.
                data: data,   // The actual data values to be plotted on the Y-axis.
                backgroundColor: backgroundColor || 'rgba(75, 192, 192, 0.6)', // Bar fill color, with a default if not provided.
                borderColor: backgroundColor ? backgroundColor.replace('0.6', '1') : 'rgba(75, 192, 192, 1)', // Bar border color, a darker shade of the fill.
                borderWidth: 1 // Width of the bar border.
            }]
        },
        options: {
            responsive: true,     // Makes the chart resize automatically with its container.
            maintainAspectRatio: false, // Allows the chart to change its aspect ratio for better responsiveness.
            scales: {
                y: {
                    beginAtZero: true // Ensures the Y-axis starts at zero for accurate comparison.
                }
            },
            plugins: {
                legend: {
                    display: false // Hides the legend as the title conveys the dataset's meaning.
                },
                title: {
                    display: true, // Displays the chart title.
                    text: title    // The text of the chart title.
                }
            }
        }
    });
}

// Ensures that the entire HTML document is fully loaded and parsed
// before attempting to access or manipulate any DOM elements.
document.addEventListener('DOMContentLoaded', () => {
    // --- Get References to Key DOM Elements ---
    // These constants hold references to the HTML elements that the script will interact with.
    const dataFileInput = document.getElementById('dataFileInput'); // File input for data upload
    const fileNameSpan = document.getElementById('fileName');       // Span to display selected file name
    const analyzeButton = document.getElementById('analyzeButton'); // Button to trigger data analysis
    const resultsArea = document.getElementById('resultsArea');     // Div to display analysis results
    const sensitiveAttrsInput = document.getElementById('sensitiveAttrsInput'); // Input for sensitive column names
    const outcomeColInput = document.getElementById('outcomeColInput');         // Input for outcome column name
    const downloadReportButton = document.getElementById('downloadReportButton'); // Button to download report

    // NEW REFERENCES for Disparate Impact Ratio (DIR) specific inputs
    const favorableOutcomeInput = document.getElementById('favorableOutcomeInput'); // Input for favorable outcome value
    const privilegedGroupInput = document.getElementById('privilegedGroupInput');   // Input for privileged group value

    // Reference to the upload area for implementing drag-and-drop functionality.
    const uploadArea = document.querySelector('.upload-area');

    // Variable to store the last successfully generated report data received from the backend.
    // This data is used to dynamically generate the displayed report and the downloadable HTML report.
    let lastReportData = null;

    // --- Event Listener for File Input Change ---
    // Fired when a user selects a file using the "Choose File" button.
    dataFileInput.addEventListener('change', (event) => {
        if (event.target.files.length > 0) {
            processFile(event.target.files[0]); // If a file is selected, process it.
        } else {
            // If no file is selected (e.g., user cancels the dialog), reset display.
            fileNameSpan.textContent = 'No file chosen';
            downloadReportButton.style.display = 'none';
        }
    });

    // --- Drag and Drop Event Listeners for the Upload Area ---
    // Prevents the default browser behavior (which would be to open the file)
    // when a draggable item is dragged over the element. Allows for custom drop handling.
    uploadArea.addEventListener('dragover', (event) => {
        event.preventDefault(); 
        uploadArea.classList.add('drag-over'); // Add a visual indicator (CSS class) when dragging over.
    });

    // Removes the visual indicator when the dragged item leaves the area.
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('drag-over');
    });

    // Handles the file drop event.
    uploadArea.addEventListener('drop', (event) => {
        event.preventDefault(); // Prevent default browser behavior (e.g., opening file in new tab).
        uploadArea.classList.remove('drag-over'); // Remove drag-over visual indicator.

        const files = event.dataTransfer.files; // Get the dropped files.
        if (files.length > 0) {
            dataFileInput.files = files; // Assign the dropped file to the hidden input for consistent processing.
            processFile(files[0]);       // Process the first dropped file.
        }
    });
    // --- End Drag and Drop Event Listeners ---

    // Centralized function to handle file selection or drop events.
    function processFile(file) {
        if (file) {
            fileNameSpan.textContent = file.name; // Display the name of the chosen file to the user.
            downloadReportButton.style.display = 'none'; // Hide the download button until analysis is complete.
            // Uncomment the line below if you want automatic analysis upon file selection/drop.
            // analyzeButton.click(); 
        } else {
            fileNameSpan.textContent = 'No file chosen';
            downloadReportButton.style.display = 'none';
        }
    }

    // --- Event Listener for the "Analyze Data" Button Click ---
    // This is the main trigger for sending data to the backend for analysis.
    analyzeButton.addEventListener('click', async () => {
        const file = dataFileInput.files[0]; // Get the currently selected file.

        // Basic validation: Check if a file has been selected.
        if (!file) {
            resultsArea.innerHTML = '<p style="color: red;">Please select a file first!</p>';
            downloadReportButton.style.display = 'none';
            return; // Stop execution if no file is selected.
        }

        // Provide immediate feedback to the user while processing.
        resultsArea.innerHTML = '<p>Uploading and analyzing data... Please wait.</p>';
        downloadReportButton.style.display = 'none'; // Ensure download button is hidden during analysis.
        console.log('Sending file:', file.name);

        // Prepare the form data for the API request.
        // FormData is used to send file uploads and other form fields via POST.
        const formData = new FormData();
        formData.append('file', file); // Append the selected file.

        // Get and process input values for sensitive attributes and outcome column.
        const sensitiveAttrs = sensitiveAttrsInput.value.split(',').map(s => s.trim()).filter(s => s.length > 0);
        const outcomeCol = outcomeColInput.value.trim();

        // Append sensitive attributes (as a JSON string) to form data if provided.
        if (sensitiveAttrs.length > 0) {
            formData.append('sensitive_attributes', JSON.stringify(sensitiveAttrs));
        }
        // Append outcome column to form data if provided.
        if (outcomeCol) {
            formData.append('outcome_column', outcomeCol);
        }

        // NEW: Append Favorable Outcome Value and Privileged Group Value.
        // These are crucial for Disparate Impact Ratio (DIR) calculations.
        const favorableOutcomeVal = favorableOutcomeInput.value.trim();
        const privilegedGroupVal = privilegedGroupInput.value.trim();

        if (favorableOutcomeVal) {
            formData.append('favorable_outcome_value', favorableOutcomeVal);
        }
        if (privilegedGroupVal) {
            formData.append('privileged_group_value', privilegedGroupVal);
        }
        
        try {
            // Send the data to the backend API using the fetch API.
            const response = await fetch('http://127.0.0.1:8000/analyze-data/', {
                method: 'POST', // Use POST method for file uploads.
                body: formData, // The prepared FormData object.
            });

            // Handle successful API response (HTTP status 2xx).
            if (response.ok) {
                const data = await response.json(); // Parse the JSON response body.
                lastReportData = data; // Store the received report data for future download.
                console.log('Backend response (full report):', data); // Log the full response for debugging.

                // --- Build the HTML content to display the analysis results ---
                let htmlContent = `
                    <p style="color: green;"><strong>Success!</strong> ${data.message}</p>
                    <h3>File Details:</h3>
                    <ul>
                        <li>Rows: ${data.file_details.rows}</li>
                        <li>Columns: ${data.file_details.columns}</li>
                        <li>Column Names: ${data.file_details.column_names.join(', ')}</li>
                    </ul>
                `;

                // --- Summary of Alerts Section ---
                // Displays high-level critical alerts found during data quality and bias checks.
                if (data.summary_alerts && data.summary_alerts.length > 0) {
                    htmlContent += `<h3>Summary of Alerts:</h3><ul class="alerts-list">`;
                    data.summary_alerts.forEach(alert => {
                        let alertClass = '';
                        // Assign CSS classes based on alert type for visual distinction.
                        if (alert.type.includes('Missing')) alertClass = 'warning-flag';
                        else if (alert.type.includes('Duplicate')) alertClass = 'info-flag';
                        else if (alert.type.includes('Bias')) alertClass = 'critical-flag'; // Catches Disparity and Disparate Impact alerts
                        else if (alert.type.includes('Info')) alertClass = 'info-flag'; // General information alerts

                        htmlContent += `<li class="${alertClass}"><strong>${alert.type}:</strong> ${alert.message}</li>`;
                    });
                    htmlContent += `</ul>`;
                } else {
                    htmlContent += `<h3>Summary of Alerts:</h3><p>No critical alerts detected in your data.</p>`;
                }
                // --- End Summary of Alerts Section ---

                // --- Data Quality Checks Display ---
                htmlContent += `<h3>Data Quality Checks:</h3>`;

                // Missing Values: Displays count and percentage of missing values per column.
                if (Object.keys(data.quality_checks.missing_values).length > 0) {
                    htmlContent += `<h4>Missing Values:</h4><ul>`;
                    for (const col in data.quality_checks.missing_values) {
                        const mv = data.quality_checks.missing_values[col];
                        htmlContent += `<li><strong>${col}:</strong> ${mv.count} missing (${mv.percentage}%)</li>`;
                    }
                    htmlContent += `</ul>`;
                    // Placeholder for Missing Values Chart. Chart will be rendered dynamically after HTML is set.
                    htmlContent += `<div class="chart-container"><canvas id="missingValuesChart"></canvas></div>`;
                } else {
                    htmlContent += `<p>No missing values detected.</p>`;
                }

                // Duplicate Rows: Displays the total count of exact duplicate rows.
                htmlContent += `<h4>Duplicate Rows:</h4>`;
                if (data.quality_checks.duplicate_rows > 0) {
                    htmlContent += `<p><strong>${data.quality_checks.duplicate_rows}</strong> exact duplicate rows detected.</p>`;
                } else {
                    htmlContent += `<p>No duplicate rows detected.</p>`;
                }

                // Column Data Types: Lists the inferred data type for each column.
                htmlContent += `<h4>Column Data Types:</h4><ul>`;
                for (const col in data.quality_checks.column_data_types) {
                    htmlContent += `<li><strong>${col}:</strong> ${data.quality_checks.column_data_types[col]}</li>`;
                }
                htmlContent += `</ul>`;

                // Column Statistics (for numeric columns): Displays descriptive statistics like mean, std dev, min, max.
                if (Object.keys(data.quality_checks.column_statistics).length > 0) {
                    htmlContent += `<h4>Numeric Column Statistics:</h4>`;
                    for (const col in data.quality_checks.column_statistics) {
                        const stats = data.quality_checks.column_statistics[col];
                        htmlContent += `<h5>${col}:</h5><ul>`;
                        for (const stat in stats) {
                            // Format numeric statistics to two decimal places for readability.
                            htmlContent += `<li><strong>${stat}:</strong> ${stats[stat].toFixed(2)}</li>`;
                        }
                        htmlContent += `</ul>`;
                    }
                } else {
                    htmlContent += `<p>No numeric columns for statistics.</p>`;
                }

                // Unique Values Preview (for low cardinality columns, with charts):
                // Shows the top 10 most frequent unique values and their counts for categorical or low-cardinality columns.
                if (Object.keys(data.quality_checks.unique_values_preview).length > 0) {
                    htmlContent += `<h4>Unique Values Preview (Low Cardinality Columns):</h4>`;
                    for (const col in data.quality_checks.unique_values_preview) {
                        const unique_vals = data.quality_checks.unique_values_preview[col];
                        htmlContent += `<h5>${col}:</h5><ul>`;
                        for (const val in unique_vals) {
                            htmlContent += `<li><strong>"${val}"</strong>: ${unique_vals[val]} occurrences</li>`;
                        }
                        htmlContent += `</ul>`;
                        // Create a unique canvas ID for each chart to avoid conflicts.
                        const canvasId = `uniqueValuesChart_${col.replace(/[^a-zA-Z0-9]/g, '_')}`;
                        htmlContent += `<div class="chart-container"><canvas id="${canvasId}"></canvas></div>`;
                    }
                } else {
                    htmlContent += `<p>No low cardinality columns to preview unique values.</p>`;
                }

                // --- Bias Flags Display ---
                // This section details potential biases detected based on sensitive attributes and outcome.
                htmlContent += `<h3>Bias Flags:</h3>`;

                // Determine if there are any bias flags to display (excluding internal '_' prefixed keys).
                const hasBiasFlags = Object.keys(data.bias_flags).some(key => !key.startsWith('_') && data.bias_flags[key].length > 0) || 
                                     (data.bias_flags._info && data.bias_flags._info.length > 0) ||
                                     (data.bias_flags._error && data.bias_flags._error.length > 0);

                if (hasBiasFlags) {
                    // Display general information or error messages related to bias flagging first.
                    if (data.bias_flags && data.bias_flags._info && data.bias_flags._info.length > 0) {
                        htmlContent += `<h4>General Bias-Related Information:</h4><ul>`;
                        data.bias_flags._info.forEach(info => {
                            htmlContent += `<li class="info-flag"><strong>${info.type}:</strong> ${info.message}</li>`;
                        });
                        htmlContent += `</ul>`;
                    }
                    if (data.bias_flags && data.bias_flags._error && data.bias_flags._error.length > 0) {
                         htmlContent += `<h4>Bias Input Errors:</h4><ul class="alerts-list">`;
                         data.bias_flags._error.forEach(err => {
                             htmlContent += `<li class="critical-flag"><strong>${err.type}:</strong> ${err.message}</li>`;
                         });
                         htmlContent += `</ul>`;
                    }

                    // Iterate through each sensitive attribute for specific bias flags.
                    for (const attr in data.bias_flags) {
                        if (attr.startsWith('_')) continue; // Skip internal backend keys.

                        const flags = data.bias_flags[attr];
                        if (flags.length === 0) continue; // Skip if no specific flags for this attribute.

                        htmlContent += `<h4>Potential Bias in "${attr}":</h4><ul>`;
                        
                        // NEW FIX FOR "DIR Summary: undefined" issue and better rendering
                        let dirSummaryDisplayedForAttr = false; 

                        flags.forEach(flag => {
                            let flagClass = '';
                            // Assign CSS classes based on flag type for visual emphasis.
                            if (flag.type === 'Imbalance') flagClass = 'warning-flag';
                            else if (flag.type === 'Disparity') flagClass = 'critical-flag';
                            else if (flag.type === 'Bias Disparate Impact') flagClass = 'critical-flag';
                            else if (flag.type.includes('Info')) flagClass = 'info-flag';
                            else if (flag.type.includes('Warning')) flagClass = 'warning-flag'; // For backend-generated DIR warnings

                            // Render the main flag message.
                            htmlContent += `<li class="${flagClass}"><strong>${flag.type}:</strong> ${flag.message}</li>`;

                            // Handle Disparate Impact Ratio (DIR) summary details.
                            // This part displays selection rates and the calculated ratio.
                            // Ensure it's only rendered once per attribute and has details.
                            if (flag.type === 'DIR Summary' && flag.details && !dirSummaryDisplayedForAttr) {
                                htmlContent += `<ul>`;
                                htmlContent += `<li><strong>Privileged Group:</strong> ${flag.details.privileged_group}</li>`;
                                htmlContent += `<li><strong>Selection Rates:</strong>`;
                                for (const group in flag.details.selection_rates) {
                                    htmlContent += `<div>- '${group}': ${flag.details.selection_rates[group]}%</div>`;
                                }
                                htmlContent += `</li>`;
                                // Display individual DIR comparisons (e.g., DIR_vs_Female).
                                for (const key in flag.details) {
                                    if (key.startsWith("DIR_vs_")) {
                                        const groupName = key.replace("DIR_vs_", "");
                                        const dirValue = flag.details[key];
                                        // Apply critical-flag class if DIR is below 0.8 threshold.
                                        let dirComparisonClass = dirValue < 0.8 ? 'critical-flag' : ''; 
                                        htmlContent += `<li class="${dirComparisonClass}"><strong>Disparate Impact Ratio (for '${groupName}' vs '${flag.details.privileged_group}'):</strong> ${dirValue.toFixed(2)}</li>`;
                                    }
                                }
                                htmlContent += `</ul>`;
                                dirSummaryDisplayedForAttr = true; // Mark as rendered to prevent re-rendering for this attribute.
                            }
                        });
                        htmlContent += `</ul>`;

                        // If distribution data is available for this sensitive attribute, add a chart placeholder.
                        if (data.quality_checks.unique_values_preview && data.quality_checks.unique_values_preview[attr]) {
                            const biasCanvasId = `biasChart_${attr.replace(/[^a-zA-Z0-9]/g, '_')}`;
                            htmlContent += `<div class="chart-container"><canvas id="${biasCanvasId}"></canvas></div>`;
                        }
                    }
                } else {
                    htmlContent += `<p>No specific bias flags detected based on the provided sensitive attributes and outcome column.</p>`;
                }
                // General note on the complexity of bias detection.
                htmlContent += `<p style="font-size: 0.9em; color: #666;"><em>Note: Bias detection is complex. These are flags for further investigation, not definitive proof of bias.</em></p>`;

                // Set the innerHTML of the results area. This must happen BEFORE drawing charts
                // so that the canvas elements exist in the DOM for Chart.js to find them.
                resultsArea.innerHTML = htmlContent;

                // --- Call Chart Rendering Functions AFTER HTML content is set ---
                const currentData = lastReportData; // Use the stored data for charts.

                // 1. Render Missing Values Chart: Displays a bar chart of missing value percentages per column.
                if (Object.keys(currentData.quality_checks.missing_values).length > 0) {
                    const labels = Object.keys(currentData.quality_checks.missing_values);
                    const percentages = labels.map(col => currentData.quality_checks.missing_values[col].percentage);
                    createBarChart('missingValuesChart', labels, percentages, 'Percentage of Missing Values', 'rgba(255, 159, 64, 0.6)');
                }

                // 2. Render Unique Values Preview Charts: Displays bar charts for the distribution of unique values
                //    in low-cardinality columns.
                if (Object.keys(currentData.quality_checks.unique_values_preview).length > 0) {
                    for (const col in currentData.quality_checks.unique_values_preview) {
                        const unique_vals = currentData.quality_checks.unique_values_preview[col];
                        const labels = Object.keys(unique_vals);
                        const counts = Object.values(unique_vals);
                        const canvasId = `uniqueValuesChart_${col.replace(/[^a-zA-Z0-9]/g, '_')}`;
                        createBarChart(canvasId, labels, counts, `Distribution of "${col}"`, 'rgba(54, 162, 235, 0.6)');
                    }
                }

                // 3. Render Bias Attribute Distribution Charts: Displays bar charts for the distribution of sensitive attributes.
                //    This reuses the unique_values_preview data for sensitive columns.
                if (Object.keys(currentData.bias_flags).length > 0) {
                    for (const attr in currentData.bias_flags) {
                        if (attr.startsWith('_')) continue; // Skip internal keys.
                        // Only draw a chart if unique value data is available for the sensitive attribute.
                        if (currentData.quality_checks.unique_values_preview && currentData.quality_checks.unique_values_preview[attr]) {
                            const unique_vals = currentData.quality_checks.unique_values_preview[attr];
                            const labels = Object.keys(unique_vals);
                            const counts = Object.values(unique_vals);
                            const biasCanvasId = `biasChart_${attr.replace(/[^a-zA-Z0-9]/g, '_')}`;
                            createBarChart(biasCanvasId, labels, counts, `Distribution of Sensitive Attribute: "${attr}"`, 'rgba(255, 99, 132, 0.6)');
                        }
                    }
                }
                downloadReportButton.style.display = 'block'; // Show the download button after successful analysis.

            } else {
                // Handle API errors where response.ok is false (e.g., HTTP 4xx or 5xx from backend).
                const errorData = await response.json(); // Attempt to parse error details from JSON response.
                resultsArea.innerHTML = `<p style="color: red;">Error: ${errorData.detail || response.statusText}</p>`;
                console.error('Backend error:', errorData); // Log the error for debugging.
                downloadReportButton.style.display = 'none'; // Hide download button on error.
            }
        } catch (error) {
            // Catch any network errors (e.g., server unreachable) or unexpected fetch-related errors.
            resultsArea.innerHTML = `<p style="color: red;">Network error or server unavailable: ${error.message}. Please check console for details.</p>`;
            console.error('Fetch error:', error); // Log the detailed fetch error.
            downloadReportButton.style.display = 'none'; // Hide download button on error.
        }
    });

    // --- Event listener for Download Report Button ---
    // Allows the user to download the currently displayed analysis report as an HTML file.
    downloadReportButton.addEventListener('click', () => {
        // Ensure analysis has been run and report data is available before attempting download.
        if (!lastReportData) {
            alert("Please run an analysis first to generate a report.");
            return;
        }

        // Get the current HTML content displayed in the results area.
        const reportContent = resultsArea.innerHTML; 
        // Generate a dynamic filename for the downloaded report (e.g., data_sanity_report_2025-07-29.html).
        const filename = `data_sanity_report_${new Date().toISOString().slice(0, 10)}.html`; 

        // Construct the full HTML document for the downloadable report.
        // It includes basic inline styles for self-containment and a note about charts being static.
        const fullHtml = `
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Data Sanity Report</title>
                <style>
                    /* Basic inline styles for the downloaded report for self-containment.
                        These should largely mirror key styles from style.css. */
                    body { font-family: 'Arial', sans-serif; line-height: 1.6; color: #333; margin: 20px; }
                    .container { max-width: 900px; margin: auto; padding: 20px; border: 1px solid #eee; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
                    h1, h2, h3, h4, h5 { color: #2c3e50; margin-top: 20px; margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 5px; }
                    ul { list-style-type: disc; margin-left: 20px; }
                    li { margin-bottom: 5px; }
                    .chart-container { width: 100%; max-width: 600px; height: 300px; margin: 20px auto; padding: 15px; background-color: #f0f0f0; border-radius: 8px; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05); }
                    .alerts-list { list-style-type: disc; padding-left: 25px; margin-bottom: 20px; text-align: left; }
                    .alerts-list li { margin-bottom: 8px; font-size: 1.1em; line-height: 1.4; }
                    .warning-flag { color: orange; font-weight: bold; }
                    .critical-flag { color: red; font-weight: bold; }
                    .info-flag { color: #007bff; font-weight: bold; }
                    .chart-note { font-size: 0.8em; color: #777; text-align: center; margin-top: 5px;}

                    /* Hide interactive elements in the downloaded report to make it look like a static document */
                    .download-button, .analyze-button, .upload-area, .input-group { display: none !important; }
                </style>
                <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            </head>
            <body>
                <div class="container">
                    <h1>Data Sanity Report</h1>
                    <p>Generated on: ${new Date().toLocaleString()}</p>
                    ${reportContent} <p class="chart-note">Note: Charts are interactive on the live webpage. In this downloaded report, they are static representations.</p>
                </div>
            </body>
            </html>
        `;

        // Create a Blob (Binary Large Object) containing the constructed HTML content.
        const blob = new Blob([fullHtml], { type: 'text/html' });
        // Create a URL representing the Blob data.
        const url = URL.createObjectURL(blob);

        // Create a temporary anchor (<a>) element to trigger the download.
        const a = document.createElement('a');
        a.href = url;               // Set the href to the Blob URL.
        a.download = filename;      // Set the desired download filename.
        document.body.appendChild(a); // Append to the body (necessary for some browsers like Firefox).
        a.click();                  // Programmatically click the anchor to start the download.
        document.body.removeChild(a); // Clean up the temporary anchor element.
        URL.revokeObjectURL(url);   // Release the object URL to allow garbage collection.
    });
});