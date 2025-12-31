/**
 * CKEditor 5 Table Alignment Fix
 *
 * This script fixes a known limitation in CKEditor 5 where table alignment
 * from the Table Properties panel doesn't output margin inline styles.
 *
 * Related CKEditor 5 issues:
 * - https://github.com/ckeditor/ckeditor5/issues/6179
 * - https://github.com/ckeditor/ckeditor5/issues/8770
 * - https://github.com/ckeditor/ckeditor5/issues/10289
 */

(function() {
    'use strict';

    /**
     * Apply margin styles to a table figure element based on alignment
     */
    function applyTableAlignmentStyles(writer, figure, alignment) {
        if (!figure || !alignment) {
            return;
        }

        // Define margin styles for each alignment
        const alignmentStyles = {
            'left': {
                'margin-left': '0',
                'margin-right': 'auto'
            },
            'center': {
                'margin-left': 'auto',
                'margin-right': 'auto'
            },
            'right': {
                'margin-left': 'auto',
                'margin-right': '0'
            }
        };

        const styles = alignmentStyles[alignment];
        if (!styles) {
            return;
        }

        // Get existing inline styles
        const currentStyle = figure.getAttribute('style') || '';

        // Parse existing styles into an object
        const styleObj = {};
        if (currentStyle) {
            currentStyle.split(';').forEach(rule => {
                const [key, value] = rule.split(':').map(s => s.trim());
                if (key && value) {
                    styleObj[key] = value;
                }
            });
        }

        // Update with alignment margins
        Object.assign(styleObj, styles);

        // Convert back to string
        const newStyle = Object.entries(styleObj)
            .filter(([key, value]) => key && value)
            .map(([key, value]) => `${key}: ${value}`)
            .join('; ');

        // Apply the updated style
        writer.setAttribute('style', newStyle, figure);
    }

    /**
     * Set up table alignment fix for a CKEditor instance
     */
    function setupTableAlignmentFix(editor) {
        // Listen for changes in the editor model
        editor.model.document.on('change:data', () => {
            const changes = editor.model.document.differ.getChanges();

            for (const change of changes) {
                // Check if this is an attribute change
                if (change.type === 'attribute') {
                    const element = change.range.start.nodeAfter || change.range.start.parent;

                    // Check if the changed attribute is tableAlignment
                    if (change.attributeKey === 'tableAlignment' && element.is('element', 'table')) {
                        const alignment = change.attributeNewValue;

                        // Find the parent figure element
                        const figure = element.parent;
                        if (figure && figure.is('element', 'figure') && figure.hasClass('table')) {
                            // Apply the alignment styles in a change block
                            editor.model.change(writer => {
                                applyTableAlignmentStyles(writer, figure, alignment);
                            });
                        }
                    }
                }
            }
        });

        // Also handle existing tables on editor load
        editor.model.document.on('change:data', () => {
            editor.model.change(writer => {
                const root = editor.model.document.getRoot();
                const range = writer.createRangeIn(root);

                for (const value of range.getWalker()) {
                    if (value.type === 'elementStart') {
                        const element = value.item;

                        // Find table elements
                        if (element.is('element', 'table')) {
                            const alignment = element.getAttribute('tableAlignment');
                            const figure = element.parent;

                            if (alignment && figure && figure.is('element', 'figure') && figure.hasClass('table')) {
                                // Check if margin styles are missing
                                const currentStyle = figure.getAttribute('style') || '';
                                const hasMarginLeft = currentStyle.includes('margin-left');
                                const hasMarginRight = currentStyle.includes('margin-right');

                                // Only apply if margins are missing
                                if (!hasMarginLeft || !hasMarginRight) {
                                    applyTableAlignmentStyles(writer, figure, alignment);
                                }
                            }
                        }
                    }
                }
            });
        }, { priority: 'low' }); // Use low priority to run after other handlers

        console.log('CKEditor table alignment fix initialized');
    }

    /**
     * Initialize the table alignment fix for all CKEditor instances
     */
    function initializeTableAlignmentFix() {
        // Check for CKEditor instances periodically
        const checkInterval = setInterval(function() {
            // Try multiple selectors to find CKEditor elements
            const selectors = [
                '.django_ckeditor_5',
                '.ck-editor',
                '[id*="ckeditor"]',
                'textarea[name*="content"]',
                'textarea[name*="bio"]'
            ];

            let foundEditors = [];
            selectors.forEach(selector => {
                const elements = document.querySelectorAll(selector);
                elements.forEach(el => {
                    if (!foundEditors.includes(el)) {
                        foundEditors.push(el);
                    }
                });
            });

            // Look for CKEditor instances
            foundEditors.forEach(function(element) {
                // Method 1: Check for ckeditorInstance property
                if (element.ckeditorInstance && !element.ckeditorInstance._tableAlignmentFixApplied) {
                    setupTableAlignmentFix(element.ckeditorInstance);
                    element.ckeditorInstance._tableAlignmentFixApplied = true;
                }

                // Method 2: Check if element is within .ck-editor container
                const ckEditorContainer = element.closest('.ck-editor');
                if (ckEditorContainer) {
                    const editable = ckEditorContainer.querySelector('.ck-editor__editable');
                    if (editable && editable.ckeditorInstance && !editable.ckeditorInstance._tableAlignmentFixApplied) {
                        setupTableAlignmentFix(editable.ckeditorInstance);
                        editable.ckeditorInstance._tableAlignmentFixApplied = true;
                    }
                }

                // Method 3: Check for editor in the parent's nextElementSibling
                if (element.nextElementSibling && element.nextElementSibling.classList.contains('ck-editor')) {
                    const editable = element.nextElementSibling.querySelector('.ck-editor__editable');
                    if (editable && editable.ckeditorInstance && !editable.ckeditorInstance._tableAlignmentFixApplied) {
                        setupTableAlignmentFix(editable.ckeditorInstance);
                        editable.ckeditorInstance._tableAlignmentFixApplied = true;
                    }
                }
            });

            // Stop checking after 10 seconds
            if (Date.now() - startTime > 10000) {
                clearInterval(checkInterval);
            }
        }, 500);

        const startTime = Date.now();
    }

    // Run when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeTableAlignmentFix);
    } else {
        initializeTableAlignmentFix();
    }

    // Also run when page is fully loaded (for dynamic content)
    window.addEventListener('load', function() {
        setTimeout(initializeTableAlignmentFix, 1000);
    });

})();
