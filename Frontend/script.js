// Helper function to create a Chart.js bar chart.
// This function is designed to be globally accessible as it's used for rendering
// charts dynamically within the main application's display area.
function createBarChart(canvasId, labels, data, title, backgroundColor) {
    // Get the 2D rendering context of the canvas element.
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    // If a chart instance already exists on this canvas, destroy it to prevent duplicates
    // and ensure the chart is redrawn with new data.
    if (Chart.getChart(canvasId)) {
        Chart.getChart(canvasId).destroy();
    }
    
    // Create a new Chart.js bar chart.
    new Chart(ctx, {
        type: 'bar', // Specifies the chart type as a bar chart.
        data: {
            labels: labels, // Labels for the x-axis (e.g., column names, unique values).
            datasets: [{
                label: title, // Label for the dataset, often the chart title.
                data: data,   // The actual data values to be plotted.
                backgroundColor: backgroundColor || 'rgba(75, 192, 192, 0.6)', // Bar fill color, with a default if not provided.
                borderColor: backgroundColor ? backgroundColor.replace('0.6', '1') : 'rgba(75, 192, 192, 1)', // Bar border color, a darker shade of fill color.
                borderWidth: 1 // Width of the bar border.
            }]
        },
        options: {
            responsive: true,     // Makes the chart responsive to container size changes.
            maintainAspectRatio: false, // Allows the chart to change aspect ratio for better responsiveness.
            scales: {
                y: {
                    beginAtZero: true // Ensures the y-axis starts at zero for accurate comparison.
                }
            },
            plugins: {
                legend: {
                    display: false // Hides the legend as the title serves the purpose.
                },
                title: {
                    display: true, // Displays the chart title.
                    text: title    // The text of the chart title.
                }
            }
        }
    });
}

