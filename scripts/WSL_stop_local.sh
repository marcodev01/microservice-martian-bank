#!/bin/bash

# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

#######################################################################################

### ONLY FOR WSL ###

# Function to close all Windows Terminal windows
close_windows_terminal() {
    echo "Attempting to close all Windows Terminal windows..."

    # Use taskkill.exe to terminate the WindowsTerminal.exe process
    taskkill.exe /IM WindowsTerminal.exe /F 2>/dev/null

    if [ $? -eq 0 ]; then
        echo "All Windows Terminal windows were successfully closed."
    else
        echo "Windows Terminal is not running or could not be closed."
    fi
}

# Main function
main() {
    # Check if the script is not being executed from within a Windows Terminal session,
    # to avoid closing the current terminal window.
    CURRENT_PROCESS_NAME=$(ps -p $$ -o comm=)
    if [[ "$CURRENT_PROCESS_NAME" == "bash" ]]; then
        close_windows_terminal
    else
        echo "This script should be executed in a WSL Bash session."
        exit 1
    fi
}

main
