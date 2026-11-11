#!/bin/sh
# Builds the arXiv upload for the technical paper: the source and the files it
# reads, with the plain-language companion as an ancillary file, in
# paper/arxiv/seed-growth-arxiv.tar.gz. Run from the repository root.
set -e
out=paper/arxiv
rm -rf "$out" && mkdir -p "$out/src/anc"
cp paper/seed-growth.tex paper/table-*.tex paper/fig-seed-life.png paper/fig-seed-growth.png "$out/src/"
cp paper/seed-growth-plain.pdf "$out/src/anc/"
tar -czf "$out/seed-growth-arxiv.tar.gz" -C "$out/src" .
tar -tzf "$out/seed-growth-arxiv.tar.gz"
