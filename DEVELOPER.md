# Setting up BugOut Index

1. Clone the repository and create a virtual environment.

2. Install the hashed lock from the repo root:

   ```bash
   python -m pip install --require-hashes -r runtime/requirements.txt
   ```

3. Publish locally the same way the weekly job does, then preview the files GitHub Pages serves. `FRED_API_KEY` comes from the environment.

   ```bash
   export FRED_API_KEY=<your key>
   export PYTHONPATH=$PWD
   python -m runtime.publish.weekly_run
   python -m http.server 8765 --directory docs
   ```

The snapshot contract is `docs/architecture/snapshot-schema.md`.
