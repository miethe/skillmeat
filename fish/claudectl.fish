# claudectl/skillmeat fish completion script
# Install: Copy to ~/.config/fish/completions/claudectl.fish

# Disable file completion by default
complete -c claudectl -f
complete -c skillmeat -f

# Global options
complete -c claudectl -l help -d 'Show help message'
complete -c claudectl -l version -d 'Show version'
complete -c claudectl -l smart-defaults -d 'Enable claudectl smart defaults'

complete -c skillmeat -l help -d 'Show help message'
complete -c skillmeat -l version -d 'Show version'
complete -c skillmeat -l smart-defaults -d 'Enable claudectl smart defaults'

# Commands
set -l commands quick-add deploy remove undeploy search list status show sync-check sync-pull sync-preview diff bundle config collection alias init

complete -c claudectl -n "not __fish_seen_subcommand_from $commands" -a quick-add -d 'Add artifact with smart defaults'
complete -c claudectl -n "not __fish_seen_subcommand_from $commands" -a deploy -d 'Deploy artifacts to project'
complete -c claudectl -n "not __fish_seen_subcommand_from $commands" -a remove -d 'Remove artifact from collection'
complete -c claudectl -n "not __fish_seen_subcommand_from $commands" -a undeploy -d 'Remove deployed artifact from project'
complete -c claudectl -n "not __fish_seen_subcommand_from $commands" -a search -d 'Search artifacts in collection'
complete -c claudectl -n "not __fish_seen_subcommand_from $commands" -a list -d 'List artifacts in collection'
complete -c claudectl -n "not __fish_seen_subcommand_from $commands" -a status -d 'Show deployment status'
complete -c claudectl -n "not __fish_seen_subcommand_from $commands" -a show -d 'Show artifact details'
complete -c claudectl -n "not __fish_seen_subcommand_from $commands" -a sync-check -d 'Check for upstream changes'
complete -c claudectl -n "not __fish_seen_subcommand_from $commands" -a sync-pull -d 'Pull upstream changes'
complete -c claudectl -n "not __fish_seen_subcommand_from $commands" -a sync-preview -d 'Preview sync changes'
complete -c claudectl -n "not __fish_seen_subcommand_from $commands" -a diff -d 'Show differences with upstream'
complete -c claudectl -n "not __fish_seen_subcommand_from $commands" -a bundle -d 'Manage artifact bundles'
complete -c claudectl -n "not __fish_seen_subcommand_from $commands" -a config -d 'Manage configuration'
complete -c claudectl -n "not __fish_seen_subcommand_from $commands" -a collection -d 'View or switch collection'
complete -c claudectl -n "not __fish_seen_subcommand_from $commands" -a alias -d 'Manage claudectl alias'
complete -c claudectl -n "not __fish_seen_subcommand_from $commands" -a init -d 'Initialize a new collection'

# Copy same commands for skillmeat
complete -c skillmeat -n "not __fish_seen_subcommand_from $commands" -a quick-add -d 'Add artifact with smart defaults'
complete -c skillmeat -n "not __fish_seen_subcommand_from $commands" -a deploy -d 'Deploy artifacts to project'
complete -c skillmeat -n "not __fish_seen_subcommand_from $commands" -a remove -d 'Remove artifact from collection'
complete -c skillmeat -n "not __fish_seen_subcommand_from $commands" -a undeploy -d 'Remove deployed artifact from project'
complete -c skillmeat -n "not __fish_seen_subcommand_from $commands" -a search -d 'Search artifacts in collection'
complete -c skillmeat -n "not __fish_seen_subcommand_from $commands" -a list -d 'List artifacts in collection'
complete -c skillmeat -n "not __fish_seen_subcommand_from $commands" -a status -d 'Show deployment status'
complete -c skillmeat -n "not __fish_seen_subcommand_from $commands" -a show -d 'Show artifact details'
complete -c skillmeat -n "not __fish_seen_subcommand_from $commands" -a sync-check -d 'Check for upstream changes'
complete -c skillmeat -n "not __fish_seen_subcommand_from $commands" -a sync-pull -d 'Pull upstream changes'
complete -c skillmeat -n "not __fish_seen_subcommand_from $commands" -a sync-preview -d 'Preview sync changes'
complete -c skillmeat -n "not __fish_seen_subcommand_from $commands" -a diff -d 'Show differences with upstream'
complete -c skillmeat -n "not __fish_seen_subcommand_from $commands" -a bundle -d 'Manage artifact bundles'
complete -c skillmeat -n "not __fish_seen_subcommand_from $commands" -a config -d 'Manage configuration'
complete -c skillmeat -n "not __fish_seen_subcommand_from $commands" -a collection -d 'View or switch collection'
complete -c skillmeat -n "not __fish_seen_subcommand_from $commands" -a alias -d 'Manage claudectl alias'
complete -c skillmeat -n "not __fish_seen_subcommand_from $commands" -a init -d 'Initialize a new collection'

