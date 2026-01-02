# server.py (top part)
import os
import json
import re
import time
from flask import Flask, request, jsonify, make_response, send_from_directory
import requests

# Serve frontend
app = Flask(
    __name__,
    static_folder="frontend",
    static_url_path=""
)

# ===== RAILWAY CORS FIX =====
# This is guaranteed to work with Vercel frontend
FRONTEND_URL = "https://ig-ecru.vercel.app"

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = FRONTEND_URL
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    return response

# Catch all OPTIONS requests for preflight
@app.route('/<path:path>', methods=['OPTIONS'])
def catch_all_options(path):
    response = make_response()
    response.headers['Access-Control-Allow-Origin'] = FRONTEND_URL
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    return response

@app.route('/', methods=['OPTIONS'])
def root_options():
    response = make_response()
    response.headers['Access-Control-Allow-Origin'] = FRONTEND_URL
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    return response

print(f"[server.py] CORS enabled for frontend: {FRONTEND_URL}")
# ===== END CORS FIX =====



# Load session from environment or config.json (if present)
def load_instagram_session():
    sid = os.environ.get("INSTAGRAM_SESSIONID")
    ds_user_id = os.environ.get("INSTAGRAM_DS_USER_ID")
    if sid and ds_user_id:
        return {"sessionid": sid, "ds_user_id": ds_user_id}
    # fallback: config.json (not recommended for prod)
    cfg_path = "config.json"
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r") as f:
                cfg = json.load(f)
                if cfg.get("INSTAGRAM_SESSIONID") and cfg.get("INSTAGRAM_DS_USER_ID"):
                    return {"sessionid": cfg["INSTAGRAM_SESSIONID"], "ds_user_id": cfg["INSTAGRAM_DS_USER_ID"]}
        except Exception:
            pass
    return {}

INSTAGRAM_SESSION = load_instagram_session()

@app.route("/")
def root():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/api/extract-reel", methods=["POST"])
def extract_reel():
    data = request.get_json(silent=True) or {}
    reel_url = data.get("url")
    if not reel_url:
        return jsonify({"error": "No URL provided"}), 400

    # Try to extract shortcode from common Instagram URL patterns
    match = re.search(r"/(reel|p|tv)/([A-Za-z0-9_-]+)", reel_url)
    if not match:
        # Also accept full query style shortcodes
        m2 = re.search(r"instagram\.com\/([A-Za-z0-9_.-]+)\/?(\?.*)?$", reel_url)
        if m2:
            # best-effort: user might have provided a short link
            shortcode = m2.group(1)
        else:
            return jsonify({"error": "Invalid Instagram URL"}), 400
    else:
        shortcode = match.group(2)

    # Try methods in order
    video_url = None
    try:
        video_url = get_video_from_official_api(shortcode)
    except Exception as e:
        app.logger.debug("Official API attempt failed: %s", e)

    if not video_url:
        try:
            video_url = get_video_from_mobile_api(shortcode)
        except Exception as e:
            app.logger.debug("Mobile API attempt failed: %s", e)

    if not video_url:
        try:
            video_url = get_video_from_graphql(shortcode)
        except Exception as e:
            app.logger.debug("GraphQL attempt failed: %s", e)

    if video_url:
        return jsonify({
            "success": True,
            "video_url": video_url,
            "shortcode": shortcode,
            "timestamp": int(time.time())
        })

    return jsonify({
        "error": "Failed to extract video. Instagram may have updated their API or session may be invalid.",
        "shortcode": shortcode
    }), 500

def get_instagram_cookies():
    # Return a cookie dict usable by requests
    if INSTAGRAM_SESSION.get("sessionid"):
        return {"sessionid": INSTAGRAM_SESSION["sessionid"], "ds_user_id": INSTAGRAM_SESSION.get("ds_user_id", "")}
    return {}

