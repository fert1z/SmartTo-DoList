// Simple accordion for FAQ
document.querySelectorAll('.faq-item h4').forEach(function(header) {
    header.addEventListener('click', function() {
        var answer = this.nextElementSibling;
        answer.style.display = answer.style.display === 'block' ? 'none' : 'block';
    });
});
