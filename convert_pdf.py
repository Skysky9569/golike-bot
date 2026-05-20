# -*- coding: utf-8 -*-
import sys
import io
import shutil

# Fix console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Copy file với Unicode path sang tên ASCII
shutil.copy2(
    "Đáp-án-kiểm-tra-cuối-kỳ-II-lớp-10-NH-2025.pdf",
    "test.pdf"
)
print("Done copied to test.pdf", file=sys.stderr)