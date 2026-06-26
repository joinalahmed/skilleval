---
name: csv-analyzer
description: Analyze CSV files and extract key statistics. Use when user uploads CSV files.
license: MIT
version: 1.0.0
metadata:
  owner: joinalahmed@gmail.com
  category: data-analysis
---

# CSV Analyzer

When given a CSV file, analyze the data and provide:
- Row count
- Column names and types
- Missing value statistics
- Basic descriptive statistics (mean, median, std)

## Steps

1. Read the CSV file using pandas
2. Validate the structure (at least 1 row, 1 column)
3. Analyze each column:
   - Detect data type (numeric, string, date)
   - Calculate statistics for numeric columns
   - Count missing values
4. Generate a summary report in JSON format

## Output Format

Save results to `analysis.json`:

```json
{
  "row_count": 100,
  "columns": [
    {
      "name": "age",
      "type": "numeric",
      "mean": 35.2,
      "median": 34.0,
      "std": 12.5,
      "missing_count": 3
    }
  ]
}
```

## Error Handling

- If file is not CSV format, report error
- If file is empty, report error
- If missing values > 50%, warn user
