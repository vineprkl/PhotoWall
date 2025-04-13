import os
import uuid
import re # Import re module
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS
from PIL.Image import Resampling
from flask import Flask, request, jsonify, render_template, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

# --- 基本配置 ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER_ORIGINALS = os.path.join(BASE_DIR, 'uploads/originals')
UPLOAD_FOLDER_THUMBNAILS = os.path.join(BASE_DIR, 'uploads/thumbnails')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER_ORIGINALS'] = UPLOAD_FOLDER_ORIGINALS
app.config['UPLOAD_FOLDER_THUMBNAILS'] = UPLOAD_FOLDER_THUMBNAILS

db = SQLAlchemy(app)

# --- 确保上传目录存在 ---
os.makedirs(UPLOAD_FOLDER_ORIGINALS, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_THUMBNAILS, exist_ok=True)


# --- 数据库模型 ---
class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_filename = db.Column(db.String(200), nullable=False)
    stored_filename_original = db.Column(db.String(100), unique=True, nullable=False)
    stored_filename_thumbnail = db.Column(db.String(100), unique=True, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=True) # For display and sorting Cat 1 & 2
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_visible = db.Column(db.Boolean, default=True, nullable=False)
    # New fields for categorization
    category = db.Column(db.String(50), nullable=False, default='游戏截图') # Default category
    sort_key_numeric = db.Column(db.Integer, nullable=True) # For sorting Category 3

    def __repr__(self):
        return f'<Photo {self.original_filename}>'

# --- 辅助函数 ---
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_safe_filename(original_filename):
    extension = original_filename.rsplit('.', 1)[1].lower()
    safe_name = str(uuid.uuid4()) + '.' + extension
    return safe_name

def parse_filename_timestamp(filename):
    """Attempts to parse timestamp from known filename patterns."""
    # Pattern 1: 屏幕截图 YYYY-MM-DD HHMMSS.ext
    match1 = re.search(r'屏幕截图 (\d{4}-\d{2}-\d{2}) (\d{6})\.', filename)
    if match1:
        try:
            dt_str = match1.group(1).replace('-', '') + match1.group(2)
            return datetime.strptime(dt_str, '%Y%m%d%H%M%S')
        except ValueError:
            print(f"Warning: Could not parse timestamp from 屏幕截图 pattern in {filename}")
            pass

    # Pattern 2: *_YYYYMMDD_HHMMSS.* (or similar)
    match2 = re.search(r'(?:[_-]|^)(\d{8})[_]?(\d{6})(?:[\_\-.]|$)', filename)
    if match2:
        try:
            dt_str = match2.group(1) + match2.group(2)
            print(f"Attempting to parse timestamp from filename pattern 2: '{dt_str}' in {filename}") 
            parsed_time = datetime.strptime(dt_str, '%Y%m%d%H%M%S')
            return parsed_time
        except ValueError:
            print(f"Warning: Could not parse timestamp from YYYYMMDD_HHMMSS pattern in {filename}")
            pass

    return None

def get_image_timestamp_exif_mtime(image_path):
    """Gets timestamp from EXIF (DateTimeOriginal > DateTime), falls back to mtime."""
    # 1. Try EXIF
    try:
        img = Image.open(image_path)
        exif_data = img._getexif()
        if exif_data:
            DATETIME_ORIGINAL = 36867
            DATETIME_TAG = 306
            timestamp_str = None
            if DATETIME_ORIGINAL in exif_data:
                timestamp_str = exif_data[DATETIME_ORIGINAL]
            elif DATETIME_TAG in exif_data:
                 timestamp_str = exif_data[DATETIME_TAG]
            if timestamp_str:
                try:
                    return datetime.strptime(timestamp_str, '%Y:%m:%d %H:%M:%S')
                except ValueError:
                    print(f"Warning: Could not parse EXIF timestamp '{timestamp_str}'")
                    pass
    except Exception as e:
        print(f"Error reading EXIF data: {e}")
        pass

    # 2. Fallback to file modification time
    try:
        mtime = os.path.getmtime(image_path)
        return datetime.fromtimestamp(mtime)
    except Exception as e:
        print(f"Error getting file modification time for {image_path}: {e}")
        return None

