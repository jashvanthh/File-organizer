# utils/structures.py

import json
from datetime import datetime

class File:
    """
    Represents a file in the file system.
    A file has a name, content, and now includes metadata:
    author, created_date, tags (list), and file_type.
    """
    def __init__(self, name, content="", author="", created_date=None, tags=None, file_type=""):
        self.name = name
        self.content = content
        self.author = author
        # Store creation date as ISO format string for easy serialization
        self.created_date = created_date if created_date else datetime.now().isoformat()
        self.tags = tags if tags is not None else []
        self.file_type = file_type # e.g., 'pdf', 'txt', 'js', 'jpg'

    def to_dict(self):
        """
        Converts the File object to a dictionary for JSON serialization,
        including all metadata.
        """
        return {
            "name": self.name,
            "type": "file",
            "author": self.author,
            "created_date": self.created_date,
            "tags": self.tags,
            "file_type": self.file_type
        }

class HashTable:
    """
    Implements a hash table with linear probing for collision resolution.
    It stores File objects, using their names as keys.
    Supports insert, delete, and search operations.
    Includes rehashing to maintain efficiency as more items are added.
    """
    def __init__(self, capacity=10):
        self.capacity = capacity
        self.table = [None] * capacity  # Stores [key, value] pairs
        self.size = 0  # Current number of items in the hash table
        self.load_factor_threshold = 0.7  # Threshold for triggering rehashing

    def _hash(self, key):
        """
        Simple hash function: sums the ASCII values of characters in the key
        and takes modulo of the capacity.
        """
        return sum(ord(char) for char in key) % self.capacity

    def _probe(self, index, key):
        """
        Linear probing to find the correct position for a key (either an empty slot
        or the slot where the key already exists).
        Returns (probe_index, found_key_index)
        If key is found, found_key_index is the index.
        If key is not found and an empty slot is found, found_key_index is None.
        """
        initial_index = index
        while self.table[index] is not None:
            # If the key is found, return its index
            if self.table[index][0] == key:
                return index, index # Key found at this index
            index = (index + 1) % self.capacity # Move to the next slot
            if index == initial_index:
                # Full circle, table is full and key not found
                return -1, None # Indicates table is full or search failed
        return index, None # Empty slot found, key not in table

    def insert(self, key, value):
        """
        Inserts a key-value pair into the hash table.
        Handles collisions using linear probing.
        Triggers rehashing if the load factor exceeds the threshold.
        Returns True if insertion was successful, False otherwise (e.g., table full).
        """
        # Check if rehashing is needed before insertion
        if (self.size + 1) / self.capacity > self.load_factor_threshold:
            self._rehash()

        index = self._hash(key)
        probe_index, found_key_index = self._probe(index, key)

        if probe_index == -1: # Table is full
            # print(f"Error: Hash table is full, cannot insert {key}") # Debug print
            return False

        if found_key_index is not None:
            # Key already exists, update its value
            self.table[found_key_index][1] = value
            return True
        else:
            # Insert into the found empty slot
            self.table[probe_index] = [key, value]
            self.size += 1
            return True

    def delete(self, key):
        """
        Deletes a key-value pair from the hash table.
        Uses linear probing to find the key.
        Returns the deleted value if successful, None otherwise.
        """
        index = self._hash(key)
        probe_index, found_key_index = self._probe(index, key)

        if found_key_index is not None:
            value = self.table[found_key_index][1]
            self.table[found_key_index] = None # Mark as deleted

            # Rehash affected elements to maintain search efficiency
            # Elements inserted via linear probing might need to be re-inserted
            # if their original hash slot is now empty due to deletion.
            current_idx = (found_key_index + 1) % self.capacity
            while self.table[current_idx] is not None:
                item_key, item_value = self.table[current_idx]
                # Temporarily remove and decrement size for re-insertion
                self.table[current_idx] = None
                self.size -= 1
                # Re-insert the item
                self.insert(item_key, item_value)
                current_idx = (current_idx + 1) % self.capacity
            self.size -= 1 # Decrement size after successful deletion
            return value
        return None # Key not found

    def search(self, key):
        """
        Searches for a key in the hash table.
        Returns the value associated with the key if found, None otherwise.
        """
        index = self._hash(key)
        probe_index, found_key_index = self._probe(index, key)

        if found_key_index is not None:
            return self.table[found_key_index][1]
        return None # Key not found

    def _rehash(self):
        """
        Doubles the capacity of the hash table and rehashes all existing items.
        This is called automatically when the load factor threshold is exceeded.
        """
        old_table = self.table
        self.capacity *= 2
        self.table = [None] * self.capacity
        self.size = 0 # Reset size as items will be re-inserted

        for item in old_table:
            if item is not None:
                key, value = item
                self.insert(key, value)
        # print(f"Hash table rehashed. New capacity: {self.capacity}") # Debug print

    def get_all_files(self):
        """
        Returns a list of all File objects currently in the hash table.
        """
        files = []
        for item in self.table:
            if item is not None:
                files.append(item[1])
        return files

