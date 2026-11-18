"""Run this ONCE on your own computer to let the pipeline upload to your YouTube channel.

1. In Google Cloud Console create a project, enable "YouTube Data API v3",
   create OAuth credentials of type "Desktop app", download the JSON as client_secret.json
   next to this file. Add your Google account as a test user on the OAuth consent screen.
2. pip install google-auth-oauthlib
3. python get_youtube_token.py
4. Copy the three printed values into GitHub → Settings → Secrets and variables → Actions.
"""
import json

from google_auth_oauthlib.flow import InstalledAppFlow

flow = InstalledAppFlow.from_client_secrets_file(
    "client_secret.json", scopes=["https://www.googleapis.com/auth/youtube.upload"])
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
info = json.load(open("client_secret.json"))["installed"]
print("\nYT_CLIENT_ID     =", info["client_id"])
print("YT_CLIENT_SECRET =", info["client_secret"])
print("YT_REFRESH_TOKEN =", creds.refresh_token)
