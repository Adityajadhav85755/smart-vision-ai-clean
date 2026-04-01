// Enhanced crypto.randomUUID polyfill
(function() {
    'use strict';
    
    // Helper function to generate UUID v4
    function generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }
    
    // Case 1: crypto exists but randomUUID doesn't
    if (typeof crypto !== 'undefined' && crypto !== null) {
        if (!crypto.randomUUID) {
            crypto.randomUUID = generateUUID;
        }
    } 
    // Case 2: crypto doesn't exist at all
    else if (typeof window !== 'undefined') {
        if (!window.crypto) {
            window.crypto = {};
        }
        window.crypto.randomUUID = generateUUID;
    }
    
    // Case 3: For web workers or other contexts
    if (typeof self !== 'undefined' && typeof self.crypto !== 'undefined') {
        if (!self.crypto.randomUUID) {
            self.crypto.randomUUID = generateUUID;
        }
    }
    
    // Case 4: Global fallback
    if (typeof global !== 'undefined' && !global.crypto) {
        global.crypto = { randomUUID: generateUUID };
    }
    
    // Polyfill loaded silently to avoid console spam
})();
