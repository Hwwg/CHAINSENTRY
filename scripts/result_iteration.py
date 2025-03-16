import pandas as pd
import json

# Load the data from the JSON file
with open('/Users/tlif3./Desktop/all/zju_research/llm_alert/AlertGPT_python/cache/gpt-4o/alert_results_cot_combined_unique_data_fp.json', 'r') as f:
    data = json.load(f)

# Convert the data to a dictionary for easier manipulation
filtered_data = {key: value for key, value in data.items() if value.get("Final Result") == "Yes" or value.get("Final Result") == "Unsure"}

# Save the filtered results to a JSON file
output_file = '/cache/gpt-4o/alert_results_cot_combined_unique_data_fp.json'  # Specify the output file path
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(filtered_data, f, ensure_ascii=False, indent=4)

print(f"Filtered results saved to {output_file}")