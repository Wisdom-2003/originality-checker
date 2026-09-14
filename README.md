# OriginalityChecker — Render Test Version

A public test deployment of the OriginalityChecker plagiarism/similarity and AI-writing indicator web app.

## Deploy on Render

1. Upload this repository to GitHub.
2. In Render, choose **New → Web Service**.
3. Connect the GitHub repository.
4. Choose the `main` branch.
5. Select **Docker** as the runtime.
6. Use the free plan for testing.
7. Create the service.
8. Wait for the build/deploy to finish.
9. Open the generated `onrender.com` URL in Chrome.

Render must expose the application on `0.0.0.0` and the configured `PORT`. This project is already configured for that.

## Current test features

- PDF, DOCX and TXT upload
- Similarity/originality analysis against the included starter corpus
- Citation-health heuristic
- Conservative AI-writing indicators
- Results dashboard
- Health endpoint

## Important

This is a test deployment, not yet the final production plagiarism engine. The similarity corpus is intentionally small and the AI-writing result is an indicator, not proof of AI authorship.
