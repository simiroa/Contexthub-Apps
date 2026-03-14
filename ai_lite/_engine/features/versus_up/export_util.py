from pathlib import Path
import datetime

class ExportUtil:
    @staticmethod
    def to_markdown(project, products, criteria, values):
        """
        project: (id, name, category, description, created_at)
        products: list of (id, project_id, name, image_path, url, notes)
        criteria: list of (id, project_id, name, data_type, weight)
        values: list of (product_id, criterion_id, value)
        """
        lines = []
        lines.append(f"# Comparison Report: {project[1]}")
        lines.append(f"**Category:** {project[2]}")
        lines.append(f"**Date:** {project[4]}")
        lines.append(f"\n{project[3]}\n")
        
        # Table Header
        header = "| Criterion | " + " | ".join([p[2] for p in products]) + " |"
        separator = "| --- | " + " | ".join(["---" for _ in products]) + " |"
        lines.append(header)
        lines.append(separator)
        
        # Mapping values for easy lookup
        val_map = {(v[0], v[1]): v[2] for v in values}
        
        # Table Rows
        for crit in criteria:
            row = f"| {crit[2]} (w:{crit[4]}) | "
            row_vals = []
            for prod in products:
                val = val_map.get((prod[0], crit[0]), "-")
                row_vals.append(str(val))
            row += " | ".join(row_vals) + " |"
            lines.append(row)
            
        lines.append("\n## Notes")
        for prod in products:
            if prod[5]: # notes
                lines.append(f"- **{prod[2]}:** {prod[5]}")
                
        return "\n".join(lines)

    @staticmethod
    def save_to_file(content, filename):
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        return filename