def create_thumbnail(original_path, thumbnail_path, height=500):
    try:
        img = Image.open(original_path)
        
        # Calculate new width maintaining aspect ratio
        aspect_ratio = img.width / img.height
        new_width = int(height * aspect_ratio)
        
        # Use resize with LANCZOS for high quality downscaling
        # Note: Ensure Pillow version supports Resampling. LANCZOS is generally best.
        # Fallback: Image.LANCZOS or Image.ANTIALIAS for older versions.
        try:
            img_resized = img.resize((new_width, height), Resampling.LANCZOS)
        except AttributeError: # Handle older Pillow versions
            print("Warning: Image.Resampling not found, falling back to Image.LANCZOS/ANTIALIAS")
            try:
                 img_resized = img.resize((new_width, height), Image.LANCZOS)
            except AttributeError:
                 img_resized = img.resize((new_width, height), Image.ANTIALIAS) # Older fallback

        # Save the thumbnail
        save_kwargs = {}
        img_format = img.format # Get original format
        if img_format == 'JPEG':
            save_kwargs['quality'] = 90 # Set higher quality for JPEGs
            # Ensure thumbnail path also has .jpg or .jpeg extension if needed
            # (Our current naming thumb_uuid.ext should handle this)
        
        img_resized.save(thumbnail_path, **save_kwargs)
        return True
    except Exception as e:
        print(f"Error creating thumbnail for {original_path}: {e}")
        return False

# --- 路由 ---

# 主页路由
@app.route('/')
def index():
    return render_template('index.html')

# 管理页面路由 (使用不易猜到的路径)
@app.route('/super-admin-panel')
def admin_panel():
    return render_template('admin.html')

# 提供上传文件的访问
@app.route('/uploads/<path:folder>/<path:filename>')
def uploaded_file(folder, filename):
    if folder == 'originals':
        return send_from_directory(app.config['UPLOAD_FOLDER_ORIGINALS'], filename)
    elif folder == 'thumbnails':
        return send_from_directory(app.config['UPLOAD_FOLDER_THUMBNAILS'], filename)
    else:
        return "Folder not found", 404


