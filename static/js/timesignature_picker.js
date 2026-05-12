/**
 * Time Signature Picker for CKEditor 5
 * Injects a row of clickable buttons below each CKEditor instance
 * that insert TimeSignatures font glyphs at the cursor position.
 */

(function () {
    'use strict';

    var TIME_SIGNATURES = [
        { label: '4/4', char: '\uE000' },
        { label: '5/4', char: '\uE001' },
        { label: '3/4', char: '\uE002' },
        { label: '2/4', char: '\uE003' },
        { label: '4/2', char: '\uE004' },
        { label: '3/2', char: '\uE005' },
        { label: '2/2', char: '\uE006' },
        { label: '4/8', char: '\uE007' },
        { label: '3/8', char: '\uE008' },
        { label: '6/8', char: '\uE009' },
        { label: '9/8', char: '\uE00A' },
    ];

    function attachPicker(ckEditorEl, editor) {
        if (ckEditorEl.dataset.tsPicker) return;
        ckEditorEl.dataset.tsPicker = '1';

        var container = document.createElement('div');
        container.className = 'flex flex-wrap items-center gap-1 mt-1 mb-2';

        var heading = document.createElement('span');
        heading.className = 'text-xs opacity-50 mr-1';
        heading.textContent = 'Time signatures:';
        container.appendChild(heading);

        TIME_SIGNATURES.forEach(function (sig) {
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'btn btn-xs btn-outline';
            btn.textContent = sig.label;
            btn.title = 'Insert ' + sig.label + ' time signature';
            btn.addEventListener('click', function () {
                editor.model.change(function (writer) {
                    editor.model.insertContent(writer.createText(sig.char));
                });
                editor.editing.view.focus();
            });
            container.appendChild(btn);
        });

        ckEditorEl.insertAdjacentElement('afterend', container);
    }

    function initializePickers() {
        var startTime = Date.now();
        var interval = setInterval(function () {
            document.querySelectorAll('.ck-editor').forEach(function (ckEditorEl) {
                var editable = ckEditorEl.querySelector('.ck-editor__editable');
                if (editable && editable.ckeditorInstance) {
                    attachPicker(ckEditorEl, editable.ckeditorInstance);
                }
            });
            if (Date.now() - startTime > 10000) {
                clearInterval(interval);
            }
        }, 500);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializePickers);
    } else {
        initializePickers();
    }

    window.addEventListener('load', function () {
        setTimeout(initializePickers, 1000);
    });
})();
