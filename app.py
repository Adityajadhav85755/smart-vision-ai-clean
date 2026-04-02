from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
from werkzeug.utils import secure_filename
from ultralytics import YOLO
import cv2
import numpy as np
import base64
from auth import signup_user, login_user, is_logged_in, get_current_user, logout_user, get_pending_users, update_user_status, get_all_students, get_all_sessions, get_user_details
from activity_logger import start_session, log_activity, end_session
app = Flask(__name__)
# Add at the top with other imports
import google.generativeai as genai
import json
import re
from datetime import datetime
# ==================== GEMINI AI CONFIGURATION ====================
GEMINI_API_KEY = "AIzaSyDVRKiDcrHcthpXp2qjDQwO_0xLTQ5z6J4"  # Replace with valid key␍
# Load API keys from environment variables for deployment security
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
if not GEMINI_API_KEY:
    print("⚠️ GEMINI_API_KEY not found in environment variables")
    print("📝 Please set GEMINI_API_KEY environment variable for deployment")
    print("🔧 For local development, create config.py with API_CONFIG")
    try:
        from static.js.config import API_CONFIG
        GEMINI_API_KEY = API_CONFIG.get('GEMINI_API_KEY', '')
        if GEMINI_API_KEY:
            print("✅ Using Gemini API key from config.js")
    except ImportError:
        print("❌ No Gemini API key available - AI features will be disabled")
print("=" * 60)
print("🔧 GEMINI INITIALIZATION")
print("=" * 60)

# Only initialize Gemini if API key is available
if GEMINI_API_KEY and GEMINI_API_KEY != 'YOUR_NEW_GEMINI_API_KEY_HERE':
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        print("✅ API Key configured successfully")
        # List available models for debugging
        print("\n📋 Available models:")
        available_models = []
        for m in genai.list_models():
            print(f"  - {m.name}")
            available_models.append(m.name)
        # CORRECT model names - WITHOUT 'models/' prefix for your API version
        model_names = [
        'models/gemini-2.0-flash',      # Newer model
        'models/gemini-2.0-flash-lite', # Lite version
        'models/gemini-2.5-flash',      # Latest flash
        'models/gemini-2.5-pro',        # Latest pro
        'models/gemini-pro-latest',     # Latest pro version
        'models/gemini-flash-latest',   # Latest flash version
        ]
        gemini_model = None
        selected_model = None
        for model_name in model_names:
            # Check if model exists in available models
            matching_models = [m for m in available_models if model_name in m]
            if matching_models:
                try:
                    full_model_name = matching_models[0]  # Use full name from API
                    print(f"\n🔄 Trying model: {full_model_name}")
                    gemini_model = genai.GenerativeModel(full_model_name)
                    # Test with a simple prompt
                    test_response = gemini_model.generate_content("Say 'OK'")
                    if test_response and test_response.text:
                        print(f"✅✅✅ SUCCESS! Using model: {full_model_name}")
                        selected_model = full_model_name
                        break
                    else:
                        print(f"⚠️ Model {full_model_name} returned empty response")
                        gemini_model = None
                except Exception as e:
                    print(f"❌ Model {model_name} failed: {e}")
                    gemini_model = None
            else:
                print(f"⚠️ Model {model_name} not found in available models")
        if gemini_model is None:
            print("\n❌ No valid Gemini model found")
    except Exception as e:
        print(f"\n❌ Gemini initialization error: {e}")
        gemini_model = None
else:
    print("⚠️ Gemini API key not configured")
    print("📝 AI recommendations will use fallback mode")
    gemini_model = None
