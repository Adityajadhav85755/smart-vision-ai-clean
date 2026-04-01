# from flask import Flask, render_template, request, jsonify, session, redirect, url_for
# import os
# from werkzeug.utils import secure_filename
# import tensorflow as tf
# import numpy as np
# import cv2
# from PIL import Image
# import base64
# from io import BytesIO

# from auth import signup_user, login_user, is_logged_in, get_current_user, logout_user
# from activity_logger import start_session, log_activity, end_session

# app = Flask(__name__)

# # ---------------- CONFIGURATION ----------------
# UPLOAD_FOLDER = 'static/uploads'
# ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
# MODEL_PATH = 'models/material_classifier.h5'
# IMG_SIZE = (224, 224)

# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
# app.secret_key = "super-secret-key-can-change-this"  # ✅ FIXED TYPO

# # ---------------- DIRECTORIES ----------------
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# os.makedirs('models', exist_ok=True)

# # ---------------- MODEL ----------------
# model = None

# def load_model():
#     global model
#     if model is None:
#         try:
#             model = tf.keras.models.load_model(MODEL_PATH)
#             print("Model loaded successfully")
#         except:
#             print("Model not found. Please train the model first.")
#             model = None
#     return model

# # ---------------- HELPERS ----------------
# def allowed_file(filename):
#     return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# def preprocess_image(image_path):
#     img = cv2.imread(image_path)
#     img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
#     img = cv2.resize(img, IMG_SIZE)
#     img = img / 255.0
#     img = np.expand_dims(img, axis=0)
#     return img

# def analyze_image_quality(img_array):
#     img = (img_array[0] * 255).astype(np.uint8)
#     gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

#     edges = cv2.Canny(gray, 50, 150)
#     edge_density = np.sum(edges > 0) / (IMG_SIZE[0] * IMG_SIZE[1])

#     hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
#     lower_rust = np.array([10, 100, 100])
#     upper_rust = np.array([25, 255, 255])
#     rust_mask = cv2.inRange(hsv, lower_rust, upper_rust)
#     rust_ratio = np.sum(rust_mask > 0) / (IMG_SIZE[0] * IMG_SIZE[1])

#     damage_score = edge_density * 0.6 + rust_ratio * 0.4

#     return {
#         'edge_density': float(edge_density),
#         'rust_ratio': float(rust_ratio),
#         'damage_score': float(damage_score)
#     }

# def get_recommendations(prediction, analysis_results):
#     is_usable = prediction >= 0.5

#     if is_usable:
#         confidence = prediction
#         recommendations = [
#             "This material is in good condition and can be reused.",
#             "Suitable for construction and building projects.",
#             "Can be recycled or repurposed for new products.",
#             "Consider selling or donating to reduce waste."
#         ]
#         if analysis_results['damage_score'] > 0.1:
#             recommendations.append("Minor issues detected - consider light repairs before use.")
#     else:
#         confidence = 1 - prediction
#         recommendations = [
#             "This material is damaged and not suitable for reuse.",
#             "Can be recycled at a specialized facility.",
#             "Handle with care - may contain sharp edges or hazardous materials.",
#             "Consider professional disposal services."
#         ]
#         if analysis_results['rust_ratio'] > 0.2:
#             recommendations.append("High rust content - may be hazardous to handle.")
#         if analysis_results['edge_density'] > 0.3:
#             recommendations.append("Multiple cracks detected - handle with extreme care.")

#     return {
#         'status': 'usable' if is_usable else 'non_usable',
#         'confidence': float(confidence),
#         'probability': float(prediction),
#         'recommendations': recommendations,
#         'analysis': analysis_results
#     }

# # ---------------- ROUTES ----------------
# @app.route('/')
# def index():
#     if not is_logged_in():
#         return redirect('/login_page')  # frontend page
#     return render_template('index.html')

# @app.route('/login_page')
# def login_page():
#     return render_template('login.html')

# @app.route('/signup_page')
# def signup_page():
#     return render_template('signup.html')

# # ---------- AUTH ----------
# @app.route('/signup', methods=['POST'])
# def signup():
#     data = request.json
#     success, msg = signup_user(data["email"], data["password"])
#     return jsonify({"success": success, "message": msg})

# @app.route('/login', methods=['POST'])
# def login():
#     data = request.json
#     success, result = login_user(data["email"], data["password"])

#     if not success:
#         return jsonify({"success": False, "message": result}), 401

#     email, session_id = get_current_user()
#     start_session(email, session_id)
#     log_activity(email, session_id, "login")

#     return jsonify({"success": True})

# @app.route('/logout')
# def logout():
#     if is_logged_in():
#         email, session_id = get_current_user()
#         log_activity(email, session_id, "logout")
#         end_session(email, session_id)
#         logout_user()
#     return jsonify({"success": True})

# # ---------- UPLOAD ----------
# @app.route('/upload', methods=['POST'])
# def upload_file():
#     if not is_logged_in():
#         return jsonify({"error": "Login required"}), 401

#     if 'file' not in request.files:
#         return jsonify({'error': 'No file part'}), 400

#     file = request.files['file']
#     if file.filename == '':
#         return jsonify({'error': 'No selected file'}), 400

#     if file and allowed_file(file.filename):
#         filename = secure_filename(file.filename)
#         filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#         file.save(filepath)

#         model = load_model()
#         if model is None:
#             return jsonify({'error': 'Model not available'}), 500

#         img_array = preprocess_image(filepath)
#         prediction = model.predict(img_array, verbose=0)[0][0]
#         analysis_results = analyze_image_quality(img_array)
#         result = get_recommendations(prediction, analysis_results)
#         result['filename'] = filename

#         with open(filepath, 'rb') as img_file:
#             img_base64 = base64.b64encode(img_file.read()).decode('utf-8')
#         result['image_data'] = f'data:image/jpeg;base64,{img_base64}'

#         email, session_id = get_current_user()
#         log_activity(email, session_id, "image_uploaded", filename)
#         log_activity(email, session_id, "prediction_done", result["status"])

#         return jsonify(result)

#     return jsonify({'error': 'File type not allowed'}), 400

# # ---------- TRAIN ----------
# @app.route('/train', methods=['POST'])
# def train_model():
#     if not is_logged_in():
#         return jsonify({"error": "Login required"}), 401

#     email, session_id = get_current_user()
#     log_activity(email, session_id, "model_training_started")

#     try:
#         import subprocess, sys
#         result = subprocess.run([sys.executable, 'train_model.py'],
#                                 capture_output=True, text=True)

#         if result.returncode == 0:
#             return jsonify({'success': True, 'output': result.stdout})
#         else:
#             return jsonify({'success': False, 'error': result.stderr}), 500

#     except Exception as e:
#         return jsonify({'success': False, 'error': str(e)}), 500

# # ---------- HEALTH ----------
# @app.route('/health')
# def health_check():
#     return jsonify({
#         'status': 'healthy',
#         'model': 'loaded' if model else 'not loaded'
#     })

# # ---------------- MAIN ----------------
# if __name__ == '__main__':
#     load_model()
#     app.run(debug=True, host='0.0.0.0', port=5000)
