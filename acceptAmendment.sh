#!/bin/bash
git fetch
git merge origin/$1
git push
touch main.py
