from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from mysql.connector import Error
import json
import os
import base64
import cv2
import numpy as np
import tensorflow as tf
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input, decode_predictions
from tensorflow.keras.preprocessing.image import img_to_array
import requests
import uuid
import io
from PIL import Image

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a secure key

# MySQL configuration
db_config = {
    'user': 'root',      # Replace with your MySQL username
    'password': 'Hari@3036',  # Replace with your MySQL password
    'host': 'localhost',
    'database': 'dog_breed_db'
}

# Upload folders
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'images', 'Captured_dog_imgs')
app.config['PROFILE_PIC_FOLDER'] = os.path.join('static', 'profile_pics')
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
if not os.path.exists(app.config['PROFILE_PIC_FOLDER']):
    os.makedirs(app.config['PROFILE_PIC_FOLDER'])

# Load model
model = MobileNetV2(weights='imagenet')

def init_db():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        # Create users table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL
            )
        ''')
        # Check and add new columns if they don't exist
        cursor.execute("SHOW COLUMNS FROM users LIKE 'profile_picture'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE users ADD COLUMN profile_picture VARCHAR(255) NULL")
        cursor.execute("SHOW COLUMNS FROM users LIKE 'email'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE users ADD COLUMN email VARCHAR(255) NULL")
        cursor.execute("SHOW COLUMNS FROM users LIKE 'phone_number'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE users ADD COLUMN phone_number VARCHAR(255) NULL")

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS login_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) NOT NULL,
                login_time DATETIME NOT NULL,
                ip_address VARCHAR(255)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                breed_name VARCHAR(255) NOT NULL,
                search_time DATETIME NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS saved_breeds (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                breed_name VARCHAR(255) NOT NULL,
                image_url VARCHAR(255) NULL,
                image_path VARCHAR(255) NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        conn.commit()
        cursor.close()
        conn.close()
    except Error as e:
        print(f"Error initializing database: {e}")

# Helper function to process image from data URL
def process_image(data_url):
    print("Processing image from data URL...")
    # Extract base64 data
    header, encoded = data_url.split(',', 1)
    print("Base64 header:", header)
    img_data = base64.b64decode(encoded)
    print("Decoded image data size:", len(img_data), "bytes")
    
    # Load image with PIL
    img = Image.open(io.BytesIO(img_data))
    
    # Ensure the image is in RGB format (remove alpha channel if present)
    if img.mode == 'RGBA':
        img = img.convert('RGB')
    img = np.array(img)
    print("Image shape after loading:", img.shape)
    
    # Ensure the image has 3 channels (RGB)
    if img.shape[-1] != 3:
        raise ValueError(f"Expected 3 channels (RGB), but got {img.shape[-1]} channels")
    
    # The image should already be 224x224 from client-side resizing
    if img.shape[:2] != (224, 224):
        print("Image dimensions are not 224x224, resizing again...")
        img = cv2.resize(img, (224, 224), interpolation=cv2.INTER_AREA)
    
    # Prepare for MobileNetV2
    img = img_to_array(img)  # Ensures shape (224, 224, 3)
    print("Image shape after img_to_array:", img.shape)
    img = preprocess_input(img)  # Normalizes to [-1, 1] for MobileNetV2
    img = np.expand_dims(img, axis=0)  # Add batch dimension: (1, 224, 224, 3)
    print("Image shape after expand_dims:", img.shape)
    
    # Make prediction
    preds = model.predict(img)
    print("Raw predictions shape:", preds.shape)
    decoded_preds = decode_predictions(preds, top=5)[0]
    print("Top 5 predictions:", [(pred[1], pred[2]) for pred in decoded_preds])
    
    # Filter for dog-related predictions
    dog_prediction = None
    for pred in decoded_preds:
        label = pred[1].lower()
        if 'dog' in label or any(breed.lower() in label for breed in ['retriever', 'shepherd', 'beagle', 'bulldog', 'terrier']):
            dog_prediction = pred
            break
    
    if dog_prediction:
        breed = dog_prediction[1].replace('_', ' ')
        print("Selected dog breed:", breed)
        return breed
    else:
        print("No dog breed identified in top predictions.")
        raise ValueError("Could not identify a dog breed in the image.")

def get_breed_info(breed):
    print("Fetching breed info for:", breed)
    API_KEY = "live_lIstnMtl9oUlFnN1a7G7z4bv1P8FOA40BKO2QBi0biydIzmDitDCsfyhQwbLpUwA"
    url = f"https://api.thedogapi.com/v1/breeds/search?q={breed}"
    headers = {"x-api-key": API_KEY}
    response = requests.get(url, headers=headers)
    if response.status_code == 200 and response.json():
        data = response.json()[0]
        info = {
            "name": data.get("name", "Unknown"),
            "bred_for": data.get("bred_for", "Unknown"),
            "temperament": data.get("temperament", "Unknown"),
            "life_span": data.get("life_span", "Unknown"),
            "origin": data.get("origin", "Unknown"),
            "weight": (data.get("weight", {}).get("metric", "Unknown") + " kg") if data.get("weight") else "Unknown",
            "height": (data.get("height", {}).get("metric", "Unknown") + " cm") if data.get("height") else "Unknown",
            "breed_group": data.get("breed_group", "Unknown"),
            "image_url": f"https://cdn2.thedogapi.com/images/{data.get('reference_image_id', '')}.jpg" if data.get("reference_image_id") else None
        }
        print("Breed info fetched successfully.")
        return info
    else:
        print("Breed info not found.")
        return {"error": "Breed not found"}

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash('Username and password are required.', 'danger')
            return render_template('login.html')
        
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("SELECT id, password FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            
            if user and user[1] == password:
                session['user_id'] = user[0]
                session['username'] = username
                cursor.execute("INSERT INTO login_history (username, login_time, ip_address) VALUES (%s, NOW(), %s)", 
                               (username, request.remote_addr))
                conn.commit()
                cursor.close()
                conn.close()
                flash('Login successful!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Invalid credentials.', 'danger')
                cursor.close()
                conn.close()
        except Error as e:
            flash(f'Database error: {str(e)}', 'danger')
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash('Username and password are required.', 'danger')
            return render_template('register.html')
        
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
            conn.commit()
            cursor.close()
            conn.close()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.errors.IntegrityError:
            flash('Username already exists.', 'danger')
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
        except Error as e:
            flash(f'Database error: {str(e)}', 'danger')
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('user_id', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT username, profile_picture, email, phone_number FROM users WHERE id = %s", (session['user_id'],))
        user = cursor.fetchone()
        cursor.execute("SELECT breed_name, image_url, image_path FROM saved_breeds WHERE user_id = %s", (session['user_id'],))
        saved_breeds = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('profile.html', user=user, saved_breeds=saved_breeds)
    except Error as e:
        flash(f'Database error: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/save_breed', methods=['POST'])
def save_breed():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    breed_name = request.form.get('breed_name')
    image_path = request.form.get('image_path')
    if not breed_name or not image_path:
        flash('Invalid save request.', 'danger')
        return redirect(url_for('index'))
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO saved_breeds (user_id, breed_name, image_path) VALUES (%s, %s, %s)", (session['user_id'], breed_name, image_path))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Breed saved successfully!', 'success')
        return redirect(url_for('profile'))
    except Error as e:
        flash(f'Error saving breed: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/save_breed_from_list', methods=['POST'])
def save_breed_from_list():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    breed_name = request.form.get('breed_name')
    if not breed_name:
        flash('Invalid save request.', 'danger')
        return redirect(url_for('dog_list'))
    # Fetch image_url from TheDogAPI
    breed_info = get_breed_info(breed_name)
    image_url = breed_info.get('image_url')
    if not image_url:
        flash('Could not fetch image for this breed.', 'danger')
        return redirect(url_for('dog_list'))
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO saved_breeds (user_id, breed_name, image_url) VALUES (%s, %s, %s)", (session['user_id'], breed_name, image_url))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Breed saved successfully!', 'success')
        return redirect(url_for('profile'))
    except Error as e:
        flash(f'Error saving breed: {str(e)}', 'danger')
        return redirect(url_for('dog_list'))

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Handle GET request (display the edit profile page)
    if request.method == 'GET':
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT username, email, phone_number, profile_picture FROM users WHERE id = %s", (session['user_id'],))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template('edit_profile.html', user=user)

    # Handle POST requests (form submissions)
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    # Check which form was submitted
    if 'update_profile' in request.form:  # Edit Profile Form
        username = request.form.get('username')
        email = request.form.get('email')
        phone_number = request.form.get('phone_number')
        profile_picture = request.files.get('profile_picture')
        current_password = request.form.get('current_password')

        # Verify current password
        cursor.execute("SELECT password FROM users WHERE id = %s", (session['user_id'],))
        user = cursor.fetchone()
        if not user or user[0] != current_password:
            flash('Current password is incorrect.', 'danger')
            cursor.close()
            conn.close()
            return render_template('edit_profile.html')

        # Update user data
        update_data = []
        if username:
            update_data.append(f"username = '{username}'")
            session['username'] = username  # Update session username
        if email:
            update_data.append(f"email = '{email}'")
        if phone_number:
            update_data.append(f"phone_number = '{phone_number}'")

        if profile_picture:
            # Save profile picture
            filename = f"{session['user_id']}.jpg"
            picture_path = os.path.join(app.config['PROFILE_PIC_FOLDER'], filename)
            os.makedirs(os.path.dirname(picture_path), exist_ok=True)
            profile_picture.save(picture_path)
            update_data.append(f"profile_picture = 'profile_pics/{filename}'")

        if update_data:
            update_str = ', '.join(update_data)
            cursor.execute(f"UPDATE users SET {update_str} WHERE id = %s", (session['user_id'],))
            conn.commit()
            flash('Profile updated successfully!', 'success')
        else:
            flash('No changes made.', 'info')

    elif 'change_password' in request.form:  # Change Password Form
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Verify current password
        cursor.execute("SELECT password FROM users WHERE id = %s", (session['user_id'],))
        user = cursor.fetchone()
        if not user or user[0] != current_password:
            flash('Current password is incorrect.', 'danger')
            cursor.close()
            conn.close()
            return render_template('edit_profile.html')

        # Validate new password
        if not new_password or new_password != confirm_password:
            flash('New password and confirmation do not match or are empty.', 'danger')
            cursor.close()
            conn.close()
            return render_template('edit_profile.html')

        # Update password
        cursor.execute("UPDATE users SET password = %s WHERE id = %s", (new_password, session['user_id'],))
        conn.commit()
        flash('Password changed successfully!', 'success')

    cursor.close()
    conn.close()
    return redirect(url_for('profile'))

@app.route('/search_history')
def search_history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT breed_name, search_time FROM search_history WHERE user_id = %s ORDER BY search_time DESC", 
                       (session['user_id'],))
        history = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('search_history.html', history=history)
    except Error as e:
        flash(f'Database error: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/dog_list')
def dog_list():
    if 'username' not in session:
        return redirect(url_for('login'))
    try:
        with open('static/data/dog_breeds.json', 'r') as f:
            data = json.load(f)
        breeds = data['breeds']
        # Fetch image URLs from TheDogAPI for each breed (only for saving purposes)
        for breed in breeds:
            breed_info = get_breed_info(breed['name'])
            breed['image_url'] = breed_info.get('image_url', None)
        return render_template('dog_list.html', breeds=breeds)
    except FileNotFoundError:
        flash('Dog breeds data not found.', 'danger')
        return redirect(url_for('index'))
    except json.JSONDecodeError:
        flash('Error reading dog breeds data.', 'danger')
        return redirect(url_for('index'))

@app.route('/dog_details/<breed_name>')
def dog_details(breed_name):
    if 'username' not in session:
        return redirect(url_for('login'))
    try:
        with open('static/data/dog_breeds.json', 'r') as f:
            data = json.load(f)
        breed_info = next((breed for breed in data['breeds'] if breed['name'].lower() == breed_name.lower()), None)
        if breed_info:
            # Fetch additional info and image from TheDogAPI
            api_info = get_breed_info(breed_info['name'])
            breed_info['image_url'] = api_info.get('image_url', None)
            try:
                conn = mysql.connector.connect(**db_config)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO search_history (user_id, breed_name, search_time) VALUES (%s, %s, NOW())", 
                               (session['user_id'], breed_info['name']))
                conn.commit()
                cursor.close()
                conn.close()
            except Error as e:
                flash(f'Database error: {str(e)}', 'danger')
            return render_template('dog_details.html', breed=breed_info)
        else:
            flash('Breed not found.', 'danger')
            return redirect(url_for('dog_list'))
    except FileNotFoundError:
        flash('Dog breeds data not found.', 'danger')
        return redirect(url_for('index'))
    except json.JSONDecodeError:
        flash('Error reading dog breeds data.', 'danger')
        return redirect(url_for('index'))

@app.route('/search', methods=['GET'])
def search():
    if 'username' not in session:
        return redirect(url_for('login'))
    breed_name = request.args.get('breed_name')
    if breed_name:
        try:
            with open('static/data/dog_breeds.json', 'r') as f:
                data = json.load(f)
            for breed in data['breeds']:
                if breed['name'].lower() == breed_name.lower():
                    return redirect(url_for('dog_details', breed_name=breed['name']))
            flash('Breed not found.', 'danger')
        except FileNotFoundError:
            flash('Dog breeds data not found.', 'danger')
        except json.JSONDecodeError:
            flash('Error reading dog breeds data.', 'danger')
    return redirect(url_for('index'))

@app.route('/upload', methods=['POST'])
def upload():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    print("Received upload request.")
    image_data = request.form.get('image_data')
    if not image_data:
        print("No image data received.")
        flash('No image data received.', 'danger')
        return redirect(url_for('index'))
    
    try:
        print("Processing image data...")
        # Extract base64 data
        if ',' not in image_data:
            raise ValueError("Invalid image data format: No comma separator found.")
        header, encoded = image_data.split(',', 1)
        print("Base64 header:", header)
        data = base64.b64decode(encoded)
        print("Decoded data size:", len(data), "bytes")
        
        # Validate decoded data
        if not data:
            raise ValueError("Decoded image data is empty.")
        
        # Save the image to captured images
        filename = f"{uuid.uuid4().hex}.jpg"
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        print("Saving image to:", image_path)
        with open(image_path, 'wb') as f:
            f.write(data)
        
        # Verify the file was saved
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file was not saved at {image_path}.")
        print("Image saved successfully.")
        
        # Process the image
        breed = process_image(image_data)
        info = get_breed_info(breed)
        # Additional validation for breed info
        if not info or 'error' in info:
            raise ValueError("Failed to retrieve valid breed information")
        
        print("Rendering result page...")
        return render_template('result.html', breed=breed, info=info, image_filename=filename)
    except ValueError as ve:
        print("ValueError:", str(ve))
        flash(f'Error processing image: {str(ve)}', 'danger')
        return redirect(url_for('index'))
    except FileNotFoundError as fnfe:
        print("FileNotFoundError:", str(fnfe))
        flash(f'Error saving image: {str(fnfe)}', 'danger')
        return redirect(url_for('index'))
    except Exception as e:
        print("Unexpected error:", str(e))
        flash(f'Error processing image: {str(e)}', 'danger')
        return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)