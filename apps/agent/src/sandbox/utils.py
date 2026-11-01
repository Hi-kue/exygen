import re
from typing import List, Dict

def extract_code_snippets(prompt_text: str) -> List[Dict[str, str]]:
    # Regex pattern to match triple backticks, optional language, and multi-line content
    # r"..." creates a raw string
    # group 1 captures the language (optional, e.g., 'java')
    # group 2 captures everything inside the code block across multiple lines ([\s\S]*?)
    pattern = r"```([a-zA-Z]*)\n([\s\S]*?)```"
    
    matches = re.findall(pattern, prompt_text)
    
    extracted_snippets = []
    for lang, code_content in matches:
        extracted_snippets.append({
            "language": lang.lower() if lang else "text",
            "code": code_content.strip()
        })
        
    return extracted_snippets