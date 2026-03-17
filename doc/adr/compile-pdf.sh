#!/bin/sh

echo "Combining all ADRs into a single PDF..."
cat *.md > combined.md
pandoc combined.md -o adrs.pdf
rm "combined.md"
