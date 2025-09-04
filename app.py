# app.py

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sys
import os
from datetime import datetime

# Add the parent directory of 'utils' to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'utils')))

# Import the custom data structures
from structures import Folder, File, HashTable, binary_search_files, RecycleBin, traverse_and_collect_all_items

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_very_secret_key_here' # IMPORTANT: Change this to a strong, random key in production!

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # This tells Flask-Login where to redirect if a user tries to access a @login_required page without logging in.

# Initialize the root folder of our file system
root_folder = Folder("root")

# Initialize the global recycle bin
recycle_bin = RecycleBin()

# In-memory user storage for demonstration purposes.
# In a real application, this would be a database.
# Format: {'username': {'password_hash': 'hashed_password', 'id': 'user_id'}}\
users = {
    'testuser': {
        'password_hash': generate_password_hash('password123'),
        'id': '1'
    }
}
next_user_id = 2 # Simple ID counter for new registrations

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

    @staticmethod
    def get(user_id):
        """Static method to retrieve a user by ID."""
        for user_data in users.values():
            if user_data['id'] == user_id:
                # Find username by ID
                for username, data in users.items():
                    if data['id'] == user_id:
                        return User(user_data['id'], username, user_data['password_hash'])
        return None

    def get_id(self):
        """Returns the unique ID of the user."""
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    """
    Required by Flask-Login: This function loads a user from the user_id stored in the session.
    """
    # print(f"DEBUG: Attempting to load user with ID: {user_id}")
    user = User.get(user_id)
    if user:
        # print(f"DEBUG: User '{user.username}' loaded successfully.")
        pass
    else:
        # print(f"DEBUG: User with ID '{user_id}' not found.")
        pass
    return user


# --- Helper Functions for File System Navigation and Manipulation ---

def find_folder_by_path(path):
    """
    Traverses the file system tree to find a specific folder by its path.
    Assumes path starts with '/root' or 'root'.
    """
    # Handle both '/root' and 'root' as starting points
    if path.startswith('/root'):
        segments = [s for s in path.split('/') if s]
    elif path == 'root': # Directly accessing root
        segments = ['root']
    else:
        # print(f"DEBUG: Path '{path}' does not start with /root or is not 'root'.")
        return None

    if not segments or segments[0] != 'root':
        # print(f"DEBUG: Invalid path format or not starting with root: {segments}")
        return None

    current_folder = root_folder
    for segment in segments[1:]:
        if segment in current_folder.children_folders:
            current_folder = current_folder.children_folders[segment]
        else:
            # print(f"DEBUG: Segment '{segment}' not found in '{current_folder.name}' children.")
            return None
    # print(f"DEBUG: Found folder for path '{path}': {current_folder.name}")
    return current_folder

def serialize_folder_to_dict(folder):
    """
    Recursively converts a Folder object and its contents into a dictionary
    suitable for JSON serialization and frontend display.
    """
    return folder.to_dict()

# --- Flask Routes ---

@app.route('/')
@login_required # This decorator protects the route. User must be logged in to access.
def index():
    """
    Renders the main index.html page.
    """
    # current_user is available thanks to Flask-Login
    # print(f"DEBUG: User {current_user.username} is authenticated and accessing index.")
    return render_template('index.html', username=current_user.username)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handles user login.
    """
    if current_user.is_authenticated:
        return redirect(url_for('index')) # If already logged in, redirect to index

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # print(f"DEBUG: Login attempt for username: {username}")

        user_data = users.get(username)
        if user_data and check_password_hash(user_data['password_hash'], password):
            user = User(user_data['id'], username, user_data['password_hash'])
            login_user(user)
            # print(f"DEBUG: User '{username}' logged in successfully.")
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next') # Redirect to the page they tried to access before login
            return redirect(next_page or url_for('index'))
        else:
            # print(f"DEBUG: Login failed for username: {username}")
            flash('Invalid username or password.', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Handles user registration.
    """
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    global next_user_id # Declare as global to modify it

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('register.html')

        if username in users:
            flash('Username already exists. Please choose a different one.', 'error')
            return render_template('register.html')

        hashed_password = generate_password_hash(password)
        users[username] = {
            'password_hash': hashed_password,
            'id': str(next_user_id)
        }
        next_user_id += 1
        # print(f"DEBUG: User '{username}' registered successfully with ID: {users[username]['id']}")
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    """
    Handles user logout.
    """
    # print(f"DEBUG: User '{current_user.username}' logging out.")
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/get_file_system', methods=['GET'])
@login_required # Protect this route
def get_file_system():
    """
    API endpoint to retrieve the current state of the file system.
    """
    try:
        file_system_data = serialize_folder_to_dict(root_folder)
        return jsonify(success=True, file_system=file_system_data)
    except Exception as e:
        print(f"Error getting file system: {e}")
        return jsonify(success=False, message=str(e)), 500

