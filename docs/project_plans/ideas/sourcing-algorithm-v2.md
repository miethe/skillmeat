# Sourcing Algorithm Updates

**Date:** 2025-12-28

## Overview

The sourcing algorithm seems to be pulling directory names as sources now, ie 'commands', 'agents', etc, when within plugins. Only specific entity types will contain more than a single file (ie skills), and will generally have a structured format.

Specifically, for now we should update the algorithm to detect plugins, treating each directory within a plugin as a separate group of sources, rather than each directory within the plugin being treated as a potential entity itself. ie the 'commands' and 'agents' directories within each plugin should be identified as the static names of those entity types, rather than being treated as potential entity names themselves. The same should be done for 'skills', 'hooks', 'rules'.

Later, we should implement native support for plugins, treating them as first-class artifact types within the app, as bundles of other artifacts. We should also expand support to all Claude-native entities, ie hooks, rules, etc. All else should be filtered towards Context Entities, but perhaps with an expanded subtypes field.