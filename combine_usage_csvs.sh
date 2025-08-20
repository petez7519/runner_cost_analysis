 Script to combine CircleCI usage CSV files for July 2025
echo "Combining CircleCI usage CSV files..."

# Define the output file
OUTPUT_FILE="/Users/Pete/Downloads/combined-usage-data-july-2025.csv"

# Define input files
FILE1="7a8345603546.csv"
FILE2="7a834560354e.csv"
FILE3="-7a8345602aae.csv"
FILE4="7a8345603552.csv"

# Get the header from the first file
echo "Extracting header..."
head -n 1 "$FILE1" > "$OUTPUT_FILE"

# Append all data rows (skipping headers) from each file
echo "Adding data from Okta organization..."
tail -n +2 "$FILE1" >> "$OUTPUT_FILE"

echo "Adding data from Shared Org 1..."
tail -n +2 "$FILE2" >> "$OUTPUT_FILE"
