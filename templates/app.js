// File Organizer JavaScript - Complete Implementation

// Store the current file system structure globally for easy access
let fileSystemData = {};
let recycleBinItems = []; // To store fetched recycle bin items
let selectedRecycleBinItemIndex = -1; // To track selected item in recycle bin modal

// Define Flask endpoint URLs using window.location.origin for robustness
const baseUrl = window.location.origin;
const getFileSystemUrl = `${baseUrl}/get_file_system`;
const createFolderUrl = `${baseUrl}/create_folder`;
const deleteFolderUrl = `${baseUrl}/delete_folder`;
const addFileUrl = `${baseUrl}/add_file`;
const deleteFileUrl = `${baseUrl}/delete_file`;
// const searchFileUrl = `${baseUrl}/search_file`; // Old name-only search, replaced by metadata search
const searchByMetadataUrl = `${baseUrl}/search_by_metadata`; // New metadata search

// Recycle Bin URLs
const getRecycleBinItemsUrl = `${baseUrl}/get_recycle_bin_items`;
const restoreFromRecycleBinUrl = `${baseUrl}/restore_from_recycle_bin`;
const permanentDeleteItemUrl = `${baseUrl}/permanent_delete_item`;
const emptyRecycleBinUrl = `${baseUrl}/empty_recycle_bin`;


/**
 * Displays a message to the user in the message box.
 * @param {string} message - The message text.
 * @param {string} type - 'success', 'error', or 'info' to determine styling.
 */
function showMessage(message, type) {
    const messageBox = document.getElementById('messageBox');
    const messageIcon = document.getElementById('messageIcon');
    const messageText = document.getElementById('messageText');

    // Remove any existing type classes
    messageBox.className = 'message-box show';
    // Add the new type class
    messageBox.classList.add(type);
    messageText.textContent = message;

    // Using Font Awesome icons
    if (type === 'success') {
        messageIcon.innerHTML = '<i class="fas fa-check-circle"></i>';
    } else if (type === 'error') {
        messageIcon.innerHTML = '<i class="fas fa-times-circle"></i>';
    } else if (type === 'info') {
        messageIcon.innerHTML = '<i class="fas fa-info-circle"></i>';
    }

    // Hide message after 5 seconds
    setTimeout(() => {
        messageBox.classList.remove('show');
    }, 5000);
}

/**
 * Shows a custom confirmation modal.
 * @param {string} message - The message to display in the modal.
 * @returns {Promise<boolean>} - Resolves to true if confirmed, false if cancelled.
 */
function showConfirmation(message) {
    return new Promise((resolve) => {
        const modal = document.getElementById('confirmationModal');
        const modalMessage = document.getElementById('modalMessage');
        const modalConfirm = document.getElementById('modalConfirm');
        const modalCancel = document.getElementById('modalCancel');

        modalMessage.textContent = message;
        modal.style.display = 'flex'; // Show the modal

        // Clear previous listeners to prevent multiple triggers if modal is re-used quickly
        const confirmClone = modalConfirm.cloneNode(true);
        const cancelClone = modalCancel.cloneNode(true);
        modalConfirm.parentNode.replaceChild(confirmClone, modalConfirm);
        modalCancel.parentNode.replaceChild(cancelClone, modalCancel);

        confirmClone.addEventListener('click', () => {
            modal.style.display = 'none';
            resolve(true);
        }, { once: true }); // Use once: true to auto-remove listener after first click

        cancelClone.addEventListener('click', () => {
            modal.style.display = 'none';
            resolve(false);
        }, { once: true });
    });
}


/**
 * Fetches the current file system structure from the backend and updates the UI.
 */
