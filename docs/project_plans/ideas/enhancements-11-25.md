# Enhancements and Other Ideas

**Date:** November 25, 2025

## Idea List

1. Auto-scanning for artifact imports
    - Implement a feature that automatically scans project directories for existing artifacts in `.claude`, ie existing skills, agents, etc, and notify users and ask if they'd like to import them.
    - Would default to local installs, but could have a bulk import screen with a table of all artifacts being imported, allowing user to add sources and other parameters/edits before confirming import.
      - Could do the same for individual imports, and should allow after-the-fact edits to artifact parameters.
2. Auto-populate details when adding artifact
    - When adding an artifact (skill, agent, etc), if user provides a URL (eg GitHub repo), auto-fetch and populate as many details as possible (name, description, topics, source, etc) to minimize user input.
    - User can then edit any fields before confirming addition.
    - Would require some parsing logic for common sources (GitHub, GitLab, etc) to extract relevant metadata.
3. Native Plugin support
    - Explore adding native support for popular Claude Plugins directly within SkillMeat.
    - Would allow users to easily add and browse Claude Plugin Marketplaces for their projects without needing separate setup steps.
4. The web app should maintain a stable cache of project data
    - Currently, the app fetches project data everytime the web app reloads and wipes the cache, or when the TTL expires. This can take a minute or more for large projects, or when many projects are managed.
    - Instead, we need a method for the app to maintain a status of all managed projects for the web app and CLI, without needing to re-fetch everything on every reload.
    - This could be done via a local database or persistent cache that stores project metadata and only refreshes when changes are made or after a longer TTL. However, we want to keep the implementation lightweight and portable, so must keep that in mind.
    - Updates could be fetched in the background to keep the UI responsive, perhaps noting if an artifact is out-of-date and needs refreshing.
    - Updates could trigger on a specific time-basis, or manual refresh, or when updatese are made. Updates made by Skillmeat (CLI or web) should auto-update the cache as well to keep everything in sync.
5. Improved search and filtering for artifacts