print("=" * 60)
def get_smart_recommendations(detected_objects):
    """
    Use Gemini AI to generate intelligent reuse recommendations
    """
    print(f"\n🔍 get_smart_recommendations called with {len(detected_objects)} objects")
    if gemini_model is None:
        print("❌ gemini_model is None - AI not available")
        return None
    try:
        # Create prompt with detected objects
        objects_description = "\n".join([
            f"- {obj['class']} (confidence: {obj['confidence']}%)"
            for obj in detected_objects
        ])
        print(f"📝 Sending prompt to Gemini...")
        prompt = f"""You are a helpful AI assistant for waste management and recycling.
I have detected these objects in an image:
{objects_description}
For EACH object, provide SPECIFIC and CREATIVE reuse ideas based on the actual object.
DO NOT use generic suggestions like "clean and reuse".
Example for "cup":
- "Transform into a unique pencil holder for your desk"
- "Create a mini succulent planter with drainage holes"
- "Use as a DIY organizer for makeup brushes or art supplies"
Example for "dining table":
- "Convert into a stylish home office desk"
- "Refinish and use as a craft or sewing table"
- "Repurpose as an outdoor patio table with weatherproofing"
Return ONLY valid JSON in this exact format, no other text:
{{
    "objects": [
        {{
            "name": "object_name",
            "status": "usable",
            "reuse_ideas": ["specific idea 1", "specific idea 2", "specific idea 3"],
            "usage_locations": ["specific location 1", "specific location 2", "specific location 3"],
            "step_by_step_guide": "detailed step-by-step instructions for the best reuse idea"
        }}
    ]
}}"""
        # Get AI response
        response = gemini_model.generate_content(prompt)
        print(f"📥 Received response from Gemini")
        if not response or not response.text:
            print("❌ Empty response from Gemini")
            return None
        print(f"📄 Response preview: {response.text[:200]}...")
        
        # Check for quota exceeded or rate limit errors
        response_text = response.text.lower()
        if any(keyword in response_text for keyword in ['quota', 'rate limit', 'exceeded', 'limit', 'retry', 'blocked']):
            print("❌ Gemini API quota/rate limit exceeded")
            return None
        
        # Parse JSON from response with better error handling
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            try:
                # Validate JSON structure before parsing
                if not json_str.strip().startswith('{') or not json_str.strip().endswith('}'):
                    print("❌ Invalid JSON structure")
                    return None
                
                recommendations = json.loads(json_str)
                objects = recommendations.get('objects', [])
                
                # Validate the structure of returned objects
                if not isinstance(objects, list):
                    print("❌ Invalid objects structure in JSON")
                    return None
                
                print(f"✅ Successfully parsed JSON with {len(objects)} objects")
                return objects
                
            except json.JSONDecodeError as e:
                print(f"❌ JSON parse error: {e}")
                print(f"Raw JSON string: {json_str[:200]}")
                return None
        else:
            print("❌ No JSON found in response")
            return None
    except Exception as e:
        print(f"❌ AI recommendation error: {e}")
        return None
def get_fallback_recommendations(detected_objects):
    """Fallback recommendations if AI fails"""
    recommendations = []
    for obj in detected_objects:
        obj_class = obj['class'].lower()
        if obj_class in ['person', 'dog', 'cat', 'car', 'truck', 'bus', 'bicycle']:
            status = 'non_usable'
            disposal = "Not applicable - this is not waste"
            recycling = "N/A"
            safety = "No action needed"
            reuse = ["N/A - this is not a waste item"]
            locations = ["N/A"]
            steps = "This is not a waste item that needs disposal or reuse."
        elif obj_class in ['apple', 'orange', 'banana', 'food']:
            status = 'usable'
            disposal = "Compost if not usable"
            recycling = "Can be composted"
            safety = "Wash before use"
            reuse = ["Compost for garden", "Make natural cleaner", "Use as biodegradable material"]
            locations = ["Kitchen", "Garden", "Compost bin"]
            steps = "1. Wash thoroughly\n2. Use for cooking\n3. Compost remaining parts"
        else:
            status = 'usable'
            disposal = "Recycle if possible"
            recycling = "Check local recycling guidelines"
            safety = "Clean before reuse"
            reuse = [f"Clean and reuse as {obj_class}", "Repurpose for storage", "Donate if in good condition"]
            locations = ["Home", "Office", "Garden"]
            steps = f"1. Clean thoroughly\n2. Inspect for damage\n3. Reuse as {obj_class}\n4. Recycle when done"
        item = {
            'name': obj['class'],
            'status': status,
            'reuse_ideas': reuse[:3],
            'usage_locations': locations[:3],
            'step_by_step_guide': steps,
            'disposal_method': disposal,
            'recycling_guide': recycling,
            'safety_tips': safety
        }
        recommendations.append(item)
    return recommendations
# Configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MODEL_PATH = 'models/yolov8n_35class/weights/best.pt'
FALLBACK_MODEL = 'yolov8n.pt'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
app.secret_key = "super-secret-key-can-change-this"
# Create directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('models', exist_ok=True)
# Load model (cached for performance)
model = None
# ==================== CLASS MAPPINGS FOR RECOMMENDATIONS ====================
USABLE_CLASSES = [
    'Bottle', 'Cup', 'Spoon', 'Fork', 'Cell Phone',
    'Toothbrush', 'Book', 'Chair', 'Bench', 'Bed',
    'Refrigerator', 'Oven', 'Tap', 'Currency'
]
OBSTACLE_CLASSES = [
    'Path Holes', 'Barriers', 'Stairs', 'Knife',
    'Traffic Light', 'Stop Sign', 'Bin'
]
NEUTRAL_CLASSES = [
    'Person', 'Dog', 'Cat', 'Car', 'Bus', 'Truck',
    'Motorcycles', 'Bicycle', 'Airplane', 'Train',
    'Face', 'Men Sign', 'Women Sign', 'Blind Stick'
]
CLASS_RECOMMENDATIONS = {
    'Bottle': '✅ Reusable container - recycle or refill',
    'Cup': '✅ Usable - wash and reuse',
    'Spoon': '✅ Usable utensil - clean and reuse',
    'Fork': '✅ Usable utensil - clean and reuse',
    'Cell Phone': '📱 Electronic device - recycle at e-waste facility if broken',
    'Toothbrush': ' Replace every 3-4 months - recycle handle',
    'Chair': ' Furniture - repair if damaged or donate',
    'Bench': ' Outdoor furniture - treat wood/metal if weathered',
    'Bed': ' Bedding - replace mattress every 8 years',
    'Refrigerator': '❄️ Large appliance - professional recycling required',
    'Oven': '🔥 Large appliance - professional recycling required',
    'Tap': '💧 Plumbing fixture - replace if leaking',
    'Currency': '💰 Keep in circulation or deposit',
    'Path Holes': '⚠️ SAFETY HAZARD - Report to maintenance',
    'Barriers': ' Construction area - proceed with caution',
    'Stairs': ' Use handrail - watch your step',
    'Knife': '🔪 Sharp object - handle with care',
    'Traffic Light': '🚦 Follow signals for safety',
    'Stop Sign': '🛑 Obey traffic rules',
    'Bin': '🗑️ Waste container - dispose trash properly',
    'default_usable': ' Usable item - handle appropriately',
    'default_obstacle': '⚠️ Be cautious of this object',
    'default_neutral': ' Object detected - no action needed'
}
# ==================== SECURITY HEADERS ====================
@app.after_request
def set_security_headers(response):
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://unpkg.com https://www.googletagmanager.com; "
        "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com https://unpkg.com https://fonts.gstatic.com; "
        "font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
        "connect-src 'self' https://api.x.ai https://api.allorigins.win https://www.google-analytics.com; "
        "img-src 'self' data: blob: https: http:; "
        "media-src 'self' https://cdn.pixabay.com blob: data:; "
        "frame-src 'self' https://www.openstreetmap.org https://www.youtube.com https://player.vimeo.com; "
        "frame-ancestors 'none';"
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response
def load_model():
    global model
    if model is None:
        try:
            if os.path.exists(MODEL_PATH):
                model = YOLO(MODEL_PATH)
                print(f"✅ Custom model loaded from {MODEL_PATH}")
            else:
                model = YOLO(FALLBACK_MODEL)
                print(f"⚠️ Using pre-trained model (detects 80 COCO classes)")
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            model = None
    return model
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
def get_class_status(class_name):
    if class_name in USABLE_CLASSES:
        return 'usable'
    elif class_name in OBSTACLE_CLASSES:
        return 'obstacle'
    elif class_name in NEUTRAL_CLASSES:
        return 'neutral'
    else:
        return 'unknown'
def get_recommendation_for_class(class_name, confidence):
    if class_name in CLASS_RECOMMENDATIONS:
        base_rec = CLASS_RECOMMENDATIONS[class_name]
    else:
        status = get_class_status(class_name)
        if status == 'usable':
            base_rec = CLASS_RECOMMENDATIONS['default_usable']
        elif status == 'obstacle':
            base_rec = CLASS_RECOMMENDATIONS['default_obstacle']
        else:
            base_rec = CLASS_RECOMMENDATIONS['default_neutral']
    if confidence > 0.8:
        confidence_note = " (High confidence detection)"
    elif confidence > 0.5:
        confidence_note = " (Moderate confidence)"
    else:
        confidence_note = " (Low confidence - verify manually)"
    return base_rec + confidence_note
def analyze_scene(results):
    detections = []
    usable_count = 0
    obstacle_count = 0
    neutral_count = 0
    for r in results:
        boxes = r.boxes
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            class_name = model.names[cls]
            status = get_class_status(class_name)
            if status == 'usable':
                usable_count += 1
            elif status == 'obstacle':
                obstacle_count += 1
            else:
                neutral_count += 1
            detections.append({
                'class': class_name,
                'confidence': round(conf, 2),
                'bbox': [int(x1), int(y1), int(x2), int(y2)],
                'status': status,
                'recommendation': get_recommendation_for_class(class_name, conf)
            })
    # Get AI-powered smart recommendations
    if detections:
        try:
            smart_recs = get_smart_recommendations(detections)
            if smart_recs is None:
                print("⚠️ Using fallback recommendations (AI failed)")
                smart_recs = get_fallback_recommendations(detections)
        except Exception as e:
            print(f"⚠️ Error in AI recommendations, using fallback: {e}")
            smart_recs = get_fallback_recommendations(detections)
        for i, det in enumerate(detections):
            if i < len(smart_recs):
                det['smart_recommendations'] = smart_recs[i]
    summary = []
    if usable_count > 0:
        summary.append(f"🎯 Found {usable_count} usable item(s)")
    if obstacle_count > 0:
        summary.append(f"⚠️ {obstacle_count} obstacle(s)/hazard(s) detected")
    if gemini_model is None:
        summary.append("ℹ️ Using basic recommendations")
    else:
        summary.append("✨ AI-powered recommendations enabled")
    return detections, summary
