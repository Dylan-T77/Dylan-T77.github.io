.PHONY: build dev clean

PORT ?= 8080

build:
	python3 scripts/build_site.py

dev: build
	@echo "The Tech Briefing — local preview at http://localhost:$(PORT)"
	python3 -m http.server $(PORT)

clean:
	find css js -type f -regextype posix-extended -regex '.*/[^/]+\.[0-9a-f]{8}\.(css|js)$$' -delete 2>/dev/null || true
	rm -f data/asset-manifest.json
