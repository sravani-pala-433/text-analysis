import pandas as pd
from io import BytesIO


async def process_excel_file(file):
	"""
	Reads and processes the uploaded Excel file.
	"""
	# Read file content asynchronously
	content = await file.read()
	# Load the content into a pandas DataFrame
	try:
		excel_data = pd.read_excel(BytesIO(content))
	except Exception as e:
		raise ValueError(f"Failed to read Excel file: {str(e)}")
	
	# Example: Convert DataFrame to a list of dictionaries
	records = excel_data.to_dict(orient="records")
	# Example: Perform custom processing (e.g., sum a column)
	summary = {
		"total_rows": len(records),
		"columns": list(excel_data.columns),
	}
	
	return {"summary": summary, "records": records[:10]}  # Returning a sample of the records
