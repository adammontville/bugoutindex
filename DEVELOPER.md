# Setting Up BugOutIndex in PyCharm

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd bugoutindex
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Open the project in PyCharm and configure:
   - Set up the Python interpreter to use the virtual environment.
   - Add a run configuration for Streamlit:
     - Script: `streamlit`
     - Parameters: `run presentation/dashboard.py`

5. Run the dashboard using the PyCharm "Run" button.