// Ensure the DOM is fully loaded before attempting to access and manipulate elements.
document.addEventListener('DOMContentLoaded', () => {
    // Get references to key DOM elements used for user interaction and displaying results.
    const dataFileInput = document.getElementById('dataFileInput');
    const fileNameSpan = document.getElementById('fileName');
    const analyzeButton = document.getElementById('analyzeButton');
    const resultsArea = document.getElementById('resultsArea');
    const sensitiveAttrsInput = document.getElementById('sensitiveAttrsInput');
    const outcomeColInput = document.getElementById('outcomeColInput');
    const downloadReportButton = document.getElementById('downloadReportButton');

    // Get reference to the upload area for drag and drop functionality.
    const uploadArea = document.querySelector('.upload-area');

    // Variable to store the last successfully generated report data.
    // This data is used when generating the downloadable HTML report.
    let lastReportData = null;

    // Event listener for when a file is selected via the input button.
    dataFileInput.addEventListener('change', (event) => {
        if (event.target.files.length > 0) {
            processFile(event.target.files[0]); // Process the selected file.
        } else {
            // Reset display if no file is chosen.
            fileNameSpan.textContent = 'No file chosen';
            downloadReportButton.style.display = 'none';
        }
    });

    // --- Drag and Drop Event Listeners ---
    // Prevent default browser behavior for dragover to allow dropping files.
    uploadArea.addEventListener('dragover', (event) => {
        event.preventDefault(); 
        uploadArea.classList.add('drag-over'); // Add a visual indicator for drag-over state.
    });

    // Remove drag-over indicator when the dragged item leaves the area.
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('drag-over');
    });

    // Handle the file drop event.
    uploadArea.addEventListener('drop', (event) => {
        event.preventDefault(); // Prevent default browser behavior (e.g., opening file).
        uploadArea.classList.remove('drag-over'); // Remove drag-over indicator.

        const files = event.dataTransfer.files; // Get the dropped files.
        if (files.length > 0) {
            dataFileInput.files = files; // Assign the dropped file to the hidden input for consistency.
            processFile(files[0]); // Process the first dropped file.
        }
    });
    // --- End Drag and Drop Event Listeners ---

    // Centralized function to handle file selection/drop.
    function processFile(file) {
        if (file) {
            fileNameSpan.textContent = file.name; // Display the name of the selected file.
            downloadReportButton.style.display = 'none'; // Hide download button until analysis is complete.
            // Uncomment the line below if you want automatic analysis upon file selection/drop.
            // analyzeButton.click(); 
        } else {
            fileNameSpan.textContent = 'No file chosen';
            downloadReportButton.style.display = 'none';
        }
    }

    // Event listener for the "Analyze Data" button click.
    analyzeButton.addEventListener('click', async () => {
        const file = dataFileInput.files[0]; // Get the selected file.

        // Validate if a file has been selected.
        if (!file) {
            resultsArea.innerHTML = '<p style="color: red;">Please select a file first!</p>';
            downloadReportButton.style.display = 'none';
            return;
        }

        // Provide immediate feedback to the user.
        resultsArea.innerHTML = '<p>Uploading and analyzing data... Please wait.</p>';
        downloadReportButton.style.display = 'none'; // Hide download button during analysis.
        console.log('Sending file:', file.name);

        // Prepare the form data for the API request.
        const formData = new FormData();
        formData.append('file', file);

        // Parse sensitive attributes and outcome column from input fields.
        const sensitiveAttrs = sensitiveAttrsInput.value.split(',').map(s => s.trim()).filter(s => s.length > 0);
        const outcomeCol = outcomeColInput.value.trim();

        // Append sensitive attributes (as a JSON string) and outcome column to form data if provided.
        if (sensitiveAttrs.length > 0) {
            formData.append('sensitive_attributes', JSON.stringify(sensitiveAttrs));
        }
        if (outcomeCol) {
            formData.append('outcome_column', outcomeCol);
        }
        
        try {
            // Send the data to the backend API.
            const response = await fetch('http://127.0.0.1:8000/analyze-data/', {
                method: 'POST',
                body: formData,
            });

            // Handle successful API response.
            if (response.ok) {
                const data = await response.json();
                lastReportData = data; // Store the received report data for future download.
                console.log('Backend response (full report):', data);

                // Build the HTML content to display the analysis results.
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
                if (data.summary_alerts && data.summary_alerts.length > 0) {
                    htmlContent += `<h3>Summary of Alerts:</h3><ul class="alerts-list">`;
                    data.summary_alerts.forEach(alert => {
                        let alertClass = '';
                        // Assign CSS classes based on alert type for visual distinction.
                        if (alert.type.includes('Missing')) alertClass = 'warning-flag';
                        else if (alert.type.includes('Duplicate')) alertClass = 'info-flag';
                        else if (alert.type.includes('Bias')) alertClass = 'critical-flag';

                        htmlContent += `<li class="${alertClass}"><strong>${alert.type}:</strong> ${alert.message}</li>`;
                    });
                    htmlContent += `</ul>`;
                } else {
                    htmlContent += `<h3>Summary of Alerts:</h3><p>No critical alerts detected in your data.</p>`;
                }
                // --- End Summary of Alerts Section ---

                // --- Data Quality Checks Display ---
                htmlContent += `<h3>Data Quality Checks:</h3>`;

                // Missing Values
                if (Object.keys(data.quality_checks.missing_values).length > 0) {
                    htmlContent += `<h4>Missing Values:</h4><ul>`;
                    for (const col in data.quality_checks.missing_values) {
                        const mv = data.quality_checks.missing_values[col];
                        htmlContent += `<li><strong>${col}:</strong> ${mv.count} missing (${mv.percentage}%)</li>`;
                    }
                    htmlContent += `</ul>`;
                    // Placeholder for Missing Values Chart.
                    htmlContent += `<div class="chart-container"><canvas id="missingValuesChart"></canvas></div>`;
                } else {
                    htmlContent += `<p>No missing values detected.</p>`;
                }

                // Duplicate Rows
                htmlContent += `<h4>Duplicate Rows:</h4>`;
                if (data.quality_checks.duplicate_rows > 0) {
                    htmlContent += `<p><strong>${data.quality_checks.duplicate_rows}</strong> duplicate rows detected.</p>`;
                } else {
                    htmlContent += `<p>No duplicate rows detected.</p>`;
                }

                // Column Data Types
                htmlContent += `<h4>Column Data Types:</h4><ul>`;
                for (const col in data.quality_checks.column_data_types) {
                    htmlContent += `<li><strong>${col}:</strong> ${data.quality_checks.column_data_types[col]}</li>`;
                }
                htmlContent += `</ul>`;

                // Column Statistics (for numeric columns)
                if (Object.keys(data.quality_checks.column_statistics).length > 0) {
                    htmlContent += `<h4>Numeric Column Statistics:</h4>`;
                    for (const col in data.quality_checks.column_statistics) {
                        const stats = data.quality_checks.column_statistics[col];
                        htmlContent += `<h5>${col}:</h5><ul>`;
                        for (const stat in stats) {
                            // Format numeric stats to two decimal places.
                            htmlContent += `<li><strong>${stat}:</strong> ${stats[stat].toFixed(2)}</li>`;
                        }
                        htmlContent += `</ul>`;
                    }
                } else {
                    htmlContent += `<p>No numeric columns for statistics.</p>`;
                }

                // Unique Values Preview (for low cardinality columns, with charts)
                if (Object.keys(data.quality_checks.unique_values_preview).length > 0) {
                    htmlContent += `<h4>Unique Values Preview (Low Cardinality Columns):</h4>`;
                    for (const col in data.quality_checks.unique_values_preview) {
                        const unique_vals = data.quality_checks.unique_values_preview[col];
                        htmlContent += `<h5>${col}:</h5><ul>`;
                        for (const val in unique_vals) {
                            htmlContent += `<li><strong>"${val}"</strong>: ${unique_vals[val]} occurrences</li>`;
                        }
                        htmlContent += `</ul>`;
                        // Create a unique canvas ID for each chart.
                        const canvasId = `uniqueValuesChart_${col.replace(/[^a-zA-Z0-9]/g, '_')}`;
                        htmlContent += `<div class="chart-container"><canvas id="${canvasId}"></canvas></div>`;
                    }
                } else {
                    htmlContent += `<p>No low cardinality columns to preview unique values.</p>`;
                }

                // --- Bias Flags Display ---
                htmlContent += `<h3>Bias Flags:</h3>`;

                // Check if any actual bias flags (excluding internal `_` prefixed keys) exist.
                const actualBiasFlagsExist = Object.keys(data.bias_flags).filter(key => !key.startsWith('_')).length > 0;

                if (actualBiasFlagsExist) {
                    for (const attr in data.bias_flags) {
                        if (attr.startsWith('_')) continue; // Skip internal keys.
                        const flags = data.bias_flags[attr];
                        htmlContent += `<h4>Potential Bias in "${attr}":</h4><ul>`;
                        flags.forEach(flag => {
                            let flagClass = '';
                            // Assign CSS classes based on flag type.
                            if (flag.type === 'Imbalance') flagClass = 'warning-flag';
                            else if (flag.type === 'Disparity') flagClass = 'critical-flag';
                            htmlContent += `<li class="${flagClass}"><strong>${flag.type}:</strong> ${flag.message}</li>`;
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
                htmlContent += `<p style="font-size: 0.9em; color: #666;"><em>Note: Bias detection is complex. These are flags for further investigation, not definitive proof of bias.</em></p>`;

                // Set the innerHTML of the results area. This must happen BEFORE drawing charts
                // so that the canvas elements exist in the DOM.
                resultsArea.innerHTML = htmlContent;

                // --- Call Chart Rendering Functions AFTER HTML content is set ---
                const currentData = lastReportData; // Use the stored data for charts.

                // 1. Render Missing Values Chart
                if (Object.keys(currentData.quality_checks.missing_values).length > 0) {
                    const labels = Object.keys(currentData.quality_checks.missing_values);
                    const percentages = labels.map(col => currentData.quality_checks.missing_values[col].percentage);
                    createBarChart('missingValuesChart', labels, percentages, 'Percentage of Missing Values', 'rgba(255, 159, 64, 0.6)');
                }

                // 2. Render Unique Values Preview Charts
                if (Object.keys(currentData.quality_checks.unique_values_preview).length > 0) {
                    for (const col in currentData.quality_checks.unique_values_preview) {
                        const unique_vals = currentData.quality_checks.unique_values_preview[col];
                        const labels = Object.keys(unique_vals);
                        const counts = Object.values(unique_vals);
                        const canvasId = `uniqueValuesChart_${col.replace(/[^a-zA-Z0-9]/g, '_')}`;
                        createBarChart(canvasId, labels, counts, `Distribution of "${col}"`, 'rgba(54, 162, 235, 0.6)');
                    }
                }

                // 3. Render Bias Attribute Distribution Charts (reusing unique_values_preview data for sensitive attributes)
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
                downloadReportButton.style.display = 'block'; // Show the download button.

            } else {
                // Handle API errors.
                const errorData = await response.json();
                resultsArea.innerHTML = `<p style="color: red;">Error: ${errorData.detail || response.statusText}</p>`;
                console.error('Backend error:', errorData);
                downloadReportButton.style.display = 'none';
            }
        } catch (error) {
            // Handle network or other fetch-related errors.
            resultsArea.innerHTML = `<p style="color: red;">Network error or server unavailable: ${error.message}</p>`;
            console.error('Fetch error:', error);
            downloadReportButton.style.display = 'none';
        }
    });

    // --- Event listener for Download Report Button ---
    downloadReportButton.addEventListener('click', () => {
        // Ensure analysis has been run and data is available.
        if (!lastReportData) {
            alert("Please run an analysis first to generate a report.");
            return;
        }

        // Get the current HTML content displayed in the results area.
        const reportContent = resultsArea.innerHTML; 
        // Generate a dynamic filename for the downloaded report.
        const filename = `data_sanity_report_${new Date().toISOString().slice(0, 10)}.html`; 

        // Construct the full HTML for the downloadable report.
        // Important: Charts in this downloaded HTML will be static as they depend on the
        // JavaScript execution environment of the original page.
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

                    /* Hide interactive elements in the downloaded report */
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

        // Create a Blob containing the HTML content.
        const blob = new Blob([fullHtml], { type: 'text/html' });
        // Create a URL for the Blob.
        const url = URL.createObjectURL(blob);

        // Create a temporary anchor element to trigger the download.
        const a = document.createElement('a');
        a.href = url;
        a.download = filename; // Set the download filename.
        document.body.appendChild(a); // Append to body (necessary for Firefox).
        a.click(); // Programmatically click the anchor to start download.
        document.body.removeChild(a); // Clean up the temporary anchor.
        URL.revokeObjectURL(url); // Release the object URL for garbage collection.
    });
});