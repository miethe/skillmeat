#!/bin/bash
# Validate Next.js build environment before building
# This prevents MODULE_NOT_FOUND errors from corrupted cache

set -e

echo "🔍 Validating Next.js build environment..."

# Check if .next exists
if [ -d ".next" ]; then
  echo "📦 Found existing .next directory"

  # Check if both dev and prod caches exist (problematic)
  if [ -d ".next/cache/webpack/client-development" ] && [ -d ".next/cache/webpack/client-production" ]; then
    echo "⚠️  WARNING: Both development and production caches detected!"
    echo "   This can cause MODULE_NOT_FOUND errors."
    echo "   Recommend running: pnpm clean"
    echo ""
    read -p "Clean .next directory now? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      echo "🧹 Cleaning .next directory..."
      rm -rf .next
      echo "✅ Cleaned successfully"
    else
      echo "⏭️  Continuing with existing cache (may cause issues)"
    fi
  fi

  # Check standalone build
  if [ -d ".next/standalone" ]; then
    echo "📦 Found standalone build"
    echo "   Standalone builds can have stale dependencies"
    echo ""
    read -p "Clean standalone build? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      echo "🧹 Cleaning standalone build..."
      rm -rf .next/standalone
      echo "✅ Cleaned successfully"
    fi
  fi
fi

# Check node_modules
if [ ! -d "node_modules" ]; then
  echo "⚠️  WARNING: node_modules not found!"
  echo "   Run: pnpm install"
  exit 1
fi

# Check pnpm lock file
if [ ! -f "pnpm-lock.yaml" ]; then
  echo "⚠️  WARNING: pnpm-lock.yaml not found!"
  echo "   Run: pnpm install"
  exit 1
fi

echo "✅ Build environment looks good!"
echo ""