async function fetchFileSystem() {
    try {
        const response = await fetch(getFileSystemUrl);
        const data = await response.json();
        if (data.success) {
            fileSystemData = data.file_system;
            // Start at level 0 for root
            const fullFileSystemHtml = renderFileSystemRecursive(fileSystemData, 0);
            // Update the display area only once at the top level
            document.getElementById('fileSystemDisplay').innerHTML = fullFileSystemHtml;
            populateFolderDropdowns(fileSystemData);
            hideSearchResults(); // Hide search results when file system is reloaded
        } else {
            showMessage('Failed to load file system: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('Error fetching file system:', error);
        showMessage('An error occurred while loading the file system.', 'error');
    }
}

/**
 * Recursively renders the file system structure as an HTML string.
 * @param {object} node - The current folder/file node to render.
 * @param {number} level - The current indentation level.
 * @returns {string} HTML string representing the file system structure.
 */
function renderFileSystemRecursive(node, level) {
    let html = '';
    let iconClass = node.type === 'folder' ? 'fa-folder' : 'fa-file';
    // Add specific icons for file types if available in Font Awesome or custom
    if (node.type === 'file') {
        const fileType = node.file_type ? node.file_type.toLowerCase() : '';
        switch (fileType) {
            case 'pdf': iconClass = 'fa-file-pdf'; break;
            case 'doc':
            case 'docx': iconClass = 'fa-file-word'; break;
            case 'xls':
            case 'xlsx': iconClass = 'fa-file-excel'; break;
            case 'ppt':
            case 'pptx': iconClass = 'fa-file-powerpoint'; break;
            case 'jpg':
            case 'jpeg':
            case 'png':
            case 'gif': iconClass = 'fa-file-image'; break;
            case 'zip': iconClass = 'fa-file-archive'; break;
            case 'js':
            case 'py':
            case 'html':
            case 'css': iconClass = 'fa-file-code'; break;
            case 'txt': iconClass = 'fa-file-alt'; break;
            default: iconClass = 'fa-file'; break;
        }
    }
    const nodeTypeClass = node.type === 'folder' ? 'tree-folder' : 'tree-file';

    // Render the current node (folder or file)
    html += `<div class="tree-node ${nodeTypeClass}" style="margin-left: ${level * 20}px;">`;
    html += `<i class="fas ${iconClass} icon"></i> ${node.name}`;
    if (node.type === 'file' && (node.author || (node.tags && node.tags.length > 0) || node.file_type)) {
        html += ` <span class="metadata-info">(`;
        const metadataParts = [];
        if (node.author) metadataParts.push(`Author: ${node.author}`);
        if (node.file_type) metadataParts.push(`Type: ${node.file_type}`);
        if (node.tags && node.tags.length > 0) metadataParts.push(`Tags: ${node.tags.join(', ')}`);
        html += metadataParts.join(', ');
        html += `)</span>`;
    }
    html += `</div>`; // Close the current node's div

    // If it's a folder, render its children (files and subfolders)
    if (node.type === 'folder') {
        // Render files first, indented relative to the folder
        if (node.files && node.files.length > 0) {
            node.files.forEach(file => {
                html += renderFileSystemRecursive(file, level + 1); // Files are one level deeper
            });
        }

        // Render child folders, recursively
        if (node.children && node.children.length > 0) {
            node.children.forEach(child => {
                html += renderFileSystemRecursive(child, level + 1); // Subfolders are one level deeper
            });
        }
    }
    return html;
}


/**
 * Populates the folder dropdowns for folder and file operations.
 * @param {object} node - The current folder node to traverse.
 * @param {string} currentPath - The path leading to the current node.
 */
function populateFolderDropdowns(node, currentPath = '') {
    const folderSelect = document.getElementById('currentFolderSelect');
    const fileFolderSelect = document.getElementById('currentFolderSelectFile');

    // Clear existing options only when starting from the root of the recursion
    if (currentPath === '') {
        folderSelect.innerHTML = '';
        fileFolderSelect.innerHTML = '';
    }

    let fullPath;
    if (node.name === 'root' && currentPath === '') {
        fullPath = '/root'; // Explicitly set the value for the initial root folder
    } else {
        fullPath = currentPath + node.name;
    }

    const option = document.createElement('option');
    option.value = fullPath;
    option.textContent = fullPath;

    // Clone the option for the second dropdown to avoid DOM re-parenting issues
    const optionClone = option.cloneNode(true);

    folderSelect.appendChild(option);
    fileFolderSelect.appendChild(optionClone);

    // Recursively add children folders
    node.children.forEach(child => {
        if (child.type === 'folder') {
            populateFolderDropdowns(child, fullPath + '/');
        }
    });
}

/**
 * Handles the creation of a new folder.
 */
async function createFolder() {
    const folderName = document.getElementById('folderName').value.trim();
    const parentPath = document.getElementById('currentFolderSelect').value;

    if (!folderName) {
        showMessage('Folder name cannot be empty.', 'error');
        return;
    }

    try {
        const response = await fetch(createFolderUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ folder_name: folderName, parent_path: parentPath })
        });
        const data = await response.json();
        if (data.success) {
            showMessage(`Folder '${folderName}' created successfully in '${parentPath}'.`, 'success');
            document.getElementById('folderName').value = ''; // Clear input
            fetchFileSystem(); // Refresh the display
        } else {
            showMessage('Error creating folder: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('Error creating folder:', error);
        showMessage('An error occurred while creating the folder.', 'error');
    }
}

/**
 * Handles the deletion of a folder.
 */
async function deleteFolder() {
    const folderName = document.getElementById('folderName').value.trim(); // Using same input for simplicity
    const parentPath = document.getElementById('currentFolderSelect').value;

    if (!folderName) {
        showMessage('Folder name cannot be empty.', 'error');
        return;
    }

    if (folderName === 'root' && (parentPath === '/root' || parentPath === 'root')) {
        showMessage('Cannot delete the root folder.', 'error');
        return;
    }

    const confirmed = await showConfirmation(`Deleting folder '${folderName}' from '${parentPath}' will move it and its contents to the Recycle Bin.`);
    if (!confirmed) {
        showMessage('Folder deletion cancelled.', 'info');
        return;
    }

    try {
        const response = await fetch(deleteFolderUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ folder_name: folderName, parent_path: parentPath })
        });
        const data = await response.json();
        if (data.success) {
            showMessage(`Folder '${folderName}' moved to Recycle Bin from '${parentPath}'.`, 'success');
            document.getElementById('folderName').value = ''; // Clear input
            fetchFileSystem(); // Refresh the display
        } else {
            showMessage('Error deleting folder: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('Error deleting folder:', error);
        showMessage('An error occurred while deleting the folder.', 'error');
    }
}

