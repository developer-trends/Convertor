import os
import io
import json
import requests
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# Configuration
SPREADSHEET_NAME = "Trends"
SHEET_NAME = "Sheet 15"
WEBP_COL_INDEX = 4      # Column E (0-based index)
OUTPUT_COL_INDEX = 7    # Column H (0-based index)
DRIVE_FOLDER_ID = "1ORg8PHtVVVXION8Io7No62pssxkgF5C6"

# Authenticate with Google APIs
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets"
]
creds_dict = json.loads(os.environ["GOOGLE_SA_JSON"])
credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)

gc = gspread.authorize(credentials)
worksheet = gc.open(SPREADSHEET_NAME).worksheet(SHEET_NAME)

drive_service = build("drive", "v3", credentials=credentials)

def convert_and_upload_webp_images():
    all_rows = worksheet.get_all_values()
    
    for row_index, row in enumerate(all_rows[1:], start=2):  # Skip header
        if len(row) <= WEBP_COL_INDEX:
            continue

        webp_url = row[WEBP_COL_INDEX].strip()
        if not webp_url.lower().endswith(".webp"):
            continue

        try:
            response = requests.get(webp_url, timeout=10)
            response.raise_for_status()

            image = Image.open(io.BytesIO(response.content)).convert("RGBA")
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            buffer.seek(0)

            file_metadata = {
                "name": f"trend_image_row{row_index}.png",
                "parents": [DRIVE_FOLDER_ID],
                "mimeType": "image/png"
            }
            media = MediaIoBaseUpload(buffer, mimetype="image/png")
            uploaded = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id,webViewLink"
            ).execute()

            drive_url = uploaded["webViewLink"]
            worksheet.update_cell(row_index, OUTPUT_COL_INDEX + 1, drive_url)

        except Exception as error:
            error_message = f"Error: {str(error)}"
            worksheet.update_cell(row_index, OUTPUT_COL_INDEX + 1, error_message)

if __name__ == "__main__":
    convert_and_upload_webp_images()
