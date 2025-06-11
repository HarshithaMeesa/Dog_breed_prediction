document.addEventListener('DOMContentLoaded', function() {
         // Auto-dismiss alerts after 5 seconds
         const alerts = document.querySelectorAll('.alert');
         alerts.forEach(alert => {
             setTimeout(() => {
                 alert.classList.remove('show');
                 alert.classList.add('fade');
             }, 5000);
         });

         // Add animation to icons on input focus
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