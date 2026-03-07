#!/bin/bash

set -e

WDIR=$(pwd)

setup_alias() {
    local install_dir="$1"
    local shell_name=$(basename "$SHELL")
    local rc_file=""
    local alias_cmd="alias quickdash='$install_dir/quickdash.sh'"
    
    case "$shell_name" in
        bash)
            if [[ "$OSTYPE" == "darwin"* && -f "$HOME/.bash_profile" ]]; then
                rc_file="$HOME/.bash_profile" # macOS
            else
                rc_file="$HOME/.bashrc" # Linux (+UNIX)
            fi
            ;;
        zsh)
            rc_file="$HOME/.zshrc"
            ;;
        fish)
            alias_cmd="alias quickdash '$install_dir/quickdash.sh'"
            rc_file="$HOME/.config/fish/config.fish"
            mkdir -p "$HOME/.config/fish"
            ;;
        *)
            echo "Unknown shell: $shell_name"
            echo "Add this alias manually pls :"
            echo "$alias_cmd"
            return 1
            ;;
    esac

    if grep -q "alias quickdash=" "$rc_file" 2>/dev/null || \
       grep -q "alias quickdash " "$rc_file" 2>/dev/null; then
        echo "alias already in $rc_file"
    else
        echo "# QuickDash alias" >> "$rc_file"
        echo "$alias_cmd" >> "$rc_file"
        echo "Added alias to $rc_file"
    fi
    
    echo "Run 'source $rc_file' or restart your terminal to use the alias 'quickdash'"
}

echo "Install QuickDash in $WDIR ? [Y/n]"
read -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Installing ..."
    git clone https://github.com/khr519/QuickDash.git
    cd QuickDash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

    echo "Do you want to create an alias for quickdash ? [Y/n]"
    read -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        setup_alias "$WDIR/QuickDash"
    fi
    
    echo "Installation complete!"
    cat greeter.txt
else
    echo "Installation cancelled."
fi