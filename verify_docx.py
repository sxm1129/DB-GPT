
import os
import sys

# Attempt to import docx
try:
    from docx import Document
except ImportError:
    print("python-docx not installed")

def extract_text_from_docx(file_path):
    print(f"Attempting to extract text from: {file_path}")
    if not os.path.exists(file_path):
        print("File not found")
        return

    try:
        doc = Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        
        text = '\n'.join(full_text)
        print(f"Extracted {len(text)} characters.")
        if len(text) < 100:
            print("WARNING: Very little text found.")
            print("Preview:", text)
        else:
            print("Preview:", text[:200])
            
    except Exception as e:
        print(f"Error reading docx: {e}")

if __name__ == "__main__":
    target_file = "/Users/hs/workspace/github/DB-GPT/pilot/data/_knowledge_cache_/f955fe53-4b1c-46d0-b4af-a3ff5503238c.docx"
    extract_text_from_docx(target_file)
