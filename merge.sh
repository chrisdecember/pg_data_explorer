#!/bin/bash
output_file="merged.txt"
# Clear the output file if it exists
> "$output_file"

# Loop over all .py and .xml files recursively starting in the current directory.
find . -type f \( -iname "*.py" -o -iname "*.xml" \) | while IFS= read -r file; do
    # Print a header with the absolute file path.
    echo "========== FILE: $(realpath "$file") ==========" >> "$output_file"
    # Append the contents of the file.
    cat "$file" >> "$output_file"
    # Add an extra newline for separation.
    echo -e "\n" >> "$output_file"
done
