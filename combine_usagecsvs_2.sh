{
  `path`: `/Users/Pete/Downloads/combine_csvs_interactive.sh`,
  `content`: `#!/bin/bash

# Script to combine multiple CircleCI usage CSV files interactively
echo \"==================================================\"
echo \"CircleCI Usage CSV Combiner - Interactive Mode\"
echo \"==================================================\"
echo \"\"

# Define the output file
read -p \"Enter the output file path (default: /Users/Pete/Downloads/combined-usage-data.csv): \" OUTPUT_FILE
if [ -z \"$OUTPUT_FILE\" ]; then
    OUTPUT_FILE=\"/Users/Pete/Downloads/combined-usage-data.csv\"
fi

echo \"Output will be saved to: $OUTPUT_FILE\"
echo \"\"

# Array to store input files
declare -a INPUT_FILES
FILE_COUNT=0

# Function to check if file exists
check_file() {
    if [ ! -f \"$1\" ]; then
        echo \"⚠️  Warning: File not found: $1\"
        return 1
    else
        echo \"✓ File found: $1\"
        return 0
    fi
}

# Interactive loop to collect file paths
echo \"Enter CSV file paths one at a time.\"
echo \"Type 'done' when finished, 'list' to see files added so far, or 'clear' to start over.\"
echo \"==================================================\"

while true; do
    FILE_COUNT=$((FILE_COUNT + 1))
    echo \"\"
    read -p \"Enter path for CSV file #$FILE_COUNT (or 'done'/'list'/'clear'): \" USER_INPUT
    
    # Check for special commands
    if [ \"$USER_INPUT\" = \"done\" ] || [ \"$USER_INPUT\" = \"DONE\" ]; then
        FILE_COUNT=$((FILE_COUNT - 1))
        break
    elif [ \"$USER_INPUT\" = \"list\" ] || [ \"$USER_INPUT\" = \"LIST\" ]; then
        FILE_COUNT=$((FILE_COUNT - 1))
        if [ ${#INPUT_FILES[@]} -eq 0 ]; then
            echo \"No files added yet.\"
        else
            echo \"\"
            echo \"Files added so far:\"
            for i in \"${!INPUT_FILES[@]}\"; do
                echo \"  $((i + 1)). ${INPUT_FILES[$i]}\"
            done
        fi
        continue
    elif [ \"$USER_INPUT\" = \"clear\" ] || [ \"$USER_INPUT\" = \"CLEAR\" ]; then
        INPUT_FILES=()
        FILE_COUNT=0
        echo \"File list cleared. Starting over...\"
        continue
    elif [ -z \"$USER_INPUT\" ]; then
        FILE_COUNT=$((FILE_COUNT - 1))
        echo \"No file entered. Please enter a file path or 'done' to finish.\"
        continue
    else
        # Check if file exists
        if check_file \"$USER_INPUT\"; then
            INPUT_FILES+=(\"$USER_INPUT\")
            echo \"Added: $USER_INPUT\"
        else
            FILE_COUNT=$((FILE_COUNT - 1))
            read -p \"File not found. Add anyway? (y/n): \" ADD_ANYWAY
            if [ \"$ADD_ANYWAY\" = \"y\" ] || [ \"$ADD_ANYWAY\" = \"Y\" ]; then
                INPUT_FILES+=(\"$USER_INPUT\")
                echo \"Added: $USER_INPUT (file not found - will error if not present at runtime)\"
            fi
        fi
    fi
done

# Check if we have any files to combine
if [ ${#INPUT_FILES[@]} -eq 0 ]; then
    echo \"\"
    echo \"❌ No files to combine. Exiting.\"
    exit 1
fi

# Display summary
echo \"\"
echo \"==================================================\"
echo \"Ready to combine ${#INPUT_FILES[@]} CSV files:\"
for i in \"${!INPUT_FILES[@]}\"; do
    echo \"  $((i + 1)). ${INPUT_FILES[$i]}\"
done
echo \"\"
echo \"Output file: $OUTPUT_FILE\"
echo \"==================================================\"

# Confirm before proceeding
read -p \"Proceed with combining? (y/n): \" CONFIRM
if [ \"$CONFIRM\" != \"y\" ] && [ \"$CONFIRM\" != \"Y\" ]; then
    echo \"Operation cancelled.\"
    exit 0
fi

# Check if output file already exists
if [ -f \"$OUTPUT_FILE\" ]; then
    read -p \"⚠️  Output file already exists. Overwrite? (y/n): \" OVERWRITE
    if [ \"$OVERWRITE\" != \"y\" ] && [ \"$OVERWRITE\" != \"Y\" ]; then
        # Suggest alternative filename
        TIMESTAMP=$(date +\"%Y%m%d_%H%M%S\")
        OUTPUT_FILE=\"${OUTPUT_FILE%.csv}_${TIMESTAMP}.csv\"
        echo \"Using alternative filename: $OUTPUT_FILE\"
    fi
fi

# Start combining files
echo \"\"
echo \"Starting combination process...\"
echo \"==================================================\"

# Get header from first file
FIRST_FILE=\"${INPUT_FILES[0]}\"
if [ ! -f \"$FIRST_FILE\" ]; then
    echo \"❌ Error: First file not found: $FIRST_FILE\"
    exit 1
fi

echo \"Extracting header from first file...\"
head -n 1 \"$FIRST_FILE\" > \"$OUTPUT_FILE\"

# Process each file
TOTAL_ROWS=0
for i in \"${!INPUT_FILES[@]}\"; do
    FILE=\"${INPUT_FILES[$i]}\"
    echo \"\"
    echo \"Processing file $((i + 1)) of ${#INPUT_FILES[@]}: $(basename \"$FILE\")\"
    
    if [ ! -f \"$FILE\" ]; then
        echo \"  ⚠️  Skipping - file not found: $FILE\"
        continue
    fi
    
    # Count rows in this file (excluding header)
    ROW_COUNT=$(tail -n +2 \"$FILE\" | wc -l | tr -d ' ')
    echo \"  Adding $ROW_COUNT data rows...\"
    
    # Append data rows (skip header)
    tail -n +2 \"$FILE\" >> \"$OUTPUT_FILE\"
    
    TOTAL_ROWS=$((TOTAL_ROWS + ROW_COUNT))
    echo \"  ✓ Complete\"
done

# Final summary
echo \"\"
echo \"==================================================\"
echo \"✅ Combination Complete!\"
echo \"==================================================\"
echo \"📍 Output file: $OUTPUT_FILE\"
echo \"📊 Total data rows: $TOTAL_ROWS\"
echo \"📁 Files combined: ${#INPUT_FILES[@]}\"

# Calculate file size
if [ -f \"$OUTPUT_FILE\" ]; then
    FILE_SIZE=$(ls -lh \"$OUTPUT_FILE\" | awk '{print $5}')
    echo \"💾 File size: $FILE_SIZE\"
fi

echo \"\"
echo \"You can now analyze this file with:\"
echo \"  export CIRCLECI_USAGE_CSV=\\\"$OUTPUT_FILE\\\"\"
echo \"  python3 analyze_runner_costs.py\"
`
}