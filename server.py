# server.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import re
import time

app = Flask(__name__)
CORS(app)

# Instagram session (you need to get this once)
INSTAGRAM_SESSION = {
    'sessionid': 'YOUR_SESSION_ID_HERE',  # Get from browser cookies
    'ds_user_id': 'YOUR_USER_ID'
}

def get_instagram_session():
    """Login to Instagram once to get session"""
    # You need to do this manually first:
    # 1. Go to instagram.com in browser
    # 2. Login
    # 3. Copy 'sessionid' and 'ds_user_id' from cookies
    # 4. Paste here
    return INSTAGRAM_SESSION

@app.route('/api/extract-reel', methods=['POST'])
def extract_reel():
    data = request.json
    reel_url = data.get('url')
    
    if not reel_url:
        return jsonify({'error': 'No URL provided'}), 400
    
    # Extract shortcode
    match = re.search(r'/reel/([A-Za-z0-9_-]+)', reel_url)
    if not match:
        match = re.search(r'/p/([A-Za-z0-9_-]+)', reel_url)
    
    if not match:
        return jsonify({'error': 'Invalid Instagram URL'}), 400
    
    shortcode = match.group(1)
    
    # Method 1: Use Instagram's official API (most reliable)
    video_url = get_video_from_official_api(shortcode)
    
    if not video_url:
        # Method 2: Use mobile API with session
        video_url = get_video_from_mobile_api(shortcode)
    
    if not video_url:
        # Method 3: Use GraphQL with session
        video_url = get_video_from_graphql(shortcode)
    
    if video_url:
        return jsonify({
            'success': True,
            'video_url': video_url,
            'shortcode': shortcode,
            'timestamp': int(time.time())
        })
    
    return jsonify({
        'error': 'Failed to extract video. Instagram may have updated their API.',
        'shortcode': shortcode
    }), 500

def get_video_from_official_api(shortcode):
    """Use Instagram's official media endpoint"""
    try:
        url = f"https://www.instagram.com/p/{shortcode}/?__a=1&__d=dis"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
        
        session = get_instagram_session()
        response = requests.get(url, headers=headers, cookies=session, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Navigate through Instagram's JSON structure
            if 'graphql' in data:
                media = data['graphql'].get('shortcode_media', {})
                
                if media.get('is_video'):
                    return media.get('video_url')
                
                # Check for video in carousel
                if 'edge_sidecar_to_children' in media:
                    edges = media['edge_sidecar_to_children']['edges']
                    for edge in edges:
                        if edge['node'].get('is_video'):
                            return edge['node'].get('video_url')
            
            # Alternative path for Reels
            if 'items' in data:
                for item in data['items']:
                    if 'video_versions' in item:
                        # Get highest quality
                        videos = item['video_versions']
                        return max(videos, key=lambda x: x.get('height', 0))['url']
    
    except Exception as e:
        print(f"Official API error: {e}")
    
    return None

def get_video_from_mobile_api(shortcode):
    """Use Instagram's mobile API endpoint"""
    try:
        # First get media ID
        media_id = get_media_id_from_shortcode(shortcode)
        if not media_id:
            return None
        
        url = f"https://i.instagram.com/api/v1/media/{media_id}/info/"
        
        headers = {
            'User-Agent': 'Instagram 219.0.0.12.117 Android',
            'X-IG-App-ID': '936619743392459',
            'Accept': '*/*',
            'Accept-Language': 'en-US',
            'X-Requested-With': 'XMLHttpRequest',
        }
        
        session = get_instagram_session()
        response = requests.get(url, headers=headers, cookies=session, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'items' in data and len(data['items']) > 0:
                item = data['items'][0]
                
                if 'video_versions' in item:
                    videos = item['video_versions']
                    # Get highest quality video
                    best_video = max(videos, key=lambda x: x.get('height', 0))
                    return best_video['url']
    
    except Exception as e:
        print(f"Mobile API error: {e}")
    
    return None

def get_media_id_from_shortcode(shortcode):
    """Convert shortcode to media ID"""
    try:
        # Instagram's algorithm to convert shortcode to media ID
        alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
        media_id = 0
        
        for char in shortcode:
            media_id = (media_id * 64) + alphabet.index(char)
        
        return str(media_id)
    except:
        return None

def get_video_from_graphql(shortcode):
    """Use Instagram's GraphQL endpoint"""
    try:
        query_hash = "2b0673e0dc4580674a88d426fe00ea90"  # For media data
        
        variables = {
            "shortcode": shortcode,
            "child_comment_count": 3,
            "fetch_comment_count": 40,
            "parent_comment_count": 24,
            "has_threaded_comments": True
        }
        
        url = f"https://www.instagram.com/graphql/query/"
        params = {
            'query_hash': query_hash,
            'variables': json.dumps(variables)
        }
        
        headers = {
            'User-Agent': 'Instagram 219.0.0.12.117 Android',
            'X-IG-App-ID': '936619743392459',
            'Accept': '*/*',
            'Accept-Language': 'en-US',
            'X-Requested-With': 'XMLHttpRequest',
        }
        
        session = get_instagram_session()
        response = requests.get(url, params=params, headers=headers, cookies=session, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Navigate through GraphQL response
            if 'data' in data and 'shortcode_media' in data['data']:
                media = data['data']['shortcode_media']
                
                if media.get('is_video'):
                    return media.get('video_url')
                
                # Check for Reels
                if 'clips_music_attribution_info' in media:
                    clip_info = media['clips_music_attribution_info']
                    if 'video_url' in clip_info:
                        return clip_info['video_url']
    
    except Exception as e:
        print(f"GraphQL error: {e}")
    
    return None

if __name__ == '__main__':
    app.run(debug=True, port=5000)
