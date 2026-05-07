"""Create the reports/ directory with sample files."""
import os

base = "reports"
os.makedirs(base, exist_ok=True)
open(os.path.join(base, "report_193.txt"), "w").write("sample content for report_193.txt")
open(os.path.join(base, "data_186.csv"), "w").write("sample content for data_186.csv")
open(os.path.join(base, "export_469.json"), "w").write("sample content for export_469.json")
print(f"Created {len(os.listdir(base))} files in {base}/")
