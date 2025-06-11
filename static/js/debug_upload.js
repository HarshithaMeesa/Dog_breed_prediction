function uploadImage() {
    console.log("uploadImage function called");
    const tempCanvas = document.createElement('canvas');
    // ... (your existing code to set up the canvas) ...
    const dataURL = tempCanvas.toDataURL('image/jpeg');
    console.log("Image data prepared:", dataURL.substring(0, 50)); // Log first 50 chars
    document.getElementById('imageData').value = dataURL;
    const form = document.getElementById('captureForm');
    console.log("Submitting form");
    form.submit();
}