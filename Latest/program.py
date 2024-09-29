import os
import re
import json
import datetime
import glob
import PySimpleGUI as sg

CONFIG_FILE = 'obsidian_vault_manager_config.json'

def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            'vault_base_path': '',
            'reports_path': '',
            'prompts_path': '',
            'outputs_path': ''
        }

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def extract_prompts_and_create_links(vault_base_path, outputs_path, prompts_path):
    os.makedirs(prompts_path, exist_ok=True)
    extracted_count = 0

    for filename in os.listdir(outputs_path):
        if filename.endswith('.md'):
            input_path = os.path.join(outputs_path, filename)
            output_path = os.path.join(prompts_path, filename)

            if os.path.exists(output_path) and os.path.getmtime(output_path) > os.path.getmtime(input_path):
                continue

            with open(input_path, 'r', encoding='utf-8') as infile:
                content = infile.read()

            content = re.sub(r'\n## Extracted Prompts\n(.*?)\n(?=##|\Z)', '', content, flags=re.DOTALL)
            prompts = re.findall(r'(?:^|\n)(#+\s*Prompt\s*\d*\s*\n[\s\S]*?)(?=\n#+|$)', content, re.MULTILINE)

            if prompts:
                with open(output_path, 'w', encoding='utf-8') as outfile:
                    for i, prompt in enumerate(prompts, 1):
                        outfile.write(f"## Prompt {i}\n\n")
                        outfile.write(prompt.strip() + '\n\n')
                        outfile.write(f"[[{os.path.relpath(input_path, vault_base_path)}|Original File]]\n\n")

                content += "\n\n## Extracted Prompts\n"
                for i in range(1, len(prompts) + 1):
                    content += f"[[{os.path.relpath(output_path, vault_base_path)}#Prompt {i}|Prompt {i}]]\n"

                with open(input_path, 'w', encoding='utf-8') as infile:
                    infile.write(content)

                extracted_count += 1

    return extracted_count

def count_words_in_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    return len(content.split())

def count_markdown_files(directory):
    return len([file for file in glob.iglob(f'{directory}/**/*.md', recursive=True)])

def gather_markdown_files(directory):
    return [file for file in glob.iglob(f'{directory}/**/*.md', recursive=True)]

def generate_vault_report(vault_base_path, reports_path):
    agents_folder = os.path.join(vault_base_path, 'Agents')
    outputs_folder = os.path.join(vault_base_path, 'Outputs')
    prompts_folder = os.path.join(vault_base_path, 'Prompts')

    os.makedirs(reports_path, exist_ok=True)
    metrics_file = os.path.join(reports_path, 'metrics_history.json')
    
    current_time = datetime.datetime.now()
    report_name = f"{current_time.strftime('%Y%m%d_%H%M')}_report.md"
    report_path = os.path.join(reports_path, report_name)

    num_agents_docs = count_markdown_files(agents_folder)
    outputs_files = gather_markdown_files(outputs_folder)
    num_outputs_docs = len(outputs_files)
    total_words_in_outputs = sum(count_words_in_file(file) for file in outputs_files)
    num_prompts_docs = count_markdown_files(prompts_folder)
    total_entities = num_agents_docs + num_outputs_docs + num_prompts_docs

    if os.path.exists(metrics_file):
        with open(metrics_file, 'r') as f:
            metrics_history = json.load(f)
    else:
        metrics_history = []

    current_metrics = {
        "date": current_time.strftime('%Y-%m-%d'),
        "num_agents_docs": num_agents_docs,
        "num_outputs_docs": num_outputs_docs,
        "total_words_in_outputs": total_words_in_outputs,
        "num_prompts_docs": num_prompts_docs,
        "total_entities": total_entities
    }

    metrics_history.append(current_metrics)

    with open(metrics_file, 'w') as f:
        json.dump(metrics_history, f, indent=4)

    if len(metrics_history) > 1:
        previous_metrics = metrics_history[-2]
        new_agents_docs = num_agents_docs - previous_metrics["num_agents_docs"]
        new_outputs_docs = num_outputs_docs - previous_metrics["num_outputs_docs"]
        new_words_in_outputs = total_words_in_outputs - previous_metrics["total_words_in_outputs"]
        new_prompts_docs = num_prompts_docs - previous_metrics["num_prompts_docs"]
        new_entities = total_entities - previous_metrics["total_entities"]
    else:
        new_agents_docs = new_outputs_docs = new_words_in_outputs = new_prompts_docs = new_entities = "N/A"

    report_content = f"""
# Vault Inventory Report

**Date:** {current_time.strftime('%Y-%m-%d %H:%M')}

## Agents Folder
- Number of documents: {num_agents_docs} (New: {new_agents_docs})

## Outputs Folder
- Number of documents: {num_outputs_docs} (New: {new_outputs_docs})
- Total word count: {total_words_in_outputs} (New: {new_words_in_outputs})

## Prompts Folder
- Number of documents: {num_prompts_docs} (New: {new_prompts_docs})

## Total Entities in System
- Total: {total_entities} (New: {new_entities})

## Historical Data
| Date | Agents | Outputs | Words | Prompts | Total Entities |
|------|--------|---------|-------|---------|----------------|
"""

    for metrics in reversed(metrics_history[-7:]):  # Show last 7 days
        report_content += f"| {metrics['date']} | {metrics['num_agents_docs']} | {metrics['num_outputs_docs']} | {metrics['total_words_in_outputs']} | {metrics['num_prompts_docs']} | {metrics['total_entities']} |\n"

    with open(report_path, 'w') as report_file:
        report_file.write(report_content)

    return report_path