# ==================== ROUTES ====================
@app.route('/')
def home():
    return render_template('home.html')
@app.route('/detection')
def detection():
    return render_template('detection.html')
@app.route('/about')
def about():
    return render_template('about.html')
@app.route('/contact')
def contact():
    return render_template('contact.html')
@app.route('/features')
def features():
    return render_template('features.html')
@app.route('/3d-experience')
def animated_galaxy():
    return render_template('3DAnime.html')
@app.route('/dashboard')
def dashboard():
    if not is_logged_in():
        return redirect('/login_page')
    
    # Get current user email and details
    email, session_id = get_current_user()
    user_details = get_user_details(email)
    
    return render_template('dashboard.html', user=user_details)
@app.route('/admin')
def admin():
    if not is_logged_in():
        return redirect('/login_page')
    return render_template('admin.html')
@app.route('/login_page')
def login_page():
    return render_template('login.html')
@app.route('/signup_page')
def signup_page():
    return render_template('signup.html')
@app.route('/student_signup', methods=['POST'])
def student_signup():
    data = request.json
    success, msg = signup_user(data["email"], data["password"])
    return jsonify({"success": success, "message": msg})
@app.route('/admin_signup', methods=['POST'])
def admin_signup():
    data = request.json
    access_key = data.get("access_key", "")
    ADMIN_ACCESS_KEY = "admin2026"
    if access_key != ADMIN_ACCESS_KEY:
        return jsonify({"success": False, "message": "Invalid admin access key"}), 401
    success, msg = signup_user(data["email"], data["password"], is_student=False)
    return jsonify({"success": success, "message": msg})
@app.route('/api/upload-history')
def get_upload_history():
    if not is_logged_in():
        return jsonify({'error': 'Unauthorized'}), 401
    uploads = []
    # Use absolute path relative to app.py
    base_dir = os.path.dirname(os.path.abspath(__file__))
    upload_dir = os.path.join(base_dir, 'static', 'uploads')
    now = datetime.now()
    this_month_count = 0
    if os.path.exists(upload_dir):
        # Filter for original images (exclude annotated ones)
        files = [f for f in os.listdir(upload_dir) if os.path.isfile(os.path.join(upload_dir, f)) and not f.startswith('annotated_')]
        # Sort files by modification time (newest first)
        files.sort(key=lambda x: os.path.getmtime(os.path.join(upload_dir, x)), reverse=True)
        for filename in files:
            filepath = os.path.join(upload_dir, filename)
            stat = os.stat(filepath)
            mtime = datetime.fromtimestamp(stat.st_mtime)
            if mtime.year == now.year and mtime.month == now.month:
                this_month_count += 1
            # Check for annotated version
            annotated_filename = f"annotated_{filename}"
            has_annotated = os.path.exists(os.path.join(upload_dir, annotated_filename))
            uploads.append({
                'filename': filename,
                'url': f"/static/uploads/{filename}",
                'annotated_url': f"/static/uploads/{annotated_filename}" if has_annotated else None,
                'timestamp': mtime.strftime('%Y-%m-%d %H:%M:%S'),
                'size': f"{stat.st_size / 1024:.1f} KB"
            })
    return jsonify({
        'total': len(uploads),
        'this_month': this_month_count,
        'uploads': uploads
    })
@app.route('/api/admin/pending_students')
def admin_pending_students():
    if not is_logged_in():
        return jsonify({"error": "Unauthorized"}), 401
    # Add actual admin check here if needed
    pending = get_pending_users()
    return jsonify({"success": True, "pending": pending})
@app.route('/api/admin/approve_student', methods=['POST'])
def admin_approve_student():
    if not is_logged_in():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    email = data.get("email")
    if update_user_status(email, "approved"):
        return jsonify({"success": True, "message": "Student approved"})
    return jsonify({"success": False, "message": "Failed to approve student"})
@app.route('/api/admin/reject_student', methods=['POST'])
def admin_reject_student():
    if not is_logged_in():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    email = data.get("email")
    if update_user_status(email, "rejected"):
        return jsonify({"success": True, "message": "Student rejected"})
    return jsonify({"success": False, "message": "Failed to reject student"})
