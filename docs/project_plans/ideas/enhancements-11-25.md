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
3. Native Claude Plugin support
    - Explore adding native support for popular Claude Plugins directly within SkillMeat.
    - Would allow users to easily add and browse Claude Plugin Marketplaces for their projects without needing separate setup steps.
4. The web app should maintain a stable cache of project data
    - Currently, the app fetches project data everytime the web app reloads and wipes the cache, or when the TTL expires. This can take a minute or more for large projects, or when many projects are managed.
    - Instead, we need a method for the app to maintain a status of all managed projects for the web app and CLI, without needing to re-fetch everything on every reload. It should run once the web app has been started, and then periodically update in the background based on various triggers.
    - This could be done via a small local database or persistent cache that stores project metadata and only refreshes when changes are made or after a longer TTL. However, we want to keep the implementation lightweight and portable, so must keep that in mind.
    - Updates could be fetched in the background to keep the UI responsive, perhaps noting if an artifact is out-of-date and needs refreshing.
    - Updates could trigger on a specific time-basis, or manual refresh, or when updatese are made. Updates made by Skillmeat (CLI or web) should auto-update the cache as well to keep everything in sync.
    - This cache could also be used to speed up other operations, such as searching for artifacts, checking for updates, etc. It could also be used to cache "Marketplaces" for online collections of artifacts for those already added to the user's Marketplace collection.
5. Improve artifact versioning and rollback support
    - Implement a more robust versioning system for artifacts, allowing users to easily view version history, compare versions, and roll back to previous versions if needed.
    - Could update the existing History tab in the unified artifact Modal to show artifact activity in one section, then a detailed version history in another, and provide rollback options.
    - Users should be able to select any prior version and view the all the content for that version in the standard Content viewer, view diffs, or restore that version with a single click. This could either all be performed within the History tab, or could open a dedicated modal for that version of the artifact.
    - Similar to above request (4), this will this will require architecting a clean method for storing and retrieving prior versions of artifacts.
6. Artifact Diffs should cleanly support merges upstream
    - Currently when viewing the diff between levels of an artifact (Source, Collection, Project), there is no clean way to determine local changes vs upstream changes when both have diverged.
    - Instead, Skillmeat should be able to manage file changes and determine local changes vs existing.
    - For example, if the Source has changed since last sync, and the Project has local changes, the diff viewer should be able to show both sets of changes clearly, and provide a clean method for merging upstream changes into the local project while preserving local edits. Ideally, this would automatically merge changes which weren't changed locally, only prompting the user for conflicts based on local changes. Ideally, when showing the diff in the Diff Viewer, there should be a clear indication of which changes are local vs normal upstream updates to the existing codebase, perhaps with color-coding or labels.
