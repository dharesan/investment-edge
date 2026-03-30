import streamlit as st
import pdfplumber
import pandas as pd
import os
import re
from io import BytesIO

def find_balance_sheet_pages(pdf_path):
    """Find pages containing 'CONSOLIDATED BALANCE SHEETS'"""
    pages_found = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = (page.extract_text() or "").upper()
            if "CONSOLIDATED BALANCE SHEETS" in text or "BALANCE SHEET" in text:
                pages_found.append(i)
    return pages_found

def extract_tables_from_page(pdf_path, page_num):
    """Extract tables from a specific page with multiple strategies"""
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_num]
        
        all_tables = []
        
        # Strategy 1: Line-based (works best for structured tables)
        settings_lines = {
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
            "snap_tolerance": 5,
            "join_tolerance": 5,
            "edge_min_length": 3,
        }
        tables_lines = page.extract_tables(table_settings=settings_lines) or []
        all_tables.extend(tables_lines)
        
        # Strategy 2: Text-based (fallback for less structured PDFs)
        settings_text = {
            "vertical_strategy": "text",
            "horizontal_strategy": "text",
            "snap_tolerance": 3,
            "join_tolerance": 3,
            "intersection_tolerance": 3,
        }
        tables_text = page.extract_tables(table_settings=settings_text) or []
        all_tables.extend(tables_text)
        
        # Strategy 3: Explicit edges
        settings_explicit = {
            "vertical_strategy": "explicit",
            "horizontal_strategy": "explicit",
            "snap_tolerance": 3,
        }
        tables_explicit = page.extract_tables(table_settings=settings_explicit) or []
        all_tables.extend(tables_explicit)
        
        # Remove duplicates (tables that were found by multiple strategies)
        unique_tables = []
        for table in all_tables:
            if table and len(table) > 0:
                # Convert to tuple for hashability
                table_str = str(table)
                is_duplicate = False
                for existing in unique_tables:
                    if str(existing) == table_str:
                        is_duplicate = True
                        break
                if not is_duplicate:
                    unique_tables.append(table)
        
        return unique_tables

def clean_value(val):
    """Clean numeric or text values from extracted cells"""
    if val is None:
        return ""
    val = str(val).strip()
    return val

def process_balance_sheet_table(table_data):
    """Process raw table data into clean DataFrame"""
    if not table_data or len(table_data) < 2:
        return None
    
    # Clean all cells
    cleaned_table = []
    for row in table_data:
        cleaned_row = [clean_value(cell) for cell in row]
        # Keep rows with at least some content
        if any(cleaned_row):
            cleaned_table.append(cleaned_row)
    
    if len(cleaned_table) < 2:
        return None
    
    # Get headers and data
    headers = cleaned_table[0]
    data_rows = cleaned_table[1:]
    
    # Skip if headers are empty
    if not any(headers):
        return None
    
    # Ensure all rows have same length as headers
    max_cols = len(headers)
    padded_rows = []
    for row in data_rows:
        if len(row) < max_cols:
            row = row + [""] * (max_cols - len(row))
        else:
            row = row[:max_cols]
        padded_rows.append(row)
    
    # Create DataFrame
    df = pd.DataFrame(padded_rows, columns=headers)
    
    # Only keep tables with meaningful data (not all empty columns)
    non_empty_cols = 0
    for col in df.columns:
        if df[col].astype(str).str.strip().ne('').any():
            non_empty_cols += 1
    
    if non_empty_cols < 2:  # At least 2 non-empty columns
        return None
    
    return df

def extract_balance_sheets(pdf_path):
    """Extract all balance sheet tables from PDF"""
    results = []
    
    # Find balance sheet pages
    bs_pages = find_balance_sheet_pages(pdf_path)
    
    if not bs_pages:
        return results
    
    # Extract from each balance sheet page and the next page (tables may span)
    for page_num in bs_pages:
        for offset in range(2):  # Check current page and next page
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    if page_num + offset >= len(pdf.pages):
                        break
                
                tables = extract_tables_from_page(pdf_path, page_num + offset)
                
                for table in tables:
                    df = process_balance_sheet_table(table)
                    if df is not None and len(df) > 1:  # Only keep tables with 2+ data rows
                        df['page'] = page_num + offset + 1
                        df['source_file'] = os.path.basename(pdf_path)
                        results.append(df)
            except:
                continue
    
    return results

def save_to_excel(dataframes_dict, output_buffer):
    """Save all DataFrames to Excel with separate sheets"""
    with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
        for sheet_name, df in dataframes_dict.items():
            if not df.empty:
                df.to_excel(writer, sheet_name=sheet_name, index=False)

# Streamlit UI
st.set_page_config(page_title="Balance Sheet Extractor", layout="wide")
st.title("📊 Financial Balance Sheet Extractor")
st.markdown("Extract consolidated balance sheets from multi-page PDFs")

uploaded_files = st.file_uploader("Upload PDF files", type=['pdf'], accept_multiple_files=True)

if uploaded_files:
    if st.button("🔍 Extract Balance Sheets", key="extract_btn"):
        all_results = {}
        
        with st.spinner("Processing PDFs..."):
            for uploaded_file in uploaded_files:
                # Save temp file
                temp_path = f"/tmp/{uploaded_file.name}"
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getvalue())
                
                # Extract balance sheets
                tables = extract_balance_sheets(temp_path)
                
                if tables:
                    all_results[uploaded_file.name] = tables
                    st.success(f"✅ Found {len(tables)} table(s) in {uploaded_file.name}")
                else:
                    st.warning(f"⚠️ No balance sheet tables found in {uploaded_file.name}")
                
                # Cleanup
                os.remove(temp_path)
        
        # Display results
        if all_results:
            st.subheader("📋 Extracted Data")
            
            for filename, tables in all_results.items():
                st.markdown(f"**File: {filename}**")
                for i, df in enumerate(tables):
                    st.write(f"Table {i+1} (Page {df['page'].iloc[0]})")
                    st.dataframe(df, use_container_width=True)
            
            # Export button
            export_dict = {}
            sheet_num = 1
            for filename, tables in all_results.items():
                for i, df in enumerate(tables):
                    sheet_name = f"{filename.replace('.pdf', '')}_{i+1}"[:31]  # Max 31 chars
                    export_dict[sheet_name] = df
            
            output_buffer = BytesIO()
            save_to_excel(export_dict, output_buffer)
            output_buffer.seek(0)
            
            st.download_button(
                label="📥 Download Extracted Balance Sheets (Excel)",
                data=output_buffer.getvalue(),
                file_name="balance_sheets.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("No balance sheet tables found. Check PDF format or page structure.")