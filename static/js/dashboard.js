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

    // Initialize Bootstrap modal
    const deleteModal = document.getElementById('deleteEpisodeModal');
    if (deleteModal) {
        // Handle delete episode buttons
        document.querySelectorAll('.delete-episode').forEach(button => {
            button.addEventListener('click', function() {
                const feedId = this.dataset.feedId;
                const episodeId = this.dataset.episodeId;
                const episodeTitle = this.dataset.episodeTitle;

                // Update modal content
                const titleSpan = deleteModal.querySelector('#episodeTitle');
                if (titleSpan) {
                    titleSpan.textContent = episodeTitle;
                }

                // Set form action
                const form = deleteModal.querySelector('#deleteEpisodeForm');
                if (form) {
                    form.action = `/feed/${feedId}/episode/${episodeId}/delete`;
                }
            });
        });
    }
});