def get_video_from_official_api(shortcode):
    """
    Use the public '?__a=1' endpoint (may return JSON or HTML depending on Instagram)
    """
    # Try both 'p' and 'reel' forms (IG sometimes expects different slugs)
    candidates = [
        f"https://www.instagram.com/reel/{shortcode}/?__a=1&__d=dis",
        f"https://www.instagram.com/p/{shortcode}/?__a=1&__d=dis",
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept-Language": "en-US,en;q=0.9",
    }
    cookies = get_instagram_cookies()
    for url in candidates:
        try:
            resp = requests.get(url, headers=headers, cookies=cookies, timeout=10)
            if resp.status_code != 200:
                continue
            # Instagram sometimes returns HTML - try to parse JSON safely
            try:
                data = resp.json()
            except ValueError:
                # try to extract JSON embedded in the HTML as a fallback
                text = resp.text
                m = re.search(r"window\._sharedData\s*=\s*({.+?});</script>", text)
                if m:
                    data = json.loads(m.group(1))
                else:
                    continue

            # Different JSON shapes exist; attempt to locate video_url
            # GraphQL style:
            if isinstance(data, dict):
                # graphql.shortcode_media
                g = data.get("graphql", {}).get("shortcode_media")
                if g and g.get("is_video"):
                    return g.get("video_url")
                # edge_sidecar_to_children
                if g and g.get("edge_sidecar_to_children"):
                    for edge in g["edge_sidecar_to_children"].get("edges", []):
                        node = edge.get("node", {})
                        if node.get("is_video"):
                            return node.get("video_url")

                # legacy path (some responses)
                if "items" in data:
                    for item in data["items"]:
                        if "video_versions" in item:
                            vids = item["video_versions"]
                            best = max(vids, key=lambda x: x.get("height", 0))
                            return best.get("url")
        except Exception:
            continue
    return None

def get_video_from_mobile_api(shortcode):
    """
    Use mobile API to get media info by media_id -> /api/v1/media/{media_id}/info/
    """
    media_id = get_media_id_from_shortcode(shortcode)
    if not media_id:
        return None

    url = f"https://i.instagram.com/api/v1/media/{media_id}/info/"
    headers = {
        "User-Agent": "Instagram 219.0.0.12.117 Android",
        "X-IG-App-ID": "936619743392459",
        "Accept": "*/*",
    }
    cookies = get_instagram_cookies()
    resp = requests.get(url, headers=headers, cookies=cookies, timeout=10)
    if resp.status_code != 200:
        return None
    try:
        data = resp.json()
        items = data.get("items") or []
        if items:
            item = items[0]
            if "video_versions" in item:
                vids = item["video_versions"]
                best = max(vids, key=lambda x: x.get("height", 0))
                return best.get("url")
    except Exception:
        return None
    return None

def get_media_id_from_shortcode(shortcode):
    """
    Convert Instagram shortcode to media ID via base64-like decode algorithm
    """
    try:
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        media_id = 0
        for c in shortcode:
            media_id = media_id * 64 + alphabet.index(c)
        return str(media_id)
    except Exception:
        return None

def get_video_from_graphql(shortcode):
    """
    Use GraphQL query endpoint as a fallback
    """
    query_hash = "2b0673e0dc4580674a88d426fe00ea90"
    variables = {
        "shortcode": shortcode,
        "child_comment_count": 3,
        "fetch_comment_count": 40,
        "parent_comment_count": 24,
        "has_threaded_comments": True
    }
    url = "https://www.instagram.com/graphql/query/"
    params = {"query_hash": query_hash, "variables": json.dumps(variables)}
    headers = {
        "User-Agent": "Instagram 219.0.0.12.117 Android",
        "X-IG-App-ID": "936619743392459",
        "Accept": "*/*",
    }
    cookies = get_instagram_cookies()
    resp = requests.get(url, headers=headers, params=params, cookies=cookies, timeout=10)
    if resp.status_code != 200:
        return None
    try:
        data = resp.json()
        media = data.get("data", {}).get("shortcode_media", {})
        if media and media.get("is_video"):
            return media.get("video_url")
        # clips/other shapes
        clip_info = media.get("clips_music_attribution_info") or {}
        if clip_info.get("video_url"):
            return clip_info.get("video_url")
    except Exception:
        return None
    return None

if __name__ == "__main__":
    # show helpful message if no session loaded
    if not INSTAGRAM_SESSION:
        app.logger.warning("No Instagram session loaded. Set environment variables INSTAGRAM_SESSIONID and INSTAGRAM_DS_USER_ID or config.json.")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
