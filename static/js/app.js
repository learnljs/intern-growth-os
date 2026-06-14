// Growth Twin interactive features
document.addEventListener('DOMContentLoaded', function() {
    // Animate XP bar on load
    const xpFill = document.querySelector('.xp-bar-fill');
    if (xpFill) {
        const targetWidth = xpFill.style.width;
        xpFill.style.width = '0%';
        setTimeout(() => { xpFill.style.width = targetWidth; }, 100);
    }

    // Animate dimension bars
    document.querySelectorAll('.dim-bar-fill').forEach(bar => {
        const targetWidth = bar.style.width;
        bar.style.width = '0%';
        setTimeout(() => { bar.style.width = targetWidth; }, 200);
    });
});
