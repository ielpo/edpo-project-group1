#!/bin/sh

echo "Combining all ADRs into a single PDF..."

for file in *.md; do
    cat "$file" >> "combined.md"
    echo -e "\n" >> "combined.md"
done

pandoc combined.md -o adrs.pdf
rm "combined.md"
