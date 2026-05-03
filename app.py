import os
import sqlite3
from flask import Flask, request, jsonify, render_template, send_from_directory, session, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'super-secret-key'  # In a real app, use a random key
ADMIN_PASSWORD = 'admin123'

DB_PATH = '/home/team/shared/data.db'
UPLOAD_FOLDER = '/home/team/shared/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            return render_template('login.html', error='Invalid password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('admin.html')

@app.route('/api/search')
def search():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    
    conn = get_db_connection()
    # Search by registration_number OR licence_number
    record = conn.execute('SELECT * FROM records WHERE registration_number = ? OR licence_number = ?', (query, query)).fetchone()
    conn.close()
    
    if record:
        return jsonify(dict(record))
    else:
        return jsonify({'error': 'Not found'}), 404

@app.route('/api/records', methods=['GET'])
def get_records():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = get_db_connection()
    records = conn.execute('SELECT * FROM records ORDER BY created_at DESC').fetchall()
    conn.close()
    return jsonify([dict(row) for row in records])

@app.route('/api/records', methods=['POST'])
def add_record():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.form
    file = request.files.get('document')
    filename = None
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO records (registration_number, licence_number, full_name, address, dob, vehicle_categories, endorsements, licence_type, valid_until, document_file_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get('registration_number'),
        data.get('licence_number'),
        data.get('full_name'),
        data.get('address'),
        data.get('dob'),
        data.get('vehicle_categories'),
        data.get('endorsements'),
        data.get('licence_type'),
        data.get('valid_until'),
        filename
    ))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/records/<int:id>', methods=['POST']) # Using POST for updates to handle file uploads easily
def update_record(id):
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.form
    file = request.files.get('document')
    
    conn = get_db_connection()
    record = conn.execute('SELECT * FROM records WHERE id = ?', (id,)).fetchone()
    if not record:
        conn.close()
        return jsonify({'error': 'Record not found'}), 404
    
    filename = record['document_file_path']
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    conn.execute('''
        UPDATE records SET registration_number=?, licence_number=?, full_name=?, address=?, dob=?, vehicle_categories=?, endorsements=?, licence_type=?, valid_until=?, document_file_path=?
        WHERE id=?
    ''', (
        data.get('registration_number'),
        data.get('licence_number'),
        data.get('full_name'),
        data.get('address'),
        data.get('dob'),
        data.get('vehicle_categories'),
        data.get('endorsements'),
        data.get('licence_type'),
        data.get('valid_until'),
        filename,
        id
    ))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/records/<int:id>', methods=['DELETE'])
def delete_record(id):
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = get_db_connection()
    conn.execute('DELETE FROM records WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
