import requests

API_URL = "http://64.227.160.120:5001/render-step"  # Change if your API is hosted elsewhere
STEP_FILE = "cad_95MoBC6uuohp06RV2nar_0_1750947399121 (1).step"  # Replace with your STEP file path
OUTPUT_ZIP = "downloaded_renders.zip"

# Form data
form_data = {
    'face_coloring_mode': 'uniform',
    'show_edges': 'true',
    'show_vertices': 'true',
    'num_orbit_views': '12',
    'return_format': 'zip'
}

with open(STEP_FILE, 'rb') as f:
    files = {'file': (STEP_FILE, f, 'application/octet-stream')}
    print(f"Uploading {STEP_FILE} to {API_URL} ...")
    response = requests.post(API_URL, data=form_data, files=files, stream=True)

if response.status_code == 200:
    with open(OUTPUT_ZIP, 'wb') as out:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                out.write(chunk)
    print(f"✅ ZIP file downloaded successfully: {OUTPUT_ZIP}")
else:
    print(f"❌ Failed to download ZIP file. Status: {response.status_code}")
    print(response.text) 