/**
 * Handles adding a new file, including metadata.
 */
async function addFile() {
    const fileName = document.getElementById('fileName').value.trim();
    const parentPath = document.getElementById('currentFolderSelectFile').value;
    const author = document.getElementById('fileAuthor').value.trim();
    const tags = document.getElementById('fileTags').value.trim();
    const fileType = document.getElementById('fileType').value.trim();

    if (!fileName) {
        showMessage('File name cannot be empty.', 'error');
        return;
    }

    try {
        const response = await fetch(addFileUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                file_name: fileName,
                parent_path: parentPath,
                author: author,
                tags: tags, // Send as comma-separated string
                file_type: fileType
            })
        });
        const data = await response.json();
        if (data.success) {
            showMessage(`File '${fileName}' added successfully to '${parentPath}'.`, 'success');
            // Clear file inputs after successful add
            document.getElementById('fileName').value = '';
            document.getElementById('fileAuthor').value = '';
            document.getElementById('fileTags').value = '';
            document.getElementById('fileType').value = '';
            fetchFileSystem(); // Refresh the display
        } else {
            showMessage('Error adding file: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('Error adding file:', error);
        showMessage('An error occurred while adding the file.', 'error');
    }
}

/**
 * Handles deleting a file and moving it to the recycle bin.
 */
async function deleteFile() {
    const fileName = document.getElementById('fileName').value.trim(); // Re-using input for simplicity
    const parentPath = document.getElementById('currentFolderSelectFile').value;

    if (!fileName) {
        showMessage('File name cannot be empty.', 'error');
        return;
    }

    const confirmed = await showConfirmation(`Are you sure you want to delete file '${fileName}' from '${parentPath}'? It will be moved to the Recycle Bin.`);
    if (!confirmed) {
        showMessage('File deletion cancelled.', 'info');
        return;
    }

    try {
        const response = await fetch(deleteFileUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ file_name: fileName, parent_path: parentPath })
        });
        const data = await response.json();
        if (data.success) {
            showMessage(`File '${fileName}' moved to Recycle Bin from '${parentPath}'.`, 'success');
            fetchFileSystem(); // Refresh the display
        } else {
            showMessage('Error deleting file: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('Error deleting file:', error);
        showMessage('An error occurred while deleting the file.', 'error');
    }
}

/**
 * Handles searching for files by metadata (or name).
 */
async function searchByMetadata() {
    const searchName = document.getElementById('searchFileName').value.trim();
    const searchAuthor = document.getElementById('fileAuthor').value.trim();
    const searchTags = document.getElementById('fileTags').value.trim();
    const searchFileType = document.getElementById('fileType').value.trim();

    if (!searchName && !searchAuthor && !searchTags && !searchFileType) {
        showMessage('Please enter at least one search criterion (name, author, tags, or file type).', 'info');
        return;
    }

    try {
        const response = await fetch(searchByMetadataUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: searchName,
                author: searchAuthor,
                tags: searchTags,
                file_type: searchFileType
            })
        });
        const data = await response.json();
        const searchResultsList = document.getElementById('searchResultsList');
        searchResultsList.innerHTML = ''; // Clear previous results

        if (data.success && data.results.length > 0) {
            data.results.forEach(item => {
                const li = document.createElement('li');
                let metadataDisplay = [];
                if (item.author) metadataDisplay.push(`Author: ${item.author}`);
                if (item.file_type) metadataDisplay.push(`Type: ${item.file_type}`);
                if (item.tags && item.tags.length > 0) metadataDisplay.push(`Tags: ${item.tags.join(', ')}`);

                li.textContent = `${item.name} (${item.type}) - Path: ${item.full_path || 'Not Available'}`;
                if (metadataDisplay.length > 0) {
                    li.textContent += ` (${metadataDisplay.join(', ')})`;
                }
                searchResultsList.appendChild(li);
            });
            document.getElementById('searchResultsDisplay').style.display = 'block';
            document.getElementById('fileSystemDisplay').style.display = 'none'; // Hide file system
            showMessage(`Found ${data.results.length} matching items.`, 'success');
        } else {
            showMessage('No items found matching your search criteria.', 'info');
            document.getElementById('searchResultsDisplay').style.display = 'none';
            document.getElementById('fileSystemDisplay').style.display = 'block'; // Show file system
        }
    } catch (error) {
        console.error('Error searching by metadata:', error);
        showMessage('An error occurred while searching for items.', 'error');
    }
}

/**
 * Hides the search results display and shows the full file system.
 */
function hideSearchResults() {
    document.getElementById('searchResultsDisplay').style.display = 'none';
    document.getElementById('fileSystemDisplay').style.display = 'block'; // Show file system
    document.getElementById('searchResultsList').innerHTML = ''; // Clear results
    // Optionally clear search inputs
    document.getElementById('searchFileName').value = '';
    // Preserve metadata inputs for potential next search, or clear them if desired.
    // document.getElementById('fileAuthor').value = '';
    // document.getElementById('fileTags').value = '';
    // document.getElementById('fileType').value = '';
}

// --- Recycle Bin Functions ---

/**
 * Fetches recycle bin items and displays them in a modal.
 */
