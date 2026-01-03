# Marketplace Sources Non-Skills V1 Bug Report

**Date:** 2025-12-31

## Summary

Currently, only Skills seem to be correctly detected by our marketplace source detection system. Other types of sources, such as Commands and Agents, are not being identified properly. Instead, they tend to be misclassified as Skills.

For example, if there is a directory 'commands/', the directories within (ie 'commands/git' and 'commands/dev') are parsed as skills, with each directory classified as a skill (ie 'dev'), rather than as directories each containing commands (ie 'commands/dev/dev-feature.md').

## Proposed Solution

We need to tune our detection algorithm. Skill detection seems to work very well, so we should focus on adjusting the logic to better identify other source types. Generally, we should start by looking at the directory structure and going from there. In some cases, the Source root directory may contain a directory per artifact type (eg 'skills/', 'commands/', 'agents/'), and in other cases, the directories may be further nested, especially if the sources are plugins.