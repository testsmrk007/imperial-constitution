#!/bin/bash
export URL=$1
export BRANCH=$2
git pull $URL $BRANCH
git push origin main
touch main.py
source venv/bin/activate
python main.py &