@app.route('/create_folder', methods=['POST'])
@login_required # Protect this route
def create_folder():
    """
    API endpoint to create a new folder.
    """
    data = request.get_json()
    folder_name = data.get('folder_name')
    parent_path = data.get('parent_path')

    if not folder_name:
        return jsonify(success=False, message="Folder name is required."), 400
    if not parent_path:
        return jsonify(success=False, message="Parent path is required."), 400

    parent_folder = find_folder_by_path(parent_path)
    if not parent_folder:
        return jsonify(success=False, message=f"Parent folder not found at path: {parent_path}"), 404

    try:
        new_folder = parent_folder.add_folder(folder_name)
        if new_folder:
            return jsonify(success=True, message=f"Folder '{folder_name}' created."), 201
        else:
            return jsonify(success=False, message=f"Folder '{folder_name}' already exists in '{parent_path}'."), 409
    except Exception as e:
        print(f"Error creating folder: {e}")
        return jsonify(success=False, message=f"An error occurred: {str(e)}"), 500

@app.route('/delete_folder', methods=['POST'])
@login_required # Protect this route
def delete_folder():
    """
    API endpoint to delete a folder and move it to the recycle bin.
    """
    data = request.get_json()
    folder_name = data.get('folder_name')
    parent_path = data.get('parent_path')

    # print(f"Backend: Received delete folder request for folder_name='{folder_name}', parent_path='{parent_path}'")

    if not folder_name:
        return jsonify(success=False, message="Folder name is required."), 400
    if not parent_path:
        return jsonify(success=False, message="Parent path is required."), 400

    # Prevent deleting the root folder itself
    if folder_name == 'root' and (parent_path == '/root' or parent_path == 'root'):
        return jsonify(success=False, message="Cannot delete the root folder."), 403

    parent_folder = find_folder_by_path(parent_path)
    if not parent_folder:
        # print(f"Backend: Parent folder not found for path: {parent_path}")
        return jsonify(success=False, message=f"Parent folder not found at path: {parent_path}"), 404

    try:
        # print(f"Backend: Attempting to delete folder '{folder_name}' from parent '{parent_folder.name}'")
        deleted_item_data, original_path = parent_folder.delete_folder(folder_name)
        if deleted_item_data:
            recycle_bin.add_item(original_path, deleted_item_data)
            # print(f"Backend: Folder '{folder_name}' moved to Recycle Bin.")
            return jsonify(success=True, message=f"Folder '{folder_name}' moved to Recycle Bin."), 200
        else:
            # print(f"Backend: Folder '{folder_name}' not found in '{parent_path}' for deletion.")
            return jsonify(success=False, message=f"Folder '{folder_name}' not found in '{parent_path}'."), 404
    except Exception as e:
        print(f"Backend: Error deleting folder: {e}")
        return jsonify(success=False, message=f"An error occurred: {str(e)}"), 500

@app.route('/add_file', methods=['POST'])
@login_required # Protect this route
def add_file():
    """
    API endpoint to add a new file to a folder, including metadata.
    """
    data = request.get_json()
    file_name = data.get('file_name')
    parent_path = data.get('parent_path')
    author = data.get('author', '')
    tags_str = data.get('tags', '')
    tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()] # Split by comma and clean
    file_type = data.get('file_type', '').lower() # Convert to lowercase for consistency

    if not file_name:
        return jsonify(success=False, message="File name is required."), 400
    if not parent_path:
        return jsonify(success=False, message="Parent path is required."), 400

    parent_folder = find_folder_by_path(parent_path)
    if not parent_folder:
        return jsonify(success=False, message=f"Parent folder not found at path: {parent_path}"), 404

    try:
        new_file_obj = File(file_name, "", author, None, tags, file_type) # Content is placeholder for now
        added_file = parent_folder.add_file(new_file_obj)
        if added_file:
            return jsonify(success=True, message=f"File '{file_name}' added."), 201
        else:
            return jsonify(success=False, message=f"File '{file_name}' already exists in '{parent_path}'."), 409
    except Exception as e:
        print(f"Error adding file: {e}")
        return jsonify(success=False, message=f"An error occurred: {str(e)}"), 500

