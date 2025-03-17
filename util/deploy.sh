#!/bin/bash

# Step 1: Pull the latest historical data from deployment into main
echo "Syncing historical data from deployment..."
bash util/sync_history.sh

# Step 2: Ensure main is up to date
echo "Updating main branch..."
git checkout main
git pull origin main

# Step 3: Merge main into deployment
echo "Merging main into deployment..."
git checkout deploy
git merge main --no-ff -m "Merging latest changes from main into deployment"

# Step 4: Push the updated deployment branch to GitHub
echo "Pushing deployment branch to GitHub..."
git push origin deploy

# Step 5: SSH into Raspberry Pi and pull the latest deployment (once SSH is configured)
#echo "Attempting to update deployment on Raspberry Pi..."
#ssh pi@your-pi-ip "cd ~/bugoutindex && git pull origin deployment && sudo systemctl restart bugoutindex"
#
#echo "Deployment completed successfully!"
