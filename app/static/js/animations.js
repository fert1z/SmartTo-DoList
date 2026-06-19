// Простой Intersection Observer для анимации при скролле
document.addEventListener("DOMContentLoaded", function() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.animationPlayState = 'running';
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.feature-card-landing, .cta-landing').forEach(card => {
        card.style.animationPlayState = 'paused';
        observer.observe(card);
    });
});