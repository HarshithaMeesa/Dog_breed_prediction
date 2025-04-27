document.addEventListener('DOMContentLoaded', function() {
    const inputs = document.querySelectorAll('.custom-input');
    inputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.style.borderColor = 'hsla(0, 90%, 32%, 0.9)';
            const icon = this.nextElementSibling.querySelector('.input-group-text i');
            if (icon) icon.style.color = 'hsla(0, 90%, 32%, 0.9)';
        });
        input.addEventListener('blur', function() {
            this.style.borderColor = 'hsla(0, 90%, 42%, 0.437)';
            const icon = this.nextElementSibling.querySelector('.input-group-text i');
            if (icon) icon.style.color = 'hsla(0, 90%, 42%, 0.7)';
        });
    });
});