# 图片上传路由 (仅限后台)
@app.route('/admin/upload', methods=['POST'])
def upload_photos():
    if 'photos' not in request.files:
        return redirect(request.url) # 或者返回错误信息
        
    files = request.files.getlist('photos')
    
    uploaded_count = 0
    errors = []

    for file in files:
        if file and file.filename != '' and allowed_file(file.filename):
            # Get the raw filename BEFORE securing it
            raw_filename = file.filename 
            # Secure the filename ONLY for storing/display, use raw_filename for logic
            original_filename_for_db = secure_filename(raw_filename)
            
            stored_original_name = generate_safe_filename(original_filename_for_db) # Use secured name base for storage name
            stored_thumbnail_name = 'thumb_' + stored_original_name
            original_path = os.path.join(app.config['UPLOAD_FOLDER_ORIGINALS'], stored_original_name)
            thumbnail_path = os.path.join(app.config['UPLOAD_FOLDER_THUMBNAILS'], stored_thumbnail_name)

            try:
                # 1. Save original file
                file.save(original_path)

                # 2. Determine Category and Sort Key using RAW filename
                category = '游戏' # Default to '游戏' now
                sort_key_numeric = None
                timestamp_from_filename = None
                
                # Check specifically for '活动' based on filename pattern
                if raw_filename.startswith('Sky') and raw_filename.endswith('.png'):
                    match_sky = re.search(r'Sky(\d+)\.png', raw_filename)
                    if match_sky:
                        try:
                            sort_key_numeric = int(match_sky.group(1))
                            category = '活动' 
                        except ValueError:
                            print(f"Warning: Could not parse number from Sky filename {raw_filename}")
                            # Falls back to category = '游戏'
                            
                # Try to parse filename timestamp regardless of category (used if category is '游戏')
                timestamp_from_filename = parse_filename_timestamp(raw_filename)

                # 3. Determine Final Timestamp based on Category
                timestamp_exif_mtime = get_image_timestamp_exif_mtime(original_path)
                final_timestamp = None
                
                if category == '游戏':
                    # Use filename if parsed, otherwise EXIF/mtime
                    final_timestamp = timestamp_from_filename or timestamp_exif_mtime
                elif category == '活动':
                    # Use EXIF/mtime just for display consistency
                    final_timestamp = timestamp_exif_mtime 
                
                if final_timestamp is None:
                     final_timestamp = datetime.utcnow()
                     print(f"Warning: No valid timestamp found for {raw_filename}, using upload time.")

                # 4. Create thumbnail
                if not create_thumbnail(original_path, thumbnail_path):
                     errors.append(f"Failed to create thumbnail for {raw_filename}")
                     os.remove(original_path)
                     continue

                # 5. Save to database using the SECURED filename for display
                new_photo = Photo(
                    original_filename=original_filename_for_db, # Store the secured name
                    stored_filename_original=stored_original_name,
                    stored_filename_thumbnail=stored_thumbnail_name,
                    timestamp=final_timestamp,
                    category=category,
                    sort_key_numeric=sort_key_numeric
                )
                db.session.add(new_photo)
                uploaded_count += 1

            except Exception as e:
                errors.append(f"Error processing {raw_filename}: {e}") # Use raw_filename in error msg
                # 清理可能已创建的文件
                if os.path.exists(original_path):
                    os.remove(original_path)
                if os.path.exists(thumbnail_path):
                    os.remove(thumbnail_path)
        elif file.filename != '':
             errors.append(f"File type not allowed for {file.filename}")

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        errors.append(f"Database commit error: {e}")
        # 可能需要更复杂的错误处理，比如删除本次上传已保存的文件

    # 可以通过 flash 消息传递上传结果给模板，或简单重定向
    print(f"Uploaded: {uploaded_count}, Errors: {len(errors)}") # 在控制台打印日志
    if errors:
        print("Errors:", errors)
        # 可以考虑返回带有错误信息的状态给前端

    return redirect(url_for('admin_panel'))


# API: 获取所有图片信息 (供后台管理使用)
@app.route('/admin/api/images', methods=['GET'])
def get_admin_images():
    photos = Photo.query.order_by(Photo.uploaded_at.desc()).all()
    photo_list = []
    for photo in photos:
        photo_list.append({
            'id': photo.id,
            'original_filename': photo.original_filename,
            'thumbnail_url': url_for('uploaded_file', folder='thumbnails', filename=photo.stored_filename_thumbnail, _external=False),
            'timestamp': photo.timestamp.strftime('%Y-%m-%d %H:%M:%S') if photo.timestamp else '未知时间',
            'uploaded_at': photo.uploaded_at.strftime('%Y-%m-%d %H:%M:%S'),
            'is_visible': photo.is_visible,
            'category': photo.category
        })
    return jsonify(photo_list)