def fix_filenames(base_folder_path):
    def sanitize_filename(filename):
        invalid_chars = r'[<>:"/\\|?*\x00-\x1F]'
        return re.sub(invalid_chars, '_', filename)

    renamed_files = []
    for dirpath, dirnames, filenames in os.walk(base_folder_path):
        for filename in filenames:
            new_filename = sanitize_filename(filename)
            if new_filename != filename:
                old_file_path = os.path.join(dirpath, filename)
                new_file_path = os.path.join(dirpath, new_filename)
                os.rename(old_file_path, new_file_path)
                renamed_files.append((old_file_path, new_file_path))

    return renamed_files

def create_gui():
    config = load_config()
    sg.theme('LightGrey1')

    layout = [
        [sg.Text('Vault Base Path:', size=(15, 1)), sg.Input(key='-VAULT-PATH-', default_text=config['vault_base_path'], size=(50, 1)), sg.FolderBrowse()],
        [sg.Text('Reports Path:', size=(15, 1)), sg.Input(key='-REPORTS-PATH-', default_text=config['reports_path'], size=(50, 1)), sg.FolderBrowse()],
        [sg.Text('Prompts Path:', size=(15, 1)), sg.Input(key='-PROMPTS-PATH-', default_text=config['prompts_path'], size=(50, 1)), sg.FolderBrowse()],
        [sg.Text('Outputs Path:', size=(15, 1)), sg.Input(key='-OUTPUTS-PATH-', default_text=config['outputs_path'], size=(50, 1)), sg.FolderBrowse()],
        [sg.Button('Extract Prompts', size=(15, 1)), sg.Button('Generate Report', size=(15, 1)), sg.Button('Fix Filenames', size=(15, 1))],
        [sg.Button('Save Settings', size=(15, 1)), sg.Button('Exit', size=(15, 1))]
    ]

    window = sg.Window('Obsidian Vault Manager', layout, finalize=True)

    while True:
        event, values = window.read()
        if event == sg.WINDOW_CLOSED or event == 'Exit':
            break
        elif event == 'Extract Prompts':
            extracted_count = extract_prompts_and_create_links(
                values['-VAULT-PATH-'],
                values['-OUTPUTS-PATH-'],
                values['-PROMPTS-PATH-']
            )
            sg.popup(f'Extracted prompts and created links for {extracted_count} files.')
        elif event == 'Generate Report':
            report_path = generate_vault_report(values['-VAULT-PATH-'], values['-REPORTS-PATH-'])
            sg.popup(f'Report generated: {report_path}')
        elif event == 'Fix Filenames':
            renamed_files = fix_filenames(values['-VAULT-PATH-'])
            sg.popup(f'Fixed {len(renamed_files)} filenames.')
        elif event == 'Save Settings':
            new_config = {
                'vault_base_path': values['-VAULT-PATH-'],
                'reports_path': values['-REPORTS-PATH-'],
                'prompts_path': values['-PROMPTS-PATH-'],
                'outputs_path': values['-OUTPUTS-PATH-']
            }
            save_config(new_config)
            sg.popup('Settings saved successfully.')

    window.close()

if __name__ == "__main__":
    create_gui()