@app.route('/delete_file', methods=['POST'])
@login_required # Protect this route
def delete_file():
    """
    API endpoint to delete a file from a folder and move it to the recycle bin.
    """
    data = request.get_json()
    file_name = data.get('file_name')
    parent_path = data.get('parent_path')

    # print(f"Backend: Received delete file request for file_name='{file_name}', parent_path='{parent_path}'")

    if not file_name:
        return jsonify(success=False, message="File name is required."), 400
    if not parent_path:
        return jsonify(success=False, message="Parent path is required."), 400

    parent_folder = find_folder_by_path(parent_path)
    if not parent_folder:
        # print(f"Backend: Parent folder not found for path: {parent_path}")
        return jsonify(success=False, message=f"Parent folder not found at path: {parent_path}"), 404

    try:
        # print(f"Backend: Attempting to delete file '{file_name}' from parent '{parent_folder.name}'")
        deleted_item_data, original_path = parent_folder.delete_file(file_name)
        if deleted_item_data:
            recycle_bin.add_item(original_path, deleted_item_data)
            # print(f"Backend: File '{file_name}' moved to Recycle Bin.")
            return jsonify(success=True, message=f"File '{file_name}' moved to Recycle Bin."), 200
        else:
            # print(f"Backend: File '{file_name}' not found in '{parent_path}' for deletion.")
            return jsonify(success=False, message=f"File '{file_name}' not found in '{parent_path}'."), 404
    except Exception as e:
        print(f"Backend: Error deleting file: {e}")
        return jsonify(success=False, message=f"An error occurred: {str(e)}"), 500

@app.route('/search_file', methods=['POST'])
@login_required # Protect this route
def search_file():
    """
    API endpoint to search for a file within a specific folder using binary search.
    This is for name-only search within a specified folder.
    """
    data = request.get_json()
    file_name = data.get('file_name')
    parent_path = data.get('parent_path')

    if not file_name:
        return jsonify(success=False, message="File name is required for search."), 400
    if not parent_path:
        return jsonify(success=False, message="Parent path is required for search scope."), 400

    parent_folder = find_folder_by_path(parent_path)
    if not parent_folder:
        return jsonify(success=False, message=f"Folder not found at path: {parent_path}"), 404

    try:
        sorted_files = parent_folder.get_sorted_files_by_name()
        found_file = binary_search_files(sorted_files, file_name)

        if found_file:
            return jsonify(success=True, message=f"File '{file_name}' found.", found_in_path=parent_path), 200
        else:
            return jsonify(success=False, message=f"File '{file_name}' not found in '{parent_path}'."), 404
    except Exception as e:
        print(f"Error searching file: {e}")
        return jsonify(success=False, message=f"An error occurred: {str(e)}"), 500

@app.route('/search_by_metadata', methods=['POST'])
@login_required
def search_by_metadata():
    """
    API endpoint to search for files based on various metadata fields across the entire file system.
    """
    data = request.get_json()
    search_name = data.get('name', '').lower()
    search_author = data.get('author', '').lower()
    search_tags_str = data.get('tags', '')
    search_tags = [tag.strip().lower() for tag in search_tags_str.split(',') if tag.strip()]
    search_file_type = data.get('file_type', '').lower()

    found_files = []
    # Use the helper to get all files from the root
    all_files_in_system, _ = traverse_and_collect_all_items(root_folder)

    for file_obj in all_files_in_system:
        match = True

        if search_name and search_name not in file_obj.name.lower():
            match = False
        if search_author and search_author not in file_obj.author.lower():
            match = False
        if search_file_type and search_file_type != file_obj.file_type.lower():
            match = False
        if search_tags:
            # Check if all search tags are present in file_obj.tags
            file_obj_tags_lower = [t.lower() for t in file_obj.tags]
            if not all(tag in file_obj_tags_lower for tag in search_tags):
                match = False

        if match:
            # To get the full path for the frontend display
            # This is inefficient for large systems but works for demonstration
            # A reverse mapping or storing path in File object would be better.
            full_path = "Unknown Path"
            # Iteratively find the parent to construct full path
            queue = [root_folder]
            while queue:
                current_f = queue.pop(0)
                if current_f.get_file_by_name(file_obj.name) == file_obj:
                    full_path = f"{current_f.get_path()}/{file_obj.name}"
                    break
                for child_f in current_f.children_folders.values():
                    queue.append(child_f)

            file_data = file_obj.to_dict()
            file_data['full_path'] = full_path # Add full path for display
            found_files.append(file_data)

    return jsonify(success=True, results=found_files), 200

# --- Recycle Bin Endpoints ---

@app.route('/get_recycle_bin_items', methods=['GET'])
@login_required
def get_recycle_bin_items():
    """API endpoint to retrieve contents of the recycle bin."""
    try:
        items = recycle_bin.get_all_items()
        return jsonify(success=True, items=items), 200
    except Exception as e:
        print(f"Error getting recycle bin items: {e}")
        return jsonify(success=False, message=str(e)), 500

