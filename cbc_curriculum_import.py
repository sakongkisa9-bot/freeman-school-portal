import re


def _clean_cell(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def extract_curriculum_tables(tables):
    """Extract a curriculum area from tables with Strand and Sub Strand columns."""
    strands = []
    strand_lookup = {}
    for table in tables:
        if not table:
            continue
        header_index = None
        strand_column = None
        sub_strand_column = None
        for row_index, row in enumerate(table[:8]):
            headers = [_clean_cell(value).casefold() for value in row]
            for index, header in enumerate(headers):
                compact = re.sub(r"[^a-z]", "", header)
                if compact == "strands":
                    strand_column = index
                elif compact in {"substrand", "substrands"}:
                    sub_strand_column = index
            if strand_column is not None and sub_strand_column is not None:
                header_index = row_index
                break
            strand_column = None
            sub_strand_column = None
        if header_index is None:
            continue

        current_strand = ""
        for row in table[header_index + 1 :]:
            if max(strand_column, sub_strand_column) >= len(row):
                continue
            strand_name = _clean_cell(row[strand_column])
            sub_strand = _clean_cell(row[sub_strand_column])
            if strand_name:
                current_strand = strand_name
            if not current_strand or not sub_strand:
                continue
            key = current_strand.casefold()
            if key not in strand_lookup:
                strand_lookup[key] = {"name": current_strand, "sub_strands": []}
                strands.append(strand_lookup[key])
            sub_strand_names = strand_lookup[key]["sub_strands"]
            if sub_strand.casefold() not in {name.casefold() for name in sub_strand_names}:
                sub_strand_names.append(sub_strand)

    if not strands:
        raise ValueError(
            "No table with Strand and Sub Strand columns was found in this PDF."
        )
    return strands


def extract_curriculum_pdf(path):
    try:
        import pdfplumber
    except ImportError as error:
        raise RuntimeError(
            "PDF import requires pdfplumber. Install the project's PDF dependencies."
        ) from error

    tables = []
    with pdfplumber.open(path) as document:
        for page in document.pages:
            tables.extend(page.extract_tables() or [])
    return extract_curriculum_tables(tables)