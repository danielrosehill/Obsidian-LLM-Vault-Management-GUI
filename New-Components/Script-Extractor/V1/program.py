import os
import re
import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

# Configuration file for storing paths
config_file = 'config.json'

# Default paths if no config is found
default_outputs_dir = '../Outputs'
default_generated_dir = '../Scripts/Generated'
log_file = 'parsed_files.log'  # This will now be relative to the generated directory

# Regular expression to detect code blocks (ensures it handles multi-line properly)
code_block_pattern = r'```(.*?)```'

# Minimum number of lines for a valid script
min_lines = 10

# Define language detection patterns
language_patterns = {
    'bash': r'#!/bin/bash|^echo|^cd|^ls|^sudo|^export',
    'python': r'^import|^def|^class|^print\(|^if __name__ == "__main__":',
    'javascript': r'^function|^const|^let|^var|^console\.log\(|^document\.getElementById\('
}

# Load the Outputs and Generated directories from config, or set to defaults
def load_config():
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
        return config.get('outputs_dir', default_outputs_dir), config.get('generated_dir', default_generated_dir)
    return default_outputs_dir, default_generated_dir

# Save the Outputs and Generated directories to config
def save_config(outputs_dir, generated_dir):
    with open(config_file, 'w') as f:
        json.dump({'outputs_dir': outputs_dir, 'generated_dir': generated_dir}, f)

# Helper function to detect the language of a code snippet
def detect_language(snippet):
    for language, pattern in language_patterns.items():
        if re.search(pattern, snippet, re.MULTILINE):
            return language
    return None

# Helper function to check if a script file has been parsed before
def script_already_parsed(script_path, log_file_path):
    if not os.path.exists(log_file_path):
        return False
    with open(log_file_path, 'r') as f:
        parsed_files = f.read().splitlines()
    return script_path in parsed_files

# Helper function to log parsed script files
def log_parsed_script(script_path, log_file_path):
    with open(log_file_path, 'a') as f:
        f.write(script_path + '\n')

# Function to handle the script extraction process
def extract_scripts(outputs_dir, generated_dir):
    # Ensure log file path is relative to generated_dir
    log_file_path = os.path.join(generated_dir, log_file)
    
    # Ensure subdirectories for scripts exist in generated directory
    paths_by_language = {
        'python': os.path.join(generated_dir, 'Python'),
        'bash': os.path.join(generated_dir, 'Bash'),
        'javascript': os.path.join(generated_dir, 'JS')
    }
    
    for path in paths_by_language.values():
        Path(path).mkdir(parents=True, exist_ok=True)

    # Traverse the outputs directory and process files
    for root, dirs, files in os.walk(outputs_dir):
        for file in files:
            file_path = os.path.join(root, file)
            print(f"Processing file: {file_path}")

            if file.endswith(".txt") or file.endswith(".md"):  # Assuming the outputs are in .txt or .md files
                with open(file_path, 'r') as f:
                    content = f.read()

                    # Find all code blocks within the content
                    code_blocks = re.findall(code_block_pattern, content, re.DOTALL)

                    print(f"Found {len(code_blocks)} code blocks in {file_path}")

                    # Process each code block
                    script_count = 0
                    for i, code_block in enumerate(code_blocks):
                        # Count the lines in the block
                        num_lines = code_block.strip().count('\n') + 1
                        print(f"Code block {i+1} has {num_lines} lines")

                        if num_lines < min_lines:
                            print(f"Skipping short code block in {file_path}")
                            continue  # Skip blocks that are too short

                        # Detect the language of the code block
                        language = detect_language(code_block)
                        if language:
                            script_count += 1
                            # Generate a filename with proper numeration
                            script_file_name = f'{Path(file).stem}_script_{script_count}.{language[:2]}'
                            script_file_path = os.path.join(paths_by_language[language], script_file_name)

                            # Skip script if it was already parsed
                            if script_already_parsed(script_file_path, log_file_path):
                                print(f"Skipping already parsed script: {script_file_path}")
                                continue

                            # Write the detected script to the appropriate file
                            with open(script_file_path, 'w') as script_file:
                                script_file.write(code_block.strip())

                            print(f"Script extracted and saved to: {script_file_path}")

                            # Log the script file as parsed
                            log_parsed_script(script_file_path, log_file_path)

    messagebox.showinfo("Extraction Complete", f"Scripts extracted. Check {generated_dir} for the results.")

# GUI for selecting directories
def set_outputs_directory():
    outputs_dir = filedialog.askdirectory(title="Select Outputs Directory")
    if outputs_dir:
        outputs_label.config(text=f"Current Outputs Directory: {outputs_dir}")
        return outputs_dir
    return None

def set_generated_directory():
    generated_dir = filedialog.askdirectory(title="Select Generated Directory")
    if generated_dir:
        generated_label.config(text=f"Current Generated Directory: {generated_dir}")
        return generated_dir
    return None

# Main function to run the GUI and the extraction
def main():
    # Load the saved paths for outputs and generated directories
    outputs_dir, generated_dir = load_config()

    # Create the main window
    root = tk.Tk()
    root.title("Script Extraction Tool")
    root.geometry("450x250")

    # Display the current outputs directory
    global outputs_label
    outputs_label = tk.Label(root, text=f"Current Outputs Directory: {outputs_dir}", wraplength=400, justify="center")
    outputs_label.pack(pady=10)

    # Button to update the Outputs directory
    update_outputs_button = tk.Button(root, text="Update Outputs Directory", command=lambda: set_outputs_directory())
    update_outputs_button.pack(pady=5)

    # Display the current generated directory
    global generated_label
    generated_label = tk.Label(root, text=f"Current Generated Directory: {generated_dir}", wraplength=400, justify="center")
    generated_label.pack(pady=10)

    # Button to update the Generated directory
    update_generated_button = tk.Button(root, text="Update Generated Directory", command=lambda: set_generated_directory())
    update_generated_button.pack(pady=5)

    # Button to start script extraction
    extract_button = tk.Button(root, text="Start Script Extraction", command=lambda: extract_scripts(outputs_dir, generated_dir))
    extract_button.pack(pady=10)

    # Exit button
    exit_button = tk.Button(root, text="Exit", command=root.quit)
    exit_button.pack(pady=10)

    # Start the GUI
    root.mainloop()

    # Save the updated paths when the application is closed
    save_config(outputs_dir, generated_dir)

if __name__ == "__main__":
    main()
