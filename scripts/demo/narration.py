# Narration script for docs/media/ui-demo.mp4.
# Each entry's (start, end) must match docs/media/ui-demo.srt exactly —
# the build script uses these windows to fit and time the narration.

SCRIPT = [
    (0.00, 2.22, "Step 1: enter the approval key. It's required for every write."),
    (2.22, 6.49, 'Step 2: ask in plain English — "show all customers." Reads run instantly.'),
    (6.49, 10.58, "Ask for one customer, and get back exactly that row."),
    (10.58, 13.79, "Step 3: add a customer. Writes wait as a pending proposal."),
    (13.79, 16.08, "Approve with the key, and now it's saved to the database."),
]
