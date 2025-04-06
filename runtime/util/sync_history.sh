#!/bin/bash

# Navigate to the repository root
echo "Switching to main branch and updating..."
git checkout main
git pull origin main

# Pull only the historical_bugout_index.csv file from deployment
echo "Fetching latest historical data from deployment..."
git checkout deployment -- data/historical_bugout_index.csv

# Stage the file explicitly
git add data/historical_bugout_index.csv

# Commit and push changes
echo "Committing and pushing changes to main..."
git commit -m "Merged latest historical data from deployment"
git push origin main

echo "History file successfully updated in main branch!"
