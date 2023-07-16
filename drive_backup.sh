#!/bin/bash

# Function to prompt for confirmation
confirm() {
    read -p "$1 [y/N]: " response
    case "$response" in
        [yY][eE][sS]|[yY])
            true
            ;;
        *)
            false
            ;;
    esac
}

if confirm "Are you sure you want to perform rsync for primary drive?"; then
    rsync -arv --size-only --delete /media/swap/primary/ /media/swap/backup
    echo "Rsync for primary drive complete."
else
    echo "Rsync for primary drive cancelled."
fi
