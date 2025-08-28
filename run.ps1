param(
[string]$ProjectPath = "C:\Users\USER\PycharmProjects\Shir-Analysis",
[string]$EnvName = "shir-analysis"
)

Push-Location $ProjectPath

# If conda is initialized in PowerShell:
conda activate shir-analysis
streamlit run app.py --server.port 8501

Pop-Location
Read-Host "Press Enter to exit"