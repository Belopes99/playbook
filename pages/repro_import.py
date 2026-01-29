import sys
import os

# Simulate Streamlit adding root to path
# Real path: .../Streamlit/pages/repro_import.py
# Root: .../Streamlit/
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)

print(f"Added root to path: {root_dir}")

try:
    from src.queries import get_conversion_ranking_query
    print("SUCCESS: Imported get_conversion_ranking_query")
except ImportError as e:
    print(f"FAILURE: ImportError: {e}")
except Exception as e:
    print(f"FAILURE: Other Error: {e}")
