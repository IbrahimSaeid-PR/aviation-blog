import requests

N8N_WEBHOOK = "http://localhost:5678/webhook-test/send-notification"
TIMEOUT = 3

def post_published(post):
    payload = {
        "event": "post_published",
        "user_id" : post.author.id,
        "post_id": post.id,
        "title": post.title,
        "author": post.author.username,
        "author_email": post.author.email,
        "has_image": bool(post.image_file),
        "has_video": bool(post.video_file),
        "created_at": post.date.isoformat(),
        "content": post.text,
    }
    try:
        requests.post(N8N_WEBHOOK, json=payload, timeout=TIMEOUT)
    except requests.RequestException:
       
        pass
