/**
 * Sidebar Resize Functionality
 *
 * Allows users to drag the left edge of the sidebar to resize it.
 */

(function() {
    let isResizing = false;
    let startX = 0;
    let startWidth = 0;
    let sidebar = null;
    let resizeHandle = null;

    function initSidebarResize() {
        sidebar = document.getElementById('sidebar');
        resizeHandle = document.getElementById('sidebar-resize-handle');

        if (!sidebar || !resizeHandle) {
            return;
        }

        // Mouse down on resize handle
        resizeHandle.addEventListener('mousedown', (e) => {
            isResizing = true;
            startX = e.clientX;
            startWidth = sidebar.offsetWidth;

            sidebar.classList.add('resizing');
            document.body.style.cursor = 'ew-resize';
            document.body.style.userSelect = 'none';

            e.preventDefault();
        });

        // Mouse move
        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;

            // Calculate new width (resize from left, so subtract delta)
            const deltaX = startX - e.clientX;
            const newWidth = startWidth + deltaX;

            // Apply constraints
            const minWidth = 250;
            const maxWidth = 800;
            const constrainedWidth = Math.max(minWidth, Math.min(maxWidth, newWidth));

            sidebar.style.width = `${constrainedWidth}px`;

            e.preventDefault();
        });

        // Mouse up
        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                sidebar.classList.remove('resizing');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
            }
        });

        // Touch support for mobile
        resizeHandle.addEventListener('touchstart', (e) => {
            isResizing = true;
            startX = e.touches[0].clientX;
            startWidth = sidebar.offsetWidth;

            sidebar.classList.add('resizing');

            e.preventDefault();
        });

        document.addEventListener('touchmove', (e) => {
            if (!isResizing) return;

            const deltaX = startX - e.touches[0].clientX;
            const newWidth = startWidth + deltaX;

            const minWidth = 250;
            const maxWidth = 800;
            const constrainedWidth = Math.max(minWidth, Math.min(maxWidth, newWidth));

            sidebar.style.width = `${constrainedWidth}px`;

            e.preventDefault();
        }, { passive: false });

        document.addEventListener('touchend', () => {
            if (isResizing) {
                isResizing = false;
                sidebar.classList.remove('resizing');
            }
        });
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSidebarResize);
    } else {
        initSidebarResize();
    }
})();
