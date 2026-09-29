import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import PatternFill

def excel_bg_color(file_location):
    file_path = file_location
    workbook = load_workbook(filename=file_path)
    sheet = workbook.active

    # Read the Excel file into a DataFrame
    df = pd.read_excel(file_path, engine='openpyxl')

    # Define the fill colors
    group_fill_color = PatternFill(start_color='D9D2E9', end_color='D9D2E9', fill_type='solid')  # Purple Accent 4, Lighter 60%
    header_fill_color = PatternFill(start_color='B4A7D6', end_color='B4A7D6', fill_type='solid')  # Purple Accent 4, Lighter 40%

    # Apply header color
    for col in range(1, sheet.max_column + 1):
        sheet.cell(row=1, column=col).fill = header_fill_color

    # Initialize variables to keep track of the current group and whether to apply color
    current_service_name = None
    apply_color = True

    # Loop through the DataFrame and apply background color to grouped rows
    for index, row in df.iterrows():
        service_name = row['OLT Hostname']

        if service_name != current_service_name:
            current_service_name = service_name
            apply_color = not apply_color  # Toggle color application for each new group

        if apply_color:
            for col in range(1, sheet.max_column + 1):
                sheet.cell(row= index + 2, column=col).fill = group_fill_color  # +2 to account for header and 1-based index

    # Save the modified Excel file
    workbook.save(filename=file_location)

    print(f"Background color applied to grouped rows and saved to '{file_location}'.")


