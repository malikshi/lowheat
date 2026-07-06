#!/bin/bash
#
# install.sh — Idempotent installer for the CodeDNA git hooks in this repo.
# Symlinks each canonical hook under tools/hooks/ into .git/hooks/ so the
# local clone benefits from the same checks as the canonical repo.
#
# Usage: bash tools/hooks/install.sh [--uninstall]

set -eu

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_DIR="$REPO_ROOT/tools/hooks"
GIT_HOOKS_DIR="$REPO_ROOT/.git/hooks"

# Only install files whose name matches a standard git hook. Excludes
# install.sh and any other non-hook files in the directory.
STANDARD_HOOKS="applypatch-msg commit-msg fsmonitor-watchman post-update pre-applypatch pre-commit pre-commit-msg pre-push pre-rebase pre-receive prepare-commit-msg push update"

if [[ "${1:-}" == "--uninstall" ]]; then
  for hook in "$HOOKS_DIR"/*; do
    name="$(basename "$hook")"
    case " $STANDARD_HOOKS " in
      *" $name "*) ;;
      *) continue ;;
    esac
    target="$GIT_HOOKS_DIR/$name"
    if [[ -L "$target" ]] && [[ "$(readlink "$target")" == "$hook" ]]; then
      rm -f "$target"
      echo "Uninstalled hook: $name"
    fi
  done
  exit 0
fi

mkdir -p "$GIT_HOOKS_DIR"

for hook in "$HOOKS_DIR"/*; do
  [[ -f "$hook" ]] || continue
  name="$(basename "$hook")"
  case " $STANDARD_HOOKS " in
    *" $name "*) ;;
    *) continue ;;
  esac

  target="$GIT_HOOKS_DIR/$name"

  if [[ -e "$target" ]] && [[ ! -L "$target" ]]; then
    echo "WARN: $target exists and is not a symlink; skipping (move it aside first if you want to install)." >&2
    continue
  fi

  if [[ -L "$target" ]] && [[ "$(readlink "$target")" == "$hook" ]]; then
    echo "Already installed: $name"
    continue
  fi

  ln -sf "$hook" "$target"
  echo "Installed hook: $name -> $hook"
done