# quick-add options
complete -c claudectl -n "__fish_seen_subcommand_from quick-add" -s t -l type -xa 'skill command agent' -d 'Artifact type'
complete -c claudectl -n "__fish_seen_subcommand_from quick-add" -s c -l collection -d 'Collection name'
complete -c claudectl -n "__fish_seen_subcommand_from quick-add" -s n -l name -d 'Override name'
complete -c claudectl -n "__fish_seen_subcommand_from quick-add" -s f -l force -d 'Overwrite existing'
complete -c claudectl -n "__fish_seen_subcommand_from quick-add" -l format -xa 'table json' -d 'Output format'

# deploy options
complete -c claudectl -n "__fish_seen_subcommand_from deploy" -s c -l collection -d 'Collection name'
complete -c claudectl -n "__fish_seen_subcommand_from deploy" -s p -l project -xa '(__fish_complete_directories)' -d 'Project path'
complete -c claudectl -n "__fish_seen_subcommand_from deploy" -s t -l type -xa 'skill command agent' -d 'Artifact type'
complete -c claudectl -n "__fish_seen_subcommand_from deploy" -s o -l overwrite -d 'Overwrite existing'
complete -c claudectl -n "__fish_seen_subcommand_from deploy" -l format -xa 'table json' -d 'Output format'

# remove options
complete -c claudectl -n "__fish_seen_subcommand_from remove" -s t -l type -xa 'skill command agent' -d 'Artifact type'
complete -c claudectl -n "__fish_seen_subcommand_from remove" -s c -l collection -d 'Collection name'
complete -c claudectl -n "__fish_seen_subcommand_from remove" -l keep-files -d 'Keep artifact files'
complete -c claudectl -n "__fish_seen_subcommand_from remove" -s f -l force -d 'Skip confirmation'
complete -c claudectl -n "__fish_seen_subcommand_from remove" -l format -xa 'table json' -d 'Output format'

# undeploy options
complete -c claudectl -n "__fish_seen_subcommand_from undeploy" -s p -l project -xa '(__fish_complete_directories)' -d 'Project path'
complete -c claudectl -n "__fish_seen_subcommand_from undeploy" -s t -l type -xa 'skill command agent' -d 'Artifact type'
complete -c claudectl -n "__fish_seen_subcommand_from undeploy" -s f -l force -d 'Skip confirmation'
complete -c claudectl -n "__fish_seen_subcommand_from undeploy" -l format -xa 'table json' -d 'Output format'

# search options
complete -c claudectl -n "__fish_seen_subcommand_from search" -s t -l type -xa 'skill command agent' -d 'Artifact type'
complete -c claudectl -n "__fish_seen_subcommand_from search" -s l -l limit -d 'Max results'
complete -c claudectl -n "__fish_seen_subcommand_from search" -l format -xa 'table json' -d 'Output format'

# list options
complete -c claudectl -n "__fish_seen_subcommand_from list" -s t -l type -xa 'skill command agent' -d 'Artifact type'
complete -c claudectl -n "__fish_seen_subcommand_from list" -s c -l collection -d 'Collection name'
complete -c claudectl -n "__fish_seen_subcommand_from list" -l tags -d 'Show tags'
complete -c claudectl -n "__fish_seen_subcommand_from list" -l no-cache -d 'Bypass cache'
complete -c claudectl -n "__fish_seen_subcommand_from list" -l format -xa 'table json' -d 'Output format'

# config subcommands
complete -c claudectl -n "__fish_seen_subcommand_from config; and not __fish_seen_subcommand_from get set list" -a get -d 'Get config value'
complete -c claudectl -n "__fish_seen_subcommand_from config; and not __fish_seen_subcommand_from get set list" -a set -d 'Set config value'
complete -c claudectl -n "__fish_seen_subcommand_from config; and not __fish_seen_subcommand_from get set list" -a list -d 'List all config'

# config get/set keys
complete -c claudectl -n "__fish_seen_subcommand_from config; and __fish_seen_subcommand_from get set" -a 'github-token active-collection default-format' -d 'Config key'

# bundle subcommands
complete -c claudectl -n "__fish_seen_subcommand_from bundle; and not __fish_seen_subcommand_from create import inspect" -a create -d 'Create bundle from artifacts'
complete -c claudectl -n "__fish_seen_subcommand_from bundle; and not __fish_seen_subcommand_from create import inspect" -a import -d 'Import bundle'
complete -c claudectl -n "__fish_seen_subcommand_from bundle; and not __fish_seen_subcommand_from create import inspect" -a inspect -d 'Inspect bundle contents'

# alias subcommands
complete -c claudectl -n "__fish_seen_subcommand_from alias; and not __fish_seen_subcommand_from install uninstall" -a install -d 'Install claudectl wrapper'
complete -c claudectl -n "__fish_seen_subcommand_from alias; and not __fish_seen_subcommand_from install uninstall" -a uninstall -d 'Uninstall claudectl wrapper'

# alias install options
complete -c claudectl -n "__fish_seen_subcommand_from alias; and __fish_seen_subcommand_from install" -l shells -xa 'bash zsh fish' -d 'Shells to install for'
complete -c claudectl -n "__fish_seen_subcommand_from alias; and __fish_seen_subcommand_from install" -s f -l force -d 'Overwrite existing'
