#!/bin/sh

echo "Combining all ADRs into a single PDF..."

# Clear file
> combined.md
first_file=1

for file in *.md; do
    [ "$file" = "combined.md" ] && continue

    if [ "$first_file" -eq 0 ]; then
        printf '\n\n\\newpage\n\n' >> "combined.md"
    fi

    cat "$file" >> "combined.md"
    first_file=0
done

pandoc combined.md -V geometry:a4paper --pdf-engine=tectonic -o adrs.pdf
rm combined.md
