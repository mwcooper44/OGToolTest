#!/usr/bin/env python3
"""
Script to clean the quill.co_blog.json file by removing entries with "Page Not Found" titles
and any entries that might have scraping errors.
"""

import json
import sys

def clean_json_file(input_file, output_file):
    """
    Clean the JSON file by removing entries with "Page Not Found" titles
    and any entries that might indicate scraping errors.
    """
    try:
        # Read the JSON file
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"Original number of items: {len(data['items'])}")
        
        # Filter out entries with "Page Not Found" titles
        cleaned_items = []
        removed_count = 0
        
        for item in data['items']:
            title = item.get('title', '').strip()
            
            # Skip entries with "Page Not Found" titles
            if title == "Page Not Found":
                removed_count += 1
                print(f"Removing: {item.get('source_url', 'Unknown URL')}")
                continue
            
            # Skip entries with empty or very short content (potential scraping errors)
            content = item.get('content', '').strip()
            if len(content) < 50:  # Very short content might indicate scraping errors
                removed_count += 1
                print(f"Removing short content entry: {item.get('source_url', 'Unknown URL')}")
                continue
            
            # Skip entries with error-like content
            if any(error_word in content.lower() for error_word in ['error', 'failed', 'timeout', 'connection refused']):
                removed_count += 1
                print(f"Removing error entry: {item.get('source_url', 'Unknown URL')}")
                continue
            
            cleaned_items.append(item)
        
        # Update the data with cleaned items
        data['items'] = cleaned_items
        
        print(f"Removed {removed_count} entries")
        print(f"Final number of items: {len(data['items'])}")
        
        # Write the cleaned data back to the file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"Cleaned JSON saved to: {output_file}")
        
    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in file '{input_file}': {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    input_file = "quill.co_blog.json"
    output_file = "quill.co_blog.json"  # Overwrite the original file
    
    clean_json_file(input_file, output_file)
