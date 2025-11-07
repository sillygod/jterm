// CodeMirror 6 ES Module Setup for jterm
// This file provides a way to load CodeMirror 6 from CDN as ES modules

// Import CodeMirror 6 core and SQL language support
// Usage: import { EditorView, basicSetup, sql } from './static/vendor/codemirror/setup.js'

// Core CodeMirror 6 modules from esm.sh CDN
export * from 'https://esm.sh/@codemirror/view@6.21.3';
export * from 'https://esm.sh/@codemirror/state@6.2.1';
export { basicSetup } from 'https://esm.sh/codemirror@6.0.1';

// Language support
export { sql } from 'https://esm.sh/@codemirror/lang-sql@6.5.4';
export { json } from 'https://esm.sh/@codemirror/lang-json@6.0.1';

// Theme support
export { oneDark } from 'https://esm.sh/@codemirror/theme-one-dark@6.1.2';

// Additional useful extensions
export { closeBrackets } from 'https://esm.sh/@codemirror/autocomplete@6.10.2';
export { searchKeymap } from 'https://esm.sh/@codemirror/search@6.5.4';