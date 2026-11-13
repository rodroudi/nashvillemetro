#!/usr/bin/env bash
# One-time publish to GitHub Pages. Needs a working `gh auth status`.
set -euo pipefail
cd "$(dirname "$0")/.."
REPO=${REPO:-nashville-council-votes}
OWNER=$(gh api user -q .login)
[ -d .git ] || { git init -q -b main; }
touch .nojekyll
git add -A && git -c user.name="$OWNER" -c user.email="$OWNER@users.noreply.github.com" commit -qm "Publish council votes map" || true
gh repo view "$OWNER/$REPO" >/dev/null 2>&1 || gh repo create "$OWNER/$REPO" --private --description "Map of Metro Nashville Council districts and recorded roll-call votes" --source . --remote origin
git remote get-url origin >/dev/null 2>&1 || git remote add origin "https://github.com/$OWNER/$REPO.git"
git push -u origin main
echo "Plan: $(gh api user -q .plan.name 2>/dev/null)"; gh api -X POST "repos/$OWNER/$REPO/pages" -f "source[branch]=main" -f "source[path]=/" || echo PAGES_FAILED
URL="https://$OWNER.github.io/$REPO/"
for i in $(seq 1 40); do code=$(curl -s -o /dev/null -w "%{http_code}" "$URL"); [ "$code" = 200 ] && break; sleep 15; done
echo "Repo: https://github.com/$OWNER/$REPO"; echo "Live: $URL (HTTP $code)"