@app.route('/api/admin/all_students')
def admin_all_students():
    if not is_logged_in():
        return jsonify({"error": "Unauthorized"}), 401
    students = get_all_students()
    return jsonify({"success": True, "students": students})
@app.route('/api/admin/all_sessions')
def admin_all_sessions():
    if not is_logged_in():
        return jsonify({"error": "Unauthorized"}), 401
    sessions = get_all_sessions()
    return jsonify({"success": True, "sessions": sessions})
@app.route('/student_login', methods=['POST'])
def student_login():
    data = request.json
    success, result = login_user(data["email"], data["password"])
    if not success:
        return jsonify({"success": False, "message": result}), 401
    email, session_id = get_current_user()
    start_session(email, session_id)
    log_activity(email, session_id, "student_login")
    return jsonify({"success": True})
@app.route('/admin_login', methods=['POST'])
def admin_login():
    data = request.json
    success, result = login_user(data["email"], data["password"])
    if not success:
        return jsonify({"success": False, "message": result}), 401
    email, session_id = get_current_user()
    start_session(email, session_id)
    log_activity(email, session_id, "admin_login")
    return jsonify({"success": True})
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    success, result = login_user(data["email"], data["password"])
    if not success:
        return jsonify({"success": False, "message": result}), 401
    email, session_id = get_current_user()
    start_session(email, session_id)
    log_activity(email, session_id, "login")
    return jsonify({"success": True})
@app.route('/logout')
def logout():
    email, session_id = get_current_user()
    end_session(email, session_id)
    log_activity(email, session_id, "logout")
    logout_user()
    return redirect(url_for('login_page'))
