
import os

input_path = "event_schema_diagram.md"
output_path = "event_schema.html"

def convert():
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found.")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Extract mermaid code (remove ```mermaid and ```)
    # Assuming simple format from my previous script
    start = content.find("```mermaid")
    end = content.find("```", start + 10)
    
    if start == -1 or end == -1:
        print("Mermaid block not found")
        return
        
    mermaid_code = content[start+10:end].strip()
    
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BetterData Event Schema</title>
    <style>
        body {{ font-family: sans-serif; padding: 20px; background: #f0f2f6; }}
        h1 {{ text-align: center; color: #333; }}
        .diagram-container {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow: auto;
        }}
    </style>
    <script type="module">
      import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
      mermaid.initialize({{ 
        startOnLoad: true, 
        theme: 'neutral',
        mindmap: {{ padding: 20 }}
      }});
    </script>
</head>
<body>
    <h1>Schema de Eventos, Resultados e Qualifiers</h1>
    <div class="diagram-container">
        <div class="mermaid">
{mermaid_code}
        </div>
    </div>
</body>
</html>
    """
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
        
    print(f"Generated {output_path}")

if __name__ == "__main__":
    convert()
