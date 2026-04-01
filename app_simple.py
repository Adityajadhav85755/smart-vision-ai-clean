from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import os
import sys
from werkzeug.utils import secure_filename
from ultralytics import YOLO
import cv2
import numpy as np
import base64
from auth import signup_user, login_user, is_logged_in, get_current_user, logout_user, get_pending_users, update_user_status, get_all_students, get_all_sessions
from activity_logger import start_session, log_activity, end_session
import json
import re
from datetime import datetime

app = Flask(__name__)

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
        "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://unpkg.com; "
        "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com https://unpkg.com; "
        "font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
        "connect-src 'self'; "
        "img-src 'self' data: https://cdn.pixabay.com; "
        "media-src 'self' https://cdn.pixabay.com; "
        "frame-src 'self' https://www.openstreetmap.org; "
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
    
    summary = []
    if usable_count > 0:
        summary.append(f"🎯 Found {usable_count} usable item(s)")
    if obstacle_count > 0:
        summary.append(f"⚠️ {obstacle_count} obstacle(s)/hazard(s) detected")
    
    summary.append("ℹ️ Using basic recommendations")
    
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
    return render_template('dashboard.html')

@app.route('/admin')
def admin():
    if not is_logged_in():
        return redirect('/login_page')
    return render_template('admin.html')

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
    return jsonify({"success": True})

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        model = load_model()
        if model is None:
            return jsonify({'error': 'Model not available.'}), 500
        
        try:
            results = model(filepath)
            detections, summary = analyze_scene(results)
            
            img = cv2.imread(filepath)
            for det in detections:
                x1, y1, x2, y2 = det['bbox']
                color = (0, 255, 0) if det['status'] == 'usable' else (0, 0, 255) if det['status'] == 'obstacle' else (255, 255, 0)
                cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
                label = f"{det['class']} ({det['confidence']})"
                cv2.putText(img, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            annotated_path = os.path.join(app.config['UPLOAD_FOLDER'], f"annotated_{filename}")
            cv2.imwrite(annotated_path, img)
            
            with open(annotated_path, 'rb') as img_file:
                img_base64 = base64.b64encode(img_file.read()).decode('utf-8')
            
            result = {
                'success': True,
                'filename': filename,
                'detections': detections,
                'summary': summary,
                'total_detections': len(detections),
                'image_data': f'data:image/jpeg;base64,{img_base64}'
            }
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({'error': f'Detection failed: {str(e)}'}), 500
    
    return jsonify({'error': 'File type not allowed'}), 400

@app.route('/health')
def health_check():
    model_status = 'loaded' if model is not None else 'not loaded'
    model_type = 'custom' if model and os.path.exists(MODEL_PATH) else 'pre-trained' if model else 'none'
    
    return jsonify({
        'status': 'healthy',
        'model': model_status,
        'model_type': model_type,
        'ai_recommendations': 'inactive',
        'classes_detected': len(model.names) if model else 0,
        'upload_folder': UPLOAD_FOLDER
    })

if __name__ == '__main__':
    load_model()
    
    print("=" * 60)
    print("🚀 Smart Vision AI - YOLO Object Detection")
    print("=" * 60)
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    if model:
        print(f"✅ YOLO Model loaded: {len(model.names)} classes")
    else:
        print(f"⚠️ Model not loaded")
    print(f"🌐 Open http://localhost:5000 in your browser")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