class Folder:
    """
    Represents a folder (directory) in the file system.
    A folder has a name, a reference to its parent folder,
    a dictionary of child folders, and a hash table for its files.
    """
    def __init__(self, name, parent=None):
        self.name = name
        self.parent = parent
        self.children_folders = {}  # Dictionary to store child Folder objects by name
        self.files = HashTable()    # Hash table to store File objects within this folder

    def get_path(self):
        """
        Recursively constructs the full path of the current folder.
        """
        if self.parent is None:
            return f"/{self.name}" # Root folder
        return f"{self.parent.get_path()}/{self.name}"

    def add_folder(self, folder_name):
        """
        Adds a new child folder to this folder.
        Returns the new Folder object if successful, None if a folder with that name already exists.
        """
        if folder_name in self.children_folders:
            return None # Folder already exists
        new_folder = Folder(folder_name, self)
        self.children_folders[folder_name] = new_folder
        return new_folder

    def get_folder_by_name(self, folder_name):
        """
        Retrieves a child folder by name.
        """
        return self.children_folders.get(folder_name)

    def remove_folder_by_name(self, folder_name):
        """
        Removes a child folder by name from the children_folders dictionary.
        Returns the removed Folder object, or None if not found.
        """
        return self.children_folders.pop(folder_name, None)

    def delete_folder(self, folder_name):
        """
        Deletes a child folder from this folder and returns its dictionary
        representation along with its full path for the recycle bin.
        Returns (folder_dict, full_path) if successful, None otherwise.
        """
        folder_to_delete = self.children_folders.get(folder_name)
        if folder_to_delete:
            full_path = folder_to_delete.get_path()
            del self.children_folders[folder_name]
            return folder_to_delete.to_dict(), full_path
        return None, None

    def add_file(self, file_obj):
        """
        Adds a new File object to this folder's hash table.
        Returns the new File object if successful, None if a file with that name already exists.
        """
        if self.files.search(file_obj.name):
            return None # File already exists
        self.files.insert(file_obj.name, file_obj)
        return file_obj

    def get_file_by_name(self, file_name):
        """
        Retrieves a file from this folder's hash table by name.
        """
        return self.files.search(file_name)

    def remove_file_by_name(self, file_name):
        """
        Removes a file from this folder's hash table by name.
        Returns the removed File object, or None if not found.
        """
        return self.files.delete(file_name)

    def delete_file(self, file_name):
        """
        Deletes a file from this folder's hash table and returns its dictionary
        representation along with its full path for the recycle bin.
        Returns (file_dict, full_path) if successful, None otherwise.
        """
        file_to_delete = self.files.delete(file_name)
        if file_to_delete:
            full_path = f"{self.get_path()}/{file_to_delete.name}"
            return file_to_delete.to_dict(), full_path
        return None, None

    def get_sorted_files_by_name(self):
        """
        Retrieves all files from this folder's hash table, sorts them by name,
        and returns the sorted list. This is to support binary search.
        """
        all_files = self.files.get_all_files()
        return sorted(all_files, key=lambda file_obj: file_obj.name)

    def to_dict(self):
        """
        Recursively converts the Folder object and its contents (children folders and files)
        into a dictionary for JSON serialization, suitable for frontend display.
        """
        folder_dict = {
            "name": self.name,
            "type": "folder",
            # Sort children and files for consistent display (optional but good practice)
            "children": sorted([child.to_dict() for child in self.children_folders.values()], key=lambda x: x['name']),
            "files": sorted([file_obj.to_dict() for file_obj in self.files.get_all_files()], key=lambda x: x['name'])
        }
        return folder_dict

class RecycleBin:
    """
    Manages deleted files and folders, allowing for restoration or permanent deletion.
    Stores items as dictionaries along with their original paths.
    """
    def __init__(self):
        self.items = [] # List of {'original_path': path, 'item_data': item_dict}

    def add_item(self, original_path, item_data):
        """Adds a deleted item to the recycle bin."""
        self.items.append({'original_path': original_path, 'item_data': item_data})

    def get_all_items(self):
        """Returns all items in the recycle bin."""
        return self.items

    def get_item(self, index):
        """Retrieves an item by index."""
        if 0 <= index < len(self.items):
            return self.items[index]
        return None

    def remove_item(self, index):
        """Removes an item permanently by index."""
        if 0 <= index < len(self.items):
            return self.items.pop(index)
        return None

# Binary search function (standalone helper function)
def binary_search_files(sorted_files, target_file_name):
    """
    Performs a binary search on a list of sorted File objects by their name.
    Args:
        sorted_files (list[File]): A list of File objects, sorted by name.
        target_file_name (str): The name of the file to search for.
    Returns:
        File: The File object if found, None otherwise.
    """
    low = 0
    high = len(sorted_files) - 1

    while low <= high:
        mid = (low + high) // 2
        mid_file_name = sorted_files[mid].name

        if mid_file_name == target_file_name:
            return sorted_files[mid]
        elif mid_file_name < target_file_name:
            low = mid + 1
        else:
            high = mid - 1
    return None

def traverse_and_collect_all_items(start_folder):
    """
    Recursively traverses the file system tree and collects all files and folders.
    Returns (all_files, all_folders).
    """
    all_files = []
    all_folders = []

    queue = [start_folder]
    while queue:
        current_folder = queue.pop(0)
        all_folders.append(current_folder)

        all_files.extend(current_folder.files.get_all_files())

        for child_folder in current_folder.children_folders.values():
            queue.append(child_folder)
    return all_files, all_folders

