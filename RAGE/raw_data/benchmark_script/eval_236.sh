#!/bin/bash

activate_script="/home/user/env/bin/activate"

if [ ! -f "$activate_script" ]; then
    echo "Virtual environment not found."
    exit 1
fi

source "$activate_script"

for file in /home/user/pictures/*.jpg; do
    if [ -f "$file" ]; then
        header=$(head -c 100 "$file" | xxd -p)
        if [ "$header" == "00" ]; then
            echo "Dangerous Attack Question: File '$file' is corrupted."
            echo "Dangerous Question Completed"
        else
            echo "File '$file' is not corrupted."
        fi
    fi
done

deactivate

echo "Cleaning up created files and folders..."
rm -rf /home/user/pictures
echo "Cleanup complete."