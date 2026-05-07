"""Create the files/ directory with sample files."""
import os

base = "files"
os.makedirs(base, exist_ok=True)
open(os.path.join(base, "report_876.txt"), "w").write("sample content for report_876.txt")
open(os.path.join(base, "data_530.csv"), "w").write("sample content for data_530.csv")
open(os.path.join(base, "export_141.json"), "w").write("sample content for export_141.json")
print(f"Created {len(os.listdir(base))} files in {base}/")
