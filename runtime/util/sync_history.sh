#!/bin/bash

# Switch to deployment branch and ensure it's up-to-date
echo "Updating local deployment branch from origin..."
git checkout deployment
git pull origin deployment

# Switch back to main and update it
echo "Switching to main branch and updating..."
git checkout main
git pull origin main

# Now pull only the historical_bugout_index.csv file from up-to-date local deployment branch
echo "Fetching latest historical data from deployment..."
git checkout deployment -- runtime/data/historical_bugout_index.csv

# Explicitly stage the updated file
git add runtime/data/historical_bugout_index.csv

# Commit and push changes
echo "Committing and pushing changes to main..."
git commit -m "Merged latest historical data from deployment"
git push origin main

echo "History file successfully updated in main branch!"