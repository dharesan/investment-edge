import streamlit as st
import pdfplumber
import pandas as pd
import os
import glob
from pathlib import Path
import io

# Statement keywords (tuned for TSMC-like PDFs)
STATEMENT_KEYWORDS = {
    'balance_sheet': ['ASSETS', 'CURRENT ASSETS', 'NONCURRENT ASSETS', 'LIABILITIES', 'EQUITY', 'TOTAL ASSETS'],
    'income_statement': ['NET REVENUE', 'COST OF REVENUE', 'GROSS PROFIT', 'OPERATING EXPENSES', 'INCOME FROM OPERATIONS', 'NET INCOME'],
    'cash_flow': ['CASH FLOWS FROM OPERATING ACTIVITIES', 'CASH FLOWS FROM INVESTING ACTIVITIES', 'CASH FLOWS FROM FINANCING ACTIVITIES'],
    'notes_and_disclosures': ['RELATED PARTY', 'COUNTERPARTY', 'INTERCOMPANY', 'CONSOLIDATION', 'CONTINGENT', 'COMMITMENTS']
}

def clean_column_names(columns):
    """Clean and deduplicate column names, replacing None with unique names."""
    cleaned = []
    none_counter = 0
    col_counts = {}
    
    for col in columns:
        if col is None or (isinstance(col, str) and col.strip() == ''):
            cleaned.append(f'Column_{none_counter}')
            none_counter += 1
        else:
            # Handle duplicate non-None column names
            col_str = str(col).strip()
            if col_str in col_counts:
                col_counts[col_str] += 1
                cleaned.append(f'{col_str}_{col_counts[col_str]}')
            else:
                col_counts[col_str] = 0
                cleaned.append(col_str)
    
    return cleaned

def extract_tables_from_pdf(pdf_path):
    """Extract all tables from PDF using pdfplumber."""
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_tables = page.extract_tables()
            for table in page_tables or []:
                if table and len(table) > 1:  # Skip empty/single-row
                    clean_cols = clean_column_names(table[0])
                    df = pd.DataFrame(table[1:], columns=clean_cols)
                    df['page'] = i + 1
                    tables.append(df)
    return tables

def classify_table(df, pdf_text):
    """Classify table into statement types based on column headers and content keywords."""
    # Convert column headers to uppercase for matching
    headers = ' '.join(df.columns).upper()
    
    # Check column headers first (most reliable indicator)
    # Related party/disclosures - highest priority
    if any(kw in headers for kw in ['COUNTERPARTY', 'RELATED PARTY', 'INTERCOMPANY', 'NATURE OF RELATIONSHIP']):
        return 'notes_and_disclosures'
    
    # Income statement indicators
    if any(kw in headers for kw in ['NET REVENUE', 'COST OF REVENUE', 'GROSS PROFIT', 'OPERATING INCOME', 'NET INCOME']):
        return 'income_statement'
    
    # Cash flow indicators
    if any(kw in headers for kw in ['OPERATING ACTIVITIES', 'INVESTING ACTIVITIES', 'FINANCING ACTIVITIES']):
        return 'cash_flow'
    
    # Balance sheet indicators
    if any(kw in headers for kw in ['ASSETS', 'LIABILITIES', 'EQUITY', 'CURRENT']):
        return 'balance_sheet'
    
    # Fall back to content-based classification
    text = ' '.join(df.astype(str).values.flatten()).upper()
    
    for stmt, keywords in STATEMENT_KEYWORDS.items():
        if sum(text.count(kw) for kw in keywords) >= 2:  # Require at least 2 keyword matches
            return stmt
    
    return 'other'

def process_pdf(pdf_path):
    """Process single PDF: extract + classify tables."""
    tables = extract_tables_from_pdf(pdf_path)
    results = {'balance_sheet': [], 'income_statement': [], 'cash_flow': [], 'notes_and_disclosures': []}
    
    # Get PDF text for better classification
    with pdfplumber.open(pdf_path) as pdf:
        pdf_text = ' '.join(page.extract_text() or '' for page in pdf.pages).upper()
    
    for df in tables:
        stmt = classify_table(df, pdf_text)
        if stmt in results:
            results[stmt].append(df)
    
    return results

def save_to_excel(results, output_path):
    """Save classified tables to Excel with separate sheets."""
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for stmt, tables in results.items():
            if tables:
                combined = pd.concat(tables, ignore_index=True)
                combined.to_excel(writer, sheet_name=stmt.replace('_', ' ').title(), index=False)
            else:
                pd.DataFrame({'No tables found': ['Check PDF format']}).to_excel(writer, sheet_name=stmt.replace('_', ' ').title(), index=False)

# Streamlit GUI
st.title("🚀 PDF Financial Extractor")
st.markdown("**Drag PDF folders/files** → Extract Balance Sheet, Income Statement, Cash Flow → **Excel output**")

# File uploader with drag-drop
uploaded_files = st.file_uploader("Drop PDFs here", type=['pdf'], accept_multiple_files=True)

if uploaded_files:
    folder_path = st.text_input("Or enter folder path (optional)")
    
    if st.button("🔥 Extract Financial Statements"):
        all_results = {}
        processed_count = 0
        
        # Process uploaded files
        for uploaded_file in uploaded_files:
            with open(uploaded_file.name, "wb") as f:
                f.write(uploaded_file.getbuffer())
            results = process_pdf(uploaded_file.name)
            all_results[uploaded_file.name] = results
            processed_count += 1
        
        # Process folder if provided
        if folder_path:
            pdf_paths = glob.glob(os.path.join(folder_path, "*.pdf"))
            for pdf_path in pdf_paths:
                filename = os.path.basename(pdf_path)
                results = process_pdf(pdf_path)
                all_results[filename] = results
                processed_count += 1
        
        st.success(f"✅ Processed {processed_count} PDFs")
        
        # Combine all results
        combined_results = {'balance_sheet': [], 'income_statement': [], 'cash_flow': [], 'notes_and_disclosures': []}
        for filename, results in all_results.items():
            for stmt, tables in results.items():
                for df in tables:
                    df['source_file'] = filename  # Track source
                    if stmt in combined_results:
                        combined_results[stmt].extend([df])
        
        # Save to Excel
        output_buffer = io.BytesIO()
        save_to_excel(combined_results, output_buffer)
        output_buffer.seek(0)
        
        st.download_button(
            label="📥 Download financial_statements.xlsx",
            data=output_buffer.getvalue(),
            file_name="financial_statements.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        # Preview first few tables
        st.subheader("📊 Preview")
        for stmt, tables in combined_results.items():
            if tables:
                st.write(f"**{stmt.replace('_', ' ').title()}** ({len(tables)} tables)")
                st.dataframe(tables[0].head(10), width='stretch')

else:
    st.info("👆 Drag PDFs or folders onto the upload area above")