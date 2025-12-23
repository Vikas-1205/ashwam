#!/bin/bash
python3 src/lang_detect.py --in_file texts.jsonl --out_file lang.jsonl
echo "Language detection complete. Output saved to lang.jsonl"