@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        print(f"🔍 Upload request received: {request.method}")
        print(f"🔍 Files in request: {list(request.files.keys())}")
        print(f"🔍 Form data: {list(request.form.keys())}")
        
        if 'file' not in request.files:
            print("❌ No file in request")
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        print(f"🔍 File object: {file}")
        print(f"🔍 Filename: {file.filename}")
        
        if file.filename == '':
            print("❌ Empty filename")
            return jsonify({'error': 'No selected file'}), 400
        
        if file and allowed_file(file.filename):
            try:
                # Generate unique filename to prevent conflicts
                import uuid
                from datetime import datetime
                import glob
                
                original_filename = secure_filename(file.filename)
                file_extension = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                unique_id = str(uuid.uuid4())[:8]
                filename = f"{timestamp}_{unique_id}.{file_extension}" if file_extension else f"{timestamp}_{unique_id}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                print(f"🔍 Generated unique filename: {filename}")
                print(f"🔍 Saving to: {filepath}")
                
                # Ensure upload directory exists
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                
                # Clean up old files to prevent disk space issues (keep only last 50 files)
                try:
                    upload_dir = app.config['UPLOAD_FOLDER']
                    files = glob.glob(os.path.join(upload_dir, '*'))
                    files = [f for f in files if os.path.isfile(f) and not f.startswith('annotated_')]
                    files.sort(key=os.path.getmtime, reverse=True)
                    
                    # Keep only the 50 most recent files
                    if len(files) > 50:
                        for old_file in files[50:]:
                            try:
                                os.remove(old_file)
                                # Also remove corresponding annotated file if exists
                                annotated_file = os.path.join(upload_dir, f"annotated_{os.path.basename(old_file)}")
                                if os.path.exists(annotated_file):
                                    os.remove(annotated_file)
                                print(f"🗑️ Cleaned up old file: {os.path.basename(old_file)}")
                            except Exception as cleanup_error:
                                print(f"⚠️ Could not clean up file {old_file}: {cleanup_error}")
                except Exception as cleanup_error:
                    print(f"⚠️ Cleanup failed: {cleanup_error}")
                
                # Save file with error handling
                try:
                    file.save(filepath)
                    print(f"✅ File saved successfully")
                except Exception as save_error:
                    print(f"❌ File save failed: {str(save_error)}")
                    return jsonify({'error': f'File save failed: {str(save_error)}'}), 500
                
                # Load model with timeout protection (reuse global model)
                try:
                    global model
                    if model is None:
                        model = load_model()
                    if model is None:
                        return jsonify({'error': 'Model not available.'}), 500
                    print(f"✅ Model ready")
                except Exception as model_error:
                    print(f"❌ Model loading failed: {str(model_error)}")
                    return jsonify({'error': f'Model loading failed: {str(model_error)}'}), 500
                
                # Process image with optimized settings
                try:
                    print("🔍 Starting image analysis...")
                    # Use smaller image size for faster processing
                    img = cv2.imread(filepath)
                    if img is None:
                        return jsonify({'error': 'Could not read uploaded image'}), 500
                    
                    # Resize large images to reduce memory usage
                    height, width = img.shape[:2]
                    if max(height, width) > 1024:
                        scale = 1024 / max(height, width)
                        new_width = int(width * scale)
                        new_height = int(height * scale)
                        img = cv2.resize(img, (new_width, new_height))
                        print(f"🔍 Image resized to {new_width}x{new_height}")
                    
                    # Run inference with optimized settings
                    results = model(img, verbose=False)
                    detections, summary = analyze_scene(results)
                    print(f"✅ Analysis completed: {len(detections)} objects detected")
                except Exception as analysis_error:
                    print(f"❌ Detection failed: {str(analysis_error)}")
                    return jsonify({'error': f'Detection failed: {str(analysis_error)}'}), 500
                
                # Create annotated image (optional - skip if too many detections)
                annotated_path = None
                try:
                    if len(detections) <= 20:  # Only annotate if reasonable number of objects
                        for det in detections:
                            x1, y1, x2, y2 = det['bbox']
                            color = (0, 255, 0) if det['status'] == 'usable' else (0, 0, 255) if det['status'] == 'obstacle' else (255, 255, 0)
                            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
                            label = f"{det['class']} ({det['confidence']})"
                            cv2.putText(img, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                        
                        annotated_path = os.path.join(app.config['UPLOAD_FOLDER'], f"annotated_{filename}")
                        cv2.imwrite(annotated_path, img)
                        print(f"✅ Annotated image saved")
                    else:
                        print(f" Too many detections ({len(detections)}), skipping annotation")
                except Exception as img_error:
                    print(f" Image annotation failed: {str(img_error)}")
                    # Continue without annotation
                
                # Create base64 response with comprehensive error handling
                try:
                    if annotated_path and os.path.exists(annotated_path):
                        with open(annotated_path, 'rb') as img_file:
                            img_base64 = base64.b64encode(img_file.read()).decode('utf-8')
                    else:
                        # Fallback to original image
                        with open(filepath, 'rb') as img_file:
                            img_base64 = base64.b64encode(img_file.read()).decode('utf-8')
                    
                    # Validate detections before creating response
                    validated_detections = []
                    for det in detections:
                        try:
                            # Ensure all required fields are present and valid
                            validated_det = {
                                'class': str(det.get('class', 'Unknown')),
                                'confidence': float(det.get('confidence', 0.0)),
                                'bbox': [int(x) for x in det.get('bbox', [0, 0, 0, 0])],
                                'status': str(det.get('status', 'unknown')),
                                'recommendation': str(det.get('recommendation', 'No recommendation available'))
                            }
                            
                            # Add smart recommendations if available
                            if 'smart_recommendations' in det and det['smart_recommendations']:
                                validated_det['smart_recommendations'] = det['smart_recommendations']
                            
                            validated_detections.append(validated_det)
                        except Exception as det_error:
                            print(f"⚠️ Skipping invalid detection: {det_error}")
                            continue
                    
                    # Create response object
                    result = {
                        'success': True,
                        'filename': filename,
                        'detections': validated_detections,
                        'summary': summary,
                        'total_detections': len(validated_detections),
                        'image_data': f'data:image/jpeg;base64,{img_base64}'
                    }
                    
                    # Validate the entire response object
                    try:
                        # Test JSON serialization
                        json_str = json.dumps(result)
                        print(f"✅ Response JSON validation passed ({len(json_str)} chars)")
                        return jsonify(result)
                    except Exception as json_error:
                        print(f"❌ Response JSON validation failed: {json_error}")
                        # Return minimal valid response
                        return jsonify({
                            'success': True,
                            'filename': filename,
                            'detections': [],
                            'summary': ['Error in response formatting'],
                            'total_detections': 0,
                            'image_data': f'data:image/jpeg;base64,{img_base64}'
                        })
                        
                except Exception as response_error:
                    print(f"❌ Response preparation failed: {str(response_error)}")
                    return jsonify({'error': f'Response preparation failed: {str(response_error)}'}), 500
                    
            except Exception as e:
                print(f"❌ Upload processing failed: {str(e)}")
                return jsonify({'error': f'Upload processing failed: {str(e)}'}), 500
        
        print(f"❌ File type not allowed: {file.filename}")
        return jsonify({'error': 'File type not allowed'}), 400
        
    except Exception as e:
        print(f"❌ Critical upload error: {str(e)}")
        return jsonify({'error': f'Critical upload error: {str(e)}'}), 500
@app.route('/api/detection/save', methods=['POST'])
def save_detection():
    """Save detection record from student dashboard"""
    if not is_logged_in():
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    email, session_id = get_current_user()
    
    detection_record = {
        'id': datetime.utcnow().isoformat(),
        'email': email,
        'filename': data.get('filename', 'unknown'),
        'material': data.get('material', 'Unknown'),
        'confidence': data.get('confidence', 0),
        'result': data.get('result', 'Unknown'),
        'status': data.get('status', 'Pending'),
        'timestamp': datetime.utcnow().isoformat(),
        'image_url': data.get('image_url', '')
    }
    
    # Save to detections file
    detections_file = 'data/detections.json'
    try:
        if os.path.exists(detections_file):
            with open(detections_file, 'r') as f:
                detections = json.load(f)
        else:
            detections = []
        detections.insert(0, detection_record)
        with open(detections_file, 'w') as f:
            json.dump(detections, f, indent=4)
    except Exception as e:
        print(f"Error saving detection: {e}")
    
    log_activity(email, session_id, "detection_upload", detection_record)
    return jsonify({'success': True, 'record': detection_record})

@app.route('/api/admin/detections')
def admin_detections():
    """Get all detection records for admin"""
    if not is_logged_in():
        return jsonify({'error': 'Unauthorized'}), 401
    
    detections_file = 'data/detections.json'
    try:
        if os.path.exists(detections_file):
            with open(detections_file, 'r') as f:
                detections = json.load(f)
        else:
            detections = []
    except:
        detections = []
    
    return jsonify({'success': True, 'detections': detections})

@app.route('/api/admin/analytics')
def admin_analytics():
    """Get analytics data for admin dashboard"""
    if not is_logged_in():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Get all data sources
        students = get_all_students()
        sessions = get_all_sessions()
        
        # Get detections
        detections_file = 'data/detections.json'
        detections = []
        if os.path.exists(detections_file):
            with open(detections_file, 'r') as f:
                detections = json.load(f)
        
        # Get upload history
        upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
        total_uploads = 0
        if os.path.exists(upload_dir):
            files = [f for f in os.listdir(upload_dir) if os.path.isfile(os.path.join(upload_dir, f)) and not f.startswith('annotated_')]
            total_uploads = len(files)
        
        # Calculate analytics
        total_students = len(students)
        approved_students = len([s for s in students if s.get('status') == 'approved'])
        pending_students = len([s for s in students if s.get('status') == 'pending'])
        
        total_scans = len(detections)
        usable_count = len([d for d in detections if d.get('result', '').lower() == 'usable'])
        non_usable_count = len([d for d in detections if d.get('result', '').lower() == 'non-usable'])
        
        # Calculate average confidence
        avg_confidence = 0
        if detections:
            confidences = [float(d.get('confidence', 0)) for d in detections if d.get('confidence')]
            if confidences:
                avg_confidence = sum(confidences) / len(confidences)
        
        # Active users (students with recent activity)
        active_students = set()
        recent_threshold = datetime.now().replace(tzinfo=None).timestamp() - (7 * 24 * 3600)  # 7 days
        for session in sessions:
            try:
                login_time = datetime.fromisoformat(session.get('login_time', '').replace('Z', '+00:00')).replace(tzinfo=None).timestamp()
                if login_time > recent_threshold:
                    active_students.add(session.get('email'))
            except:
                continue
        
        # Student-wise scan counts
        student_scans = {}
        for detection in detections:
            email = detection.get('email', 'unknown')
            student_scans[email] = student_scans.get(email, 0) + 1
        
        analytics = {
            'overview': {
                'total_students': total_students,
                'approved_students': approved_students,
                'pending_students': pending_students,
                'total_scans': total_scans,
                'total_uploads': total_uploads,
                'usable_count': usable_count,
                'non_usable_count': non_usable_count,
                'average_confidence': round(avg_confidence, 2),
                'active_students': len(active_students)
            },
            'student_scans': student_scans,
            'recent_activity': sessions[:10] if sessions else []
        }
        
        return jsonify({'success': True, 'analytics': analytics})
        
    except Exception as e:
        print(f"Error in analytics: {e}")
        return jsonify({'success': True, 'analytics': {'overview': {}, 'student_scans': {}, 'recent_activity': []}})

@app.route('/api/admin/student_uploads/<student_email>')
def admin_student_uploads(student_email):
    """Get upload history for a specific student"""
    if not is_logged_in():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Get detections for this student
        detections_file = 'data/detections.json'
        student_detections = []
        if os.path.exists(detections_file):
            with open(detections_file, 'r') as f:
                all_detections = json.load(f)
                student_detections = [d for d in all_detections if d.get('email') == student_email]
        
        # Get upload directory files for this student
        upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
        student_uploads = []
        if os.path.exists(upload_dir):
            files = [f for f in os.listdir(upload_dir) if os.path.isfile(os.path.join(upload_dir, f)) and not f.startswith('annotated_')]
            for filename in files:
                filepath = os.path.join(upload_dir, filename)
                stat = os.stat(filepath)
                mtime = datetime.fromtimestamp(stat.st_mtime)
                
                # Check if this upload belongs to the student (by timestamp matching)
                matching_detection = None
                for detection in student_detections:
                    try:
                        det_time = datetime.fromisoformat(detection.get('timestamp', '').replace('Z', '+00:00')).replace(tzinfo=None)
                        if abs((det_time - mtime).total_seconds()) < 60:  # Within 1 minute
                            matching_detection = detection
                            break
                    except:
                        continue
                
                if matching_detection or len(student_detections) == len(files):  # If we can match or all files belong to this student
                    student_uploads.append({
                        'filename': filename,
                        'url': f"/static/uploads/{filename}",
                        'size': f"{stat.st_size / 1024:.1f} KB",
                        'upload_time': mtime.isoformat(),
                        'material_type': matching_detection.get('material', 'Unknown') if matching_detection else 'Unknown',
                        'confidence': matching_detection.get('confidence', 0) if matching_detection else 0,
                        'result': matching_detection.get('result', 'Unknown') if matching_detection else 'Unknown',
                        'analysis': matching_detection.get('analysis', '') if matching_detection else ''
                    })
        
        return jsonify({'success': True, 'uploads': student_uploads})
        
    except Exception as e:
        print(f"Error getting student uploads: {e}")
        return jsonify({'success': True, 'uploads': []})

@app.route('/api/admin/student_sessions/<student_email>')
def admin_student_sessions(student_email):
    """Get session history for a specific student"""
    if not is_logged_in():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        all_sessions = get_all_sessions()
        student_sessions = [s for s in all_sessions if s.get('email') == student_email]
        
        return jsonify({'success': True, 'sessions': student_sessions})
        
    except Exception as e:
        print(f"Error getting student sessions: {e}")
        return jsonify({'success': True, 'sessions': []})

@app.route('/api/admin/notifications')
def admin_notifications():
    """Get notifications and alerts for admin"""
    if not is_logged_in():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        notifications = []
        
        # Get pending students notifications
        pending_students = get_pending_users()
        for student in pending_students:
            notifications.append({
                'type': 'pending_registration',
                'title': 'New Student Registration',
                'message': f"Student {student['email']} is awaiting approval",
                'timestamp': student.get('created_at', datetime.utcnow().isoformat()),
                'priority': 'medium',
                'action_required': True
            })
        
        # Get recent detections with hazard alerts
        detections_file = 'data/detections.json'
        if os.path.exists(detections_file):
            with open(detections_file, 'r') as f:
                detections = json.load(f)
                
            # Check for recent hazard detections (last 24 hours)
            recent_threshold = datetime.utcnow().timestamp() - (24 * 3600)
            for detection in detections:
                try:
                    det_time = datetime.fromisoformat(detection.get('timestamp', '').replace('Z', '+00:00')).replace(tzinfo=None).timestamp()
                    if det_time > recent_threshold:
                        result = detection.get('result', '').lower()
                        if 'hazard' in result or 'danger' in result or 'obstacle' in result:
                            notifications.append({
                                'type': 'hazard_alert',
                                'title': 'Hazard Detection Alert',
                                'message': f"Student {detection.get('email', 'Unknown')} detected a potential hazard: {detection.get('material', 'Unknown')}",
                                'timestamp': detection.get('timestamp'),
                                'priority': 'high',
                                'action_required': True
                            })
                except:
                    continue
        
        # Sort by timestamp (most recent first)
        notifications.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return jsonify({'success': True, 'notifications': notifications[:20]})  # Limit to 20 most recent
        
    except Exception as e:
        print(f"Error getting notifications: {e}")
        return jsonify({'success': True, 'notifications': []})

@app.route('/health')
def health_check():
    model_status = 'loaded' if model is not None else 'not loaded'
    model_type = 'custom' if model and os.path.exists(MODEL_PATH) else 'pre-trained' if model else 'none'
    ai_status = 'active' if gemini_model is not None else 'inactive'
    return jsonify({
        'status': 'healthy',
        'model': model_status,
        'model_type': model_type,
        'ai_recommendations': ai_status,
        'classes_detected': len(model.names) if model else 0,
        'upload_folder': UPLOAD_FOLDER
    })
if __name__ == '__main__':
    load_model()
    print("=" * 60)
    print("🚀 Smart Vision AI - YOLO Object Detection with AI Recommendations")
    print("=" * 60)
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    if model:
        print(f"✅ YOLO Model loaded: {len(model.names)} classes")
    if gemini_model:
        print(f"✅ Gemini AI active - Smart recommendations enabled")
    else:
        print(f"⚠️ Gemini AI inactive - Using fallback recommendations")
    print(f"🌐 Open http://localhost:5000 in your browser")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)