async function showRecycleBinModal() {
    try {
        const response = await fetch(getRecycleBinItemsUrl);
        const data = await response.json();
        if (data.success) {
            recycleBinItems = data.items;
            renderRecycleBinList();
            document.getElementById('recycleBinModal').style.display = 'flex';
        } else {
            showMessage('Failed to load recycle bin items: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('Error fetching recycle bin items:', error);
        showMessage('An error occurred while loading recycle bin.', 'error');
    }
}

/**
 * Renders the list of items in the recycle bin modal.
 */
function renderRecycleBinList() {
    const recycleBinList = document.getElementById('recycleBinList');
    recycleBinList.innerHTML = ''; // Clear previous list
    selectedRecycleBinItemIndex = -1; // Reset selection

    if (recycleBinItems.length === 0) {
        recycleBinList.innerHTML = '<li class="empty-message">Recycle Bin is empty.</li>';
    } else {
        recycleBinItems.forEach((item, index) => {
            const li = document.createElement('li');
            li.textContent = `${item.item_data.name} (${item.item_data.type}) - Original Path: ${item.original_path}`;
            li.dataset.index = index;
            li.addEventListener('click', () => selectRecycleBinItem(index, li));
            recycleBinList.appendChild(li);
        });
    }
    updateRecycleBinButtons();
}

/**
 * Selects an item in the recycle bin list.
 * @param {number} index - The index of the selected item.
 * @param {HTMLElement} element - The list item element.
 */
function selectRecycleBinItem(index, element) {
    // Deselect previously selected item
    const currentSelected = document.querySelector('#recycleBinList .selected');
    if (currentSelected) {
        currentSelected.classList.remove('selected');
    }

    // Select new item
    element.classList.add('selected');
    selectedRecycleBinItemIndex = index;
    updateRecycleBinButtons();
}

/**
 * Updates the state of the recycle bin action buttons based on selection.
 */
function updateRecycleBinButtons() {
    const restoreBtn = document.getElementById('restoreRecycleBinItem');
    const permDeleteBtn = document.getElementById('permanentDeleteRecycleBinItem');

    if (selectedRecycleBinItemIndex !== -1) {
        restoreBtn.disabled = false;
        permDeleteBtn.disabled = false;
    } else {
        restoreBtn.disabled = true;
        permDeleteBtn.disabled = true;
    }
}

/**
 * Closes the recycle bin modal.
 */
function closeRecycleBinModal() {
    document.getElementById('recycleBinModal').style.display = 'none';
    selectedRecycleBinItemIndex = -1; // Reset selection
    updateRecycleBinButtons();
}

/**
 * Handles restoring a selected item from the recycle bin.
 */
async function restoreRecycleBinItem() {
    if (selectedRecycleBinItemIndex === -1) {
        showMessage('Please select an item to restore.', 'info');
        return;
    }

    const itemToRestore = recycleBinItems[selectedRecycleBinItemIndex];
    const confirmed = await showConfirmation(`Restore '${itemToRestore.item_data.name}' (${itemToRestore.item_data.type}) to its original path '${itemToRestore.original_path}'?`);
    if (!confirmed) {
        showMessage('Restore cancelled.', 'info');
        return;
    }

    try {
        const response = await fetch(restoreFromRecycleBinUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_index: selectedRecycleBinItemIndex })
        });
        const data = await response.json();
        if (data.success) {
            showMessage(data.message, 'success');
            closeRecycleBinModal();
            fetchFileSystem(); // Refresh file system display
        } else {
            showMessage('Restore failed: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('Error restoring item:', error);
        showMessage('An error occurred during restoration.', 'error');
    }
}

/**
 * Handles permanently deleting a selected item from the recycle bin.
 */
async function permanentDeleteRecycleBinItem() {
    if (selectedRecycleBinItemIndex === -1) {
        showMessage('Please select an item to permanently delete.', 'info');
        return;
    }

    const itemToDelete = recycleBinItems[selectedRecycleBinItemIndex];
    const confirmed = await showConfirmation(`Permanently delete '${itemToDelete.item_data.name}' (${itemToDelete.item_data.type})? This cannot be undone.`);
    if (!confirmed) {
        showMessage('Permanent deletion cancelled.', 'info');
        return;
    }

    try {
        const response = await fetch(permanentDeleteItemUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_index: selectedRecycleBinItemIndex })
        });
        const data = await response.json();
        if (data.success) {
            showMessage(data.message, 'success');
            // Refresh recycle bin list
            showRecycleBinModal(); // Re-fetch and re-render to update the list
        } else {
            showMessage('Permanent deletion failed: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('Error permanent deleting item:', error);
        showMessage('An error occurred during permanent deletion.', 'error');
    }
}

/**
 * Handles emptying the entire recycle bin.
 */
async function emptyRecycleBin() {
    if (recycleBinItems.length === 0) {
        showMessage('Recycle Bin is already empty.', 'info');
        return;
    }
    const confirmed = await showConfirmation('Are you sure you want to empty the entire Recycle Bin? This cannot be undone.');
    if (!confirmed) {
        showMessage('Empty Recycle Bin cancelled.', 'info');
        return;
    }

    try {
        const response = await fetch(emptyRecycleBinUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({}) // Empty body for this operation
        });
        const data = await response.json();
        if (data.success) {
            showMessage(data.message, 'success');
            closeRecycleBinModal(); // Close and re-open to refresh the empty state
            // No need to fetchFileSystem as emptying only affects recycle bin, not live FS immediately
        } else {
            showMessage('Emptying Recycle Bin failed: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('Error emptying recycle bin:', error);
        showMessage('An error occurred while emptying the recycle bin.', 'error');
    }
}


// Initial fetch of file system when the page loads
document.addEventListener('DOMContentLoaded', () => {
    fetchFileSystem();

    // Event listeners for recycle bin modal buttons
    document.getElementById('closeRecycleBinModal').addEventListener('click', closeRecycleBinModal);
    document.getElementById('restoreRecycleBinItem').addEventListener('click', restoreRecycleBinItem);
    document.getElementById('permanentDeleteRecycleBinItem').addEventListener('click', permanentDeleteRecycleBinItem);

    // Close modal when clicking outside content
    document.getElementById('recycleBinModal').addEventListener('click', (event) => {
        if (event.target === document.getElementById('recycleBinModal')) {
            closeRecycleBinModal();
        }
    });

    // Close confirmation modal when clicking outside content
    document.getElementById('confirmationModal').addEventListener('click', (event) => {
        if (event.target === document.getElementById('confirmationModal')) {
            document.getElementById('confirmationModal').style.display = 'none';
        }
    });
});
