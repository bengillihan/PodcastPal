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

    // Handle delete episode buttons
    const deleteModal = new bootstrap.Modal(document.getElementById('deleteEpisodeModal'));
    document.querySelectorAll('.delete-episode').forEach(button => {
        button.addEventListener('click', function() {
            const feedId = this.dataset.feedId;
            const episodeId = this.dataset.episodeId;
            const episodeTitle = this.dataset.episodeTitle;

            document.getElementById('episodeTitle').textContent = episodeTitle;
            const deleteForm = document.getElementById('deleteEpisodeForm');
            deleteForm.action = `/feed/${feedId}/episode/${episodeId}/delete`;

            deleteModal.show();
        });
    });
});