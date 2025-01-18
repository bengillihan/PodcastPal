document.addEventListener('DOMContentLoaded', function() {
    // Handle RSS feed URL copy buttons
    document.querySelectorAll('.copy-btn').forEach(button => {
        button.addEventListener('click', async function() {
            const feedUrl = this.dataset.feedUrl;
            try {
                await navigator.clipboard.writeText(feedUrl);
                const originalText = this.textContent;
                this.textContent = 'Copied!';
                setTimeout(() => {
                    this.textContent = originalText;
                }, 2000);
            } catch (err) {
                console.error('Failed to copy: ', err);
            }
        });
    });
});
