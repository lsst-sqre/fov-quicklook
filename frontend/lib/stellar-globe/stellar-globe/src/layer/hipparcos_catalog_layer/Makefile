generate_parts:
	python ./split.py

upload: hipparcos-catalog
	rsync --delete -av ./hipparcos-catalog hscmap.mtk.nao.ac.jp:htdocs/stellar-globe/static