# API: 删除图片
@app.route('/admin/api/images/<int:image_id>/delete', methods=['POST', 'DELETE']) # 允许 POST 或 DELETE 方法
def delete_image(image_id):
    photo = Photo.query.get_or_404(image_id)
    
    original_path = os.path.join(app.config['UPLOAD_FOLDER_ORIGINALS'], photo.stored_filename_original)
    thumbnail_path = os.path.join(app.config['UPLOAD_FOLDER_THUMBNAILS'], photo.stored_filename_thumbnail)

    try:
        db.session.delete(photo)
        db.session.commit()

        # 数据库删除成功后，再删除文件
        if os.path.exists(original_path):
            os.remove(original_path)
        if os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
            
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting image {image_id}: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# API: 切换图片可见性
@app.route('/admin/api/images/<int:image_id>/toggle_visibility', methods=['POST'])
def toggle_visibility(image_id):
    photo = Photo.query.get_or_404(image_id)
    try:
        photo.is_visible = not photo.is_visible
        db.session.commit()
        return jsonify({'success': True, 'is_visible': photo.is_visible})
    except Exception as e:
        db.session.rollback()
        print(f"Error toggling visibility for image {image_id}: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# API: 获取公开可见的图片 (供主页使用)
@app.route('/api/photos', methods=['GET'])
def get_public_photos():
    # Default to '游戏' if no category specified
    category_filter = request.args.get('category', default='游戏') 
    
    query = Photo.query.filter_by(is_visible=True)
    
    # Filter by the specific category
    query = query.filter_by(category=category_filter)
    
    # Apply category-specific sorting
    if category_filter == '游戏':
        query = query.order_by(Photo.timestamp.desc().nullslast(), Photo.uploaded_at.desc())
    elif category_filter == '活动': 
        query = query.order_by(Photo.sort_key_numeric.asc().nullslast(), Photo.uploaded_at.desc())
    # else: # Future categories might just default to upload time or need specific rules
    #    query = query.order_by(Photo.uploaded_at.desc())
        
    photos = query.all()
    
    photo_list = []
    for photo in photos:
        photo_list.append({
            'id': photo.id,
            'original_url': url_for('uploaded_file', folder='originals', filename=photo.stored_filename_original, _external=False),
            'thumbnail_url': url_for('uploaded_file', folder='thumbnails', filename=photo.stored_filename_thumbnail, _external=False),
            'timestamp': photo.timestamp.strftime('%Y-%m-%d %H:%M:%S') if photo.timestamp else '未知时间',
            'category': photo.category
        })
    return jsonify(photo_list)

# --- 添加 Flask CLI 命令 ---
@app.cli.command('init-db')
def init_db_command():
    """Creates the database tables."""
    with app.app_context(): # 确保在应用上下文中执行
        db.create_all()
    print('Initialized the database.')

# --- New CLI Command to Clear Data ---
@app.cli.command('clear-all')
def clear_all_data():
    """Deletes all photo records from the database and all uploaded image files."""
    print("\n*** WARNING! ***")
    print("This command will permanently delete:")
    print("- ALL photo records from the database.")
    print("- ALL files in the 'uploads/originals' directory.")
    print("- ALL files in the 'uploads/thumbnails' directory.")
    print("This action is IRREVERSIBLE. Make sure you have backups if needed.")
    
    confirmation = input('Type "yes" to confirm you want to delete everything: ')
    
    if confirmation.lower() != 'yes':
        print("Confirmation not received. Aborting operation.")
        return

    print("Proceeding with deletion...")
    
    # Delete database records
    try:
        with app.app_context(): # Ensure we are in app context for db operations
            num_rows_deleted = Photo.query.delete()
            db.session.commit()
        print(f"- Deleted {num_rows_deleted} records from the database.")
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting database records: {e}")
        print("Aborting further deletion.")
        return
        
    # Delete files
    deleted_files_count = 0
    errors_deleting_files = []
    
    for folder_path in [app.config['UPLOAD_FOLDER_ORIGINALS'], app.config['UPLOAD_FOLDER_THUMBNAILS']]:
        print(f"Clearing files in {folder_path}...")
        if not os.path.exists(folder_path):
            print(f"  Directory not found: {folder_path}")
            continue
            
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.remove(file_path)
                    deleted_files_count += 1
                # Optionally handle subdirectories if they shouldn't be there
                # elif os.path.isdir(file_path):
                #     print(f"  Warning: Found unexpected subdirectory: {file_path}")
            except Exception as e:
                error_msg = f"Error deleting file {file_path}: {e}"
                print(f"  {error_msg}")
                errors_deleting_files.append(error_msg)
                
    print(f"- Deleted {deleted_files_count} files from upload directories.")
    
    if errors_deleting_files:
        print("\nErrors occurred during file deletion:")
        for err in errors_deleting_files:
            print(f"- {err}")
        print("Database records were deleted, but some files may remain.")
    else:
        print("\nOperation completed successfully.")


if __name__ == '__main__':
    # 在开发环境中使用 Flask 内置服务器
    # 生产环境推荐使用 waitress 或 gunicorn
    # 例如: waitress-serve --host 0.0.0.0 --port 5000 app:app
    app.run(debug=True) # debug=True 便于开发调试 