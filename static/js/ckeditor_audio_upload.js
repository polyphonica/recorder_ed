/**
 * Custom Audio Upload Plugin for CKEditor 5
 * Adds a button to upload and insert audio files with HTML5 audio player
 */

class AudioUpload extends ClassicEditor.builtinPlugins.Plugin {
    init() {
        const editor = this.editor;

        // Add the audioUpload button to the component factory
        editor.ui.componentFactory.add('audioUpload', locale => {
            const view = new ClassicEditor.builtinPlugins.ButtonView(locale);

            view.set({
                label: 'Insert Audio',
                icon: '<svg viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path d="M10 3a7 7 0 1 0 0 14 7 7 0 0 0 0-14zm0 1.5a5.5 5.5 0 1 1 0 11 5.5 5.5 0 0 1 0-11zM8 7v6l5-3-5-3z"/></svg>',
                tooltip: true
            });

            // Execute when the button is clicked
            view.on('execute', () => {
                this._openFileDialog(editor);
            });

            return view;
        });
    }

    _openFileDialog(editor) {
        // Create hidden file input
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.accept = 'audio/mp3,audio/wav,audio/ogg,audio/m4a,audio/aac,.mp3,.wav,.ogg,.m4a,.aac';
        fileInput.style.display = 'none';

        fileInput.addEventListener('change', (event) => {
            const file = event.target.files[0];
            if (file) {
                this._uploadAudio(editor, file);
            }
        });

        document.body.appendChild(fileInput);
        fileInput.click();
        document.body.removeChild(fileInput);
    }

    _uploadAudio(editor, file) {
        // Get CSRF token for Django
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
                         document.querySelector('meta[name="csrf-token"]')?.content || '';

        // Create FormData for upload
        const formData = new FormData();
        formData.append('upload', file);

        // Show upload progress notification
        editor.plugins.get('Notification').showInfo('Uploading audio file...', {
            namespace: 'audioUpload'
        });

        // Upload the file using CKEditor's configured upload URL
        fetch('/ckeditor5/image_upload/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.url) {
                this._insertAudioElement(editor, data.url, file.name);
                editor.plugins.get('Notification').showSuccess('Audio uploaded successfully!', {
                    namespace: 'audioUpload'
                });
            } else if (data.error) {
                throw new Error(data.error.message || 'Upload failed');
            }
        })
        .catch(error => {
            console.error('Audio upload error:', error);
            editor.plugins.get('Notification').showWarning('Audio upload failed: ' + error.message, {
                namespace: 'audioUpload'
            });
        });
    }

    _insertAudioElement(editor, url, filename) {
        // Determine audio type from URL
        const extension = url.split('.').pop().toLowerCase();
        const mimeTypes = {
            'mp3': 'audio/mpeg',
            'wav': 'audio/wav',
            'ogg': 'audio/ogg',
            'm4a': 'audio/mp4',
            'aac': 'audio/aac'
        };
        const mimeType = mimeTypes[extension] || 'audio/mpeg';

        // Create HTML5 audio element
        const audioHtml = `
            <figure class="media">
                <audio controls style="width: 100%;">
                    <source src="${url}" type="${mimeType}">
                    Your browser does not support the audio element.
                </audio>
                <figcaption>${filename}</figcaption>
            </figure>
        `;

        // Insert into editor
        const viewFragment = editor.data.processor.toView(audioHtml);
        const modelFragment = editor.data.toModel(viewFragment);
        editor.model.insertContent(modelFragment);
    }
}

// Make the plugin available globally
window.AudioUpload = AudioUpload;
