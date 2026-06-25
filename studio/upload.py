from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def build_body(meta: dict) -> dict:
    status = {"privacyStatus": meta.get("visibility", "private"),
              "selfDeclaredMadeForKids": False}
    if meta.get("publish_at"):
        status["publishAt"] = meta["publish_at"]
        status["privacyStatus"] = "private"  # required by API when scheduling
        if meta.get("visibility") == "public":
            status["privacyStatus"] = "public"
    return {
        "snippet": {
            "title": meta["title"],
            "description": meta["description"],
            "tags": meta.get("tags", []),
            "categoryId": meta.get("category_id", "22"),
        },
        "status": status,
    }


def _service(client_secret: str, token: str):
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if Path(token).exists():
        creds = Credentials.from_authorized_user_file(token, SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(client_secret, SCOPES)
        creds = flow.run_local_server(port=0)
        Path(token).write_text(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def upload(video: Path, thumb: Path, meta: dict, *, client_secret: str, token: str) -> str:
    from googleapiclient.http import MediaFileUpload
    service = _service(client_secret, token)
    request = service.videos().insert(
        part="snippet,status", body=build_body(meta),
        media_body=MediaFileUpload(str(video), resumable=True),
    )
    response = request.execute()
    video_id = response["id"]
    if thumb and Path(thumb).exists():
        service.thumbnails().set(
            videoId=video_id, media_body=MediaFileUpload(str(thumb))).execute()
    return video_id