@app.route('/restore_from_recycle_bin', methods=['POST'])
@login_required
def restore_from_recycle_bin():
    """API endpoint to restore an item from the recycle bin."""
    data = request.get_json()
    item_index = data.get('item_index')

    if item_index is None:
        return jsonify(success=False, message="Item index is required."), 400

    try:
        item = recycle_bin.get_item(item_index)
        if not item:
            return jsonify(success=False, message="Item not found in recycle bin."), 404

        original_path = item['original_path']
        item_data = item['item_data']
        item_type = item_data['type']
        item_name = item_data['name']

        # Determine the parent path for restoration
        path_parts = original_path.split('/')
        if len(path_parts) > 2: # e.g., /root/folder/file.txt -> parent is /root/folder
            parent_path = '/'.join(path_parts[:-1])
        elif len(path_parts) == 2 and path_parts[1] == 'root': # special case for /root itself, should not happen for items within it.
            parent_path = 'root' # Restoring directly into root is handled by finding root_folder
            if item_name == 'root': # Cannot restore root into itself
                return jsonify(success=False, message="Cannot restore the original root folder as a child."), 400
        elif len(path_parts) == 2: # e.g., /root/file.txt -> parent is /root
             parent_path = '/root'
        else:
             return jsonify(success=False, message="Invalid original path for restoration."), 400

        parent_folder = find_folder_by_path(parent_path)

        if not parent_folder:
            return jsonify(success=False, message=f"Original parent folder '{parent_path}' not found. Cannot restore."), 404

        # Check if an item with the same name already exists in the target location
        if item_type == 'file' and parent_folder.get_file_by_name(item_name):
            return jsonify(success=False, message=f"A file named '{item_name}' already exists in '{parent_path}'. Please rename existing file or restore manually."), 409
        elif item_type == 'folder' and parent_folder.get_folder_by_name(item_name):
            return jsonify(success=False, message=f"A folder named '{item_name}' already exists in '{parent_path}'. Please rename existing folder or restore manually."), 409


        # Perform restoration based on item type
        if item_type == 'file':
            restored_file = File(
                item_data['name'],
                item_data.get('content', ''),
                item_data.get('author', ''),
                item_data.get('created_date'),
                item_data.get('tags', []),
                item_data.get('file_type', '')
            )
            parent_folder.add_file(restored_file)
        elif item_type == 'folder':
            # Recursive function to restore folders and their contents
            def restore_folder_recursive(target_parent_folder, folder_data):
                new_folder = target_parent_folder.add_folder(folder_data['name'])
                if not new_folder: # Should not happen if existence check passed above
                    return None
                for file_in_folder_data in folder_data['files']:
                    new_file = File(
                        file_in_folder_data['name'],
                        file_in_folder_data.get('content', ''),
                        file_in_folder_data.get('author', ''),
                        file_in_folder_data.get('created_date'),
                        file_in_folder_data.get('tags', []),
                        file_in_folder_data.get('file_type', '')
                    )
                    new_folder.add_file(new_file)
                for child_folder_data in folder_data['children']:
                    restore_folder_recursive(new_folder, child_folder_data)
                return new_folder

            restore_folder_recursive(parent_folder, item_data)

        # Remove from recycle bin after successful restoration
        recycle_bin.remove_item(item_index)
        return jsonify(success=True, message=f"'{item_name}' restored to '{parent_path}'."), 200

    except Exception as e:
        print(f"Error restoring item: {e}")
        return jsonify(success=False, message=f"An error occurred during restoration: {str(e)}"), 500

@app.route('/permanent_delete_item', methods=['POST'])
@login_required
def permanent_delete_item():
    """API endpoint to permanently delete an item from the recycle bin."""
    data = request.get_json()
    item_index = data.get('item_index')

    if item_index is None:
        return jsonify(success=False, message="Item index is required."), 400

    try:
        deleted_item = recycle_bin.remove_item(item_index)
        if deleted_item:
            item_name = deleted_item['item_data']['name']
            return jsonify(success=True, message=f"'{item_name}' permanently deleted."), 200
        else:
            return jsonify(success=False, message="Item not found in recycle bin for permanent deletion."), 404
    except Exception as e:
        print(f"Error permanently deleting item: {e}")
        return jsonify(success=False, message=f"An error occurred: {str(e)}"), 500

@app.route('/empty_recycle_bin', methods=['POST'])
@login_required
def empty_recycle_bin():
    """API endpoint to empty the entire recycle bin."""
    try:
        recycle_bin.items = [] # Clear all items
        return jsonify(success=True, message="Recycle Bin emptied successfully."), 200
    except Exception as e:
        print(f"Error emptying recycle bin: {e}")
        return jsonify(success=False, message=f"An error occurred: {str(e)}"), 500


if __name__ == '__main__':
    app.run(debug=True)

