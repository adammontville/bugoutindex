# Setting up BugOut Index

1. Clone the repository and create a virtual environment.

2. Install the hashed lock from the repo root:

   ```bash
   python -m pip install --require-hashes -r runtime/requirements.txt
   ```

3. Publish locally the same way the weekly job does. `FRED_API_KEY` comes from the environment.

   ```bash
   export FRED_API_KEY=<your key>
   export PYTHONPATH=$PWD
   python -m runtime.publish.weekly_run
   python -m http.server 8765 --directory docs
   ```

4. Optional viewer: from `runtime/`, run `streamlit run main.py`. It reads `docs/data/latest.json` and does not write the site. The weekly job does not import Streamlit.

The snapshot contract is `docs/architecture/snapshot-schema.md`.
