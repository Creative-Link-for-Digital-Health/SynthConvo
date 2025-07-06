import os
import pandas as pd

directory = os.getcwd()
dataframes = []

# Iterate through files in the directory
for filename in os.listdir(directory):
    if filename.endswith(".txt"):
        file_path = os.path.join(directory, filename)
        
        with open(file_path, 'r') as file:
            content = file.read()
        
        df = pd.DataFrame({'filename': [filename], 'content': [content]})
        
        dataframes.append(df)

result_df = pd.concat(dataframes, ignore_index=True)

# Output as CSV
output_file = "vignette_list.csv"
result_df.to_csv(output_file, index=False)

print(f"Vignette list updated. Output saved to {output_file}")