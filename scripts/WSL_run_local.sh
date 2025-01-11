#!/bin/bash

# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

### ONLY FOR WSL ###

#######################################################################################
## Setup

# Change to the parent directory
cd ..

# Check for dependencies
if ! command -v node &>/dev/null; then
    echo -e "\nNode.js is not installed. Please install Node.js and npm."
    exit 1
fi

if ! command -v python3 &>/dev/null; then
    echo -e "\nPython 3 is not installed. Please install Python 3."
    exit 1
fi

#######################################################################################
## Functions for running microservices

# Function to run JavaScript microservices
run_javascript_microservice() {
    local service_name="$1"
    local service_alias="$2"
    local current_dir="$(pwd)"
    
    echo "Starting $service_name microservice..."
    
    # Open a new Windows Terminal tab and execute commands
    if command -v wt.exe &>/dev/null; then
        wt.exe new-tab --title "$service_name" wsl bash -i -c "cd '$current_dir/$service_name' && npm install && npm run $service_alias"
    else
        echo "wt.exe not found. Please ensure Windows Terminal is installed."
        exit 1
    fi
    sleep 2
    
    echo "$service_name is running..."
    echo
}

# Function to run Python microservices
run_python_microservice() {
    local service_name="$1"
    local service_alias="$2"
    local current_dir="$(pwd)"
    
    echo "Starting $service_name microservice..."
    
    # Open a new Windows Terminal tab and execute commands
    if command -v wt.exe &>/dev/null; then
        wt.exe new-tab --title "$service_name" wsl bash -i -c "cd '$current_dir/$service_name' && \
        rm -rf venv_bankapp && python3 -m venv venv_bankapp && \
        source venv_bankapp/bin/activate && \
        pip3 install -r requirements.txt && python3 '$service_alias.py'"
    else
        echo "wt.exe not found. Please ensure Windows Terminal is installed."
        exit 1
    fi
    sleep 2
    
    echo "$service_name is running..."
    echo
}

#######################################################################################
## Running JavaScript microservices

run_javascript_microservice "ui" "ui"
run_javascript_microservice "customer-auth" "auth"
run_javascript_microservice "atm-locator" "atm"

#######################################################################################
## Running Python microservices

# Disable automatic activation of the conda base environment, if conda is used
if command -v conda &>/dev/null; then
    conda config --set auto_activate_base false &>/dev/null
fi

# Update and upgrade Python3 using apt
sudo apt-get update &>/dev/null
sudo apt-get install --only-upgrade python3 -y &>/dev/null

run_python_microservice "dashboard" "dashboard"
run_python_microservice "accounts" "accounts"
run_python_microservice "transactions" "transaction"
run_python_microservice "loan" "loan"

echo "Setup completed successfully!"
