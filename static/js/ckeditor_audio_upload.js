/**
 * Audio Upload Helper for CKEditor 5
 * Adds audio upload functionality by creating buttons next to CKEditor instances
 */

(function() {
    'use strict';

    // Function to create an audio upload button for a CKEditor instance
    function createAudioUploadButton(editorElement, editorInstance) {
        // Check if button already exists
        if (editorElement.parentElement.querySelector('.audio-upload-btn')) {
            return;
        }

        // Create button container
        const btnContainer = document.createElement('div');
        btnContainer.className = 'audio-upload-container mb-2';
        btnContainer.style.cssText = 'margin-bottom: 0.5rem;';

        // Create the upload button
        const uploadBtn = document.createElement('button');
        uploadBtn.type = 'button';
        uploadBtn.className = 'audio-upload-btn btn btn-sm btn-outline gap-2';
        uploadBtn.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19.114 5.636a9 9 0 010 12.728M16.463 8.288a5.25 5.25 0 010 7.424M6.75 8.25l4.72-4.72a.75.75 0 011.28.53v15.88a.75.75 0 01-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 012.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75z" />
            </svg>
            Upload Audio File
        `;

        uploadBtn.addEventListener('click', function() {
            openAudioFilePicker(editorInstance);
        });

        btnContainer.appendChild(uploadBtn);

        // Insert button before the editor
        editorElement.parentElement.insertBefore(btnContainer, editorElement);
    }

    // Open file picker for audio files
    function openAudioFilePicker(editor) {
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.accept = 'audio/mp3,audio/wav,audio/ogg,audio/m4a,audio/aac,.mp3,.wav,.ogg,.m4a,.aac';
        fileInput.style.display = 'none';

        fileInput.addEventListener('change', function(event) {
            const file = event.target.files[0];
            if (file) {
                uploadAudioFile(file, editor);
            }
        });

        document.body.appendChild(fileInput);
        fileInput.click();
        document.body.removeChild(fileInput);
    }

    // Upload audio file to server
    function uploadAudioFile(file, editor) {
        // Get CSRF token
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
                         document.querySelector('meta[name="csrf-token"]')?.content || '';

        // Create FormData
        const formData = new FormData();
        formData.append('upload', file);

        // Show loading message
        const loadingMsg = document.createElement('div');
        loadingMsg.className = 'alert alert-info mt-2';
        loadingMsg.innerHTML = '<span>Uploading audio file...</span>';
        const editorContainer = editor.sourceElement?.parentElement || editor.ui.view.element.parentElement;
        editorContainer.appendChild(loadingMsg);

        // Upload file
        fetch('/ckeditor5/image_upload/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            loadingMsg.remove();

            if (data.url) {
                insertAudioElement(editor, data.url, file.name);

                // Show success message
                const successMsg = document.createElement('div');
                successMsg.className = 'alert alert-success mt-2';
                successMsg.innerHTML = '<span>✓ Audio uploaded successfully!</span>';
                editorContainer.appendChild(successMsg);
                setTimeout(() => successMsg.remove(), 3000);
            } else {
                throw new Error(data.error?.message || 'Upload failed');
            }
        })
        .catch(error => {
            loadingMsg.remove();
            console.error('Audio upload error:', error);

            const errorMsg = document.createElement('div');
            errorMsg.className = 'alert alert-error mt-2';
            errorMsg.innerHTML = `<span>✗ Upload failed: ${error.message}</span>`;
            editorContainer.appendChild(errorMsg);
            setTimeout(() => errorMsg.remove(), 5000);
        });
    }

    // Insert audio element into CKEditor
    function insertAudioElement(editor, url, filename) {
        // Determine MIME type
        const extension = url.split('.').pop().toLowerCase();
        const mimeTypes = {
            'mp3': 'audio/mpeg',
            'wav': 'audio/wav',
            'ogg': 'audio/ogg',
            'm4a': 'audio/mp4',
            'aac': 'audio/aac'
        };
        const mimeType = mimeTypes[extension] || 'audio/mpeg';

        // Create HTML for audio player
        const audioHtml = `
<figure class="media">
    <audio controls style="width: 100%;">
        <source src="${url}" type="${mimeType}">
        Your browser does not support the audio element.
    </audio>
    <figcaption>${filename}</figcaption>
</figure>
<p>&nbsp;</p>
        `.trim();

        // Insert into editor using setData to append
        editor.model.change(writer => {
            const viewFragment = editor.data.processor.toView(audioHtml);
            const modelFragment = editor.data.toModel(viewFragment);
            editor.model.insertContent(modelFragment);
        });
    }

    // Initialize audio upload buttons for all CKEditor instances
    function initializeAudioUpload() {
        // Wait for CKEditor instances to be ready
        const checkEditors = setInterval(function() {
            // Find all CKEditor elements
            const editorElements = document.querySelectorAll('.django_ckeditor_5');

            editorElements.forEach(function(editorElement) {
                // Try to find the CKEditor instance
                // CKEditor 5 stores instance reference on the DOM element
                if (editorElement.ckeditorInstance) {
                    createAudioUploadButton(editorElement, editorElement.ckeditorInstance);
                }
            });

            // Stop checking after 10 seconds
            if (Date.now() - startTime > 10000) {
                clearInterval(checkEditors);
            }
        }, 500);

        const startTime = Date.now();
    }

    // Run when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeAudioUpload);
    } else {
        initializeAudioUpload();
    }

    // Also run when page is fully loaded (for dynamic content)
    window.addEventListener('load', function() {
        setTimeout(initializeAudioUpload, 1000);
    });

})();
