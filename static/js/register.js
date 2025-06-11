document.addEventListener('DOMContentLoaded', function() {
    // Optional: Add animation to icons on input focus
    const inputs = document.querySelectorAll('.custom-input');
    inputs.forEach(input => {
        input.addEventListener('focus', function() {
            const icon = this.parentElement.querySelector('.input-group-text i');
            if (icon) {
                icon.classList.add('fas', 'fa-bounce');
            }
        });
    });
});