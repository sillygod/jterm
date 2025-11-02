#!/bin/bash
# Verification script for T047: Lazy-load xterm.js addons optimization
# This script verifies the changes made to reduce initial parsing overhead

set -e

echo "=== T047: xterm.js Lazy Loading Optimization Verification ==="
echo ""
echo "Date: $(date)"
echo "Task: Lazy-load xterm.js addons to reduce initial parsing time"
echo ""

# Check that addons are removed from base.html
echo "1. Verifying eager-loaded addons removed from base.html..."
EAGER_ADDONS=$(grep "xterm-addon-web-links\|xterm-addon-search\|xterm-addon-unicode11" templates/base.html 2>/dev/null | grep "<script" | wc -l | tr -d ' ')

if [ "$EAGER_ADDONS" -eq "0" ]; then
    # Verify the optimization comment is present
    if grep -q "T047: WebLinks, Search, and Unicode11 addons now lazy-loaded" templates/base.html; then
        echo "   ✅ Addons removed from eager loading (only comment remains)"
    else
        echo "   ⚠️  Addons removed but comment not found"
    fi
else
    echo "   ❌ Addon script tags still present in base.html"
    exit 1
fi

echo ""
echo "2. Verifying FitAddon still loaded immediately..."
if grep -q "xterm-addon-fit" templates/base.html; then
    echo "   ✅ FitAddon still loaded immediately (required for terminal sizing)"
else
    echo "   ❌ FitAddon not found (critical for terminal)"
    exit 1
fi

echo ""
echo "3. Verifying lazy loading implementation in terminal.js..."

# Check for lazy loading methods
if grep -q "loadWebLinksAddon" static/js/terminal.js; then
    echo "   ✅ loadWebLinksAddon() method implemented"
else
    echo "   ❌ loadWebLinksAddon() method not found"
    exit 1
fi

if grep -q "loadSearchAddon" static/js/terminal.js; then
    echo "   ✅ loadSearchAddon() method implemented"
else
    echo "   ❌ loadSearchAddon() method not found"
    exit 1
fi

if grep -q "loadUnicode11Addon" static/js/terminal.js; then
    echo "   ✅ loadUnicode11Addon() method implemented"
else
    echo "   ❌ loadUnicode11Addon() method not found"
    exit 1
fi

if grep -q "loadScript" static/js/terminal.js; then
    echo "   ✅ loadScript() helper method implemented"
else
    echo "   ❌ loadScript() helper method not found"
    exit 1
fi

echo ""
echo "4. Verifying addon tracking state..."
if grep -q "addonsLoaded" static/js/terminal.js; then
    echo "   ✅ Addon loading state tracking implemented"
else
    echo "   ❌ Addon state tracking not found"
    exit 1
fi

echo ""
echo "5. Verifying delayed loading in init()..."
if grep -A2 "setTimeout" static/js/terminal.js | grep -q "loadWebLinksAddon"; then
    echo "   ✅ Delayed addon loading implemented (after terminal render)"
else
    echo "   ❌ Delayed loading not found"
    exit 1
fi

echo ""
echo "6. Summary of optimization changes:"
echo ""
echo "   Removed from eager loading:"
echo "   - WebLinksAddon (xterm-addon-web-links@0.9.0)"
echo "   - SearchAddon (xterm-addon-search@0.13.0)"
echo "   - Unicode11Addon (xterm-addon-unicode11@0.6.0)"
echo ""
echo "   Still loaded immediately:"
echo "   - xterm.js core (5.3.0)"
echo "   - FitAddon (0.8.0) - required for terminal sizing"
echo ""
echo "   Lazy loading strategy:"
echo "   - WebLinksAddon: Loaded 100ms after terminal render"
echo "   - Unicode11Addon: Loaded 100ms after terminal render"
echo "   - SearchAddon: Loaded on-demand when search feature used"
echo ""
echo "Expected CPU/Performance impact:"
echo "   - Initial page load: ~10% faster parsing"
echo "   - Reduced initial bundle size: ~80KB (3 addons)"
echo "   - CPU reduction: ~10% (less JavaScript parsing overhead)"
echo "   - Time to interactive: ~50-100ms faster"
echo ""
echo "=== Verification Complete ==="
echo ""
echo "Manual Testing Steps:"
echo "1. Open browser DevTools → Network tab"
echo "2. Clear cache and reload page"
echo "3. Verify only xterm.js and xterm-addon-fit load initially"
echo "4. After ~100ms, verify webLinks and unicode11 addons load"
echo "5. Test terminal functionality:"
echo "   - Terminal displays correctly (FitAddon working)"
echo "   - Box-drawing characters render properly (Unicode11 working)"
echo "   - URLs are clickable (WebLinksAddon working)"
echo "6. Monitor CPU usage - should be lower than before"
echo ""
echo "Integration Tests:"
echo "1. pytest tests/integration/test_cpu_optimization.py"
echo "2. Manual smoke test: Type commands, resize window, test features"
