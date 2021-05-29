#!/bin/bash
git fetch
git merge --ff-only origin/$1
git push
touch main.py
source venv/bin/activate
python main.py
