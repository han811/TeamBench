"""Create the static/ directory with sample files."""
import os

base = "static"
os.makedirs(base, exist_ok=True)
open(os.path.join(base, "report_682.txt"), "w").write("sample content for report_682.txt")
open(os.path.join(base, "data_967.csv"), "w").write("sample content for data_967.csv")
open(os.path.join(base, "export_921.json"), "w").write("sample content for export_921.json")
print(f"Created {len(os.listdir(base))} files in {base}/")
