import streamlit as st
import yaml
import anthropic
import datetime
from docx import Document
import os
import fitz  # PyMuPDF for PDF parsing
import pandas as pd
import io
from pathlib import Path

# -------------- CONFIG ----------------
ANTHROPIC_KEY = st.secrets["api_keys"]["anthropic_api_key"]
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

def load_client_config(client_name):
    with open(f"clients/{client_name}.yaml", "r") as file:
        return yaml.safe_load(file)

# -------------- FILE PROCESSING ----------------
def process_uploaded_file(uploaded_file):
    """Process uploaded file and extract text content"""
    if uploaded_file is None:
        return ""
    
    file_extension = uploaded_file.name.split('.')[-1].lower()
    
    try:
        if file_extension == 'pdf':
            # Process PDF
            pdf_document = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            text = ""
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                text += page.get_text()
            pdf_document.close()
            return text
        
        elif file_extension == 'docx':
            # Process DOCX
            doc = Document(uploaded_file)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        
        elif file_extension == 'txt':
            # Process TXT
            return str(uploaded_file.read(), "utf-8")
        
        elif file_extension in ['csv', 'xlsx', 'xls']:
            # Process spreadsheet files
            if file_extension == 'csv':
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            # Convert DataFrame to text summary
            text = f"Data Summary:\n"
            text += f"Shape: {df.shape[0]} rows, {df.shape[1]} columns\n"
            text += f"Columns: {', '.join(df.columns.tolist())}\n\n"
            text += "Sample Data:\n"
            text += df.head().to_string()
            
            # Add basic statistics for numeric columns
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                text += "\n\nNumeric Statistics:\n"
                text += df[numeric_cols].describe().to_string()
            
            return text
        
        else:
            st.error(f"Unsupported file type: {file_extension}")
            return ""
    
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return ""

# -------------- STREAMLIT UI ----------------
st.set_page_config(
    page_title="AI Blog Writer Pro", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional CSS styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
        padding: 2.5rem 2rem;
        border-radius: 8px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 2.8rem;
        font-weight: 300;
        letter-spacing: -1px;
    }
    
    .main-header p {
        margin: 1rem 0 0 0;
        font-size: 1.1rem;
        opacity: 0.85;
        font-weight: 300;
    }
    
    .section-header {
        background: #f8f9fa;
        padding: 1.2rem 1.5rem;
        border-radius: 6px;
        border-left: 4px solid #3498db;
        margin: 1.5rem 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    .section-header h3 {
        margin: 0;
        color: #2c3e50;
        font-weight: 500;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.8rem 2.5rem;
        font-weight: 500;
        font-size: 1rem;
        transition: all 0.2s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #2980b9 0%, #3498db 100%);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    .success-message {
        background: #d4edda;
        color: #155724;
        padding: 1.5rem;
        border-radius: 6px;
        border: 1px solid #c3e6cb;
        margin: 1.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .success-message h4 {
        margin-top: 0;
        font-weight: 500;
    }
    
    .metric-container {
        background: white;
        padding: 1.5rem;
        border-radius: 6px;
        border: 1px solid #e1e8ed;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    .professional-info {
        background: #f8f9fa;
        padding: 1rem 1.5rem;
        border-radius: 6px;
        border-left: 3px solid #17a2b8;
        margin: 1rem 0;
    }
    
    .sidebar-section {
        background: white;
        padding: 1rem;
        border-radius: 6px;
        margin-bottom: 1rem;
        border: 1px solid #e1e8ed;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>AI Blog Writer Pro</h1>
    <p>Advanced AI-powered content creation with document analysis</p>
</div>
""", unsafe_allow_html=True)

# Sidebar for configuration
with st.sidebar:
    st.markdown("### Configuration")
    
    # Client selection
    client_name = st.selectbox(
        "Client Profile",
        ["marketing_junction"],
        help="Select the client configuration profile"
    )
    
    # Language versions
    st.markdown("### Language Versions")
    generate_uk = st.checkbox("Generate UK English Version", value=True)
    generate_us = st.checkbox("Generate US English Version", value=True)
    
    # SEO Settings
    st.markdown("### SEO Settings")
    ai_friendly = st.checkbox(
        "AI-Friendly Formatting (AEO Optimized)",
        help="Format content for AI search engines with Q&A structure"
    )
    
    extra_keywords = st.text_input(
        "Additional Keywords",
        placeholder="keyword1, keyword2, keyword3",
        help="Comma-separated keywords to include"
    )
    
    # Export options
    st.markdown("### Export Options")
    export_format = st.selectbox(
        "Export Format",
        ["DOCX", "PDF", "Both"],
        help="Choose export format for generated content"
    )

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown('<div class="section-header"><h3>Blog Content Setup</h3></div>', unsafe_allow_html=True)
    
    with st.form("blog_form"):
        # Blog title
        blog_title = st.text_input(
            "Blog Title",
            placeholder="Enter your compelling blog topic here...",
            help="This will be the main title of your blog post"
        )
        
        # Content inputs
        st.markdown("### Content Inputs")
        
        content_col1, content_col2 = st.columns(2)
        
        with content_col1:
            pasted_facts = st.text_area(
                "Key Facts & Figures",
                height=120,
                placeholder="• Statistical data\n• Research findings\n• Important facts",
                help="Add relevant facts and statistics to include in your blog"
            )
        
        with content_col2:
            pasted_quotes = st.text_area(
                "Quotes & Original Thoughts",
                height=120,
                placeholder="• Expert quotes\n• Industry insights\n• Original perspectives",
                help="Add quotes and unique insights to enhance your content"
            )
        
        # File upload section
        st.markdown("### Supporting Documents")
        uploaded_file = st.file_uploader(
            "Upload Supporting Document",
            type=['pdf', 'docx', 'txt', 'csv', 'xlsx', 'xls'],
            help="Upload a document that Claude will analyze and use as supporting material"
        )
        
        if uploaded_file:
            st.success(f"File uploaded: {uploaded_file.name}")
            file_size = len(uploaded_file.getvalue()) / 1024  # KB
            st.info(f"File size: {file_size:.1f} KB")
        
        # Submit button
        submitted = st.form_submit_button("Generate Blog Articles", use_container_width=True)

with col2:
    st.markdown('<div class="section-header"><h3>Generation Settings</h3></div>', unsafe_allow_html=True)
    
    # Preview settings
    st.markdown("### Preview Settings")
    show_analysis = st.checkbox("Show Document Analysis", value=True)
    show_word_count = st.checkbox("Show Word Count", value=True)
    show_keywords = st.checkbox("Show Keywords Used", value=True)
    
    # Generation metrics (placeholder)
    if 'generation_stats' not in st.session_state:
        st.session_state.generation_stats = {
            'total_blogs': 0,
            'total_words': 0,
            'files_processed': 0
        }
    
    st.markdown("### Session Statistics")
    stats_col1, stats_col2 = st.columns(2)
    
    with stats_col1:
        st.metric("Blogs Generated", st.session_state.generation_stats['total_blogs'])
        st.metric("Files Processed", st.session_state.generation_stats['files_processed'])
    
    with stats_col2:
        st.metric("Total Words", st.session_state.generation_stats['total_words'])
        st.metric("Avg Words/Blog", 
                 st.session_state.generation_stats['total_words'] // max(1, st.session_state.generation_stats['total_blogs']))

# -------------- CLAUDE PROMPT HELPER ----------------
def generate_prompt(title, facts, quotes, ai_opt, client_cfg, custom_keywords="", document_content="", language="UK"):
    base_keywords = client_cfg.get("keywords", [])
    if custom_keywords:
        additional_keywords = [kw.strip().lower() for kw in custom_keywords.split(",") if kw.strip()]
        # Convert base keywords to lowercase for comparison
        base_keywords_lower = [kw.lower() for kw in base_keywords]
        # Only add keywords that aren't already in the base list
        for kw in additional_keywords:
            if kw not in base_keywords_lower:
                base_keywords.append(kw)
    keywords = ", ".join(base_keywords)
    
    language_instruction = "UK English" if language == "UK" else "US English"
    spelling_note = "(use British spelling, 's' instead of 'z' in words like 'organisation')" if language == "UK" else "(use American spelling, 'z' instead of 's' in words like 'organization')"
    
    prompt = f'''
Write a comprehensive blog article in {language_instruction} {spelling_note} about: "{title}"

Audience: knowledgeable professionals in the industry.
Tone: {client_cfg.get("tone", "informative and engaging")}.
Perspective: Professional recruitment agency (don't mention this explicitly).
Avoid: Em/En dashes, clichéd phrases like 'in the world of', generic conclusions.

DOCUMENT ANALYSIS:
{f"Supporting Document Content: {document_content}" if document_content else "No supporting document provided."}

Please analyze the supporting document (if provided) and extract relevant insights, statistics, and information that can enhance the blog article. Use this information naturally throughout the content.

CONTENT REQUIREMENTS:
- Include SEO-friendly headings and subheadings
- Use proper {language_instruction} grammar and spelling
- Structure: Introduction, 3-4 main sections, conclusion
- Word count: 800-1200 words
- Keywords to naturally incorporate: {keywords}
- Key facts to include: {facts}
- Quotes to incorporate: {quotes}

{'AI-FRIENDLY FORMATTING: Use H2 headings as questions, provide brief answers first, then elaborate with detailed explanations.' if ai_opt else 'Use traditional blog formatting with descriptive headings.'}

IMPORTANT GUIDELINES:
- Do not invent statistics or fake data
- You may create realistic quotes but not fabricate specific events
- If using document content, cite it as "according to recent research" or "industry data shows"
- Make the content engaging and actionable for professionals
- Include practical insights and takeaways

Please generate a well-structured, informative blog article that incorporates all provided information naturally and professionally.
'''
    return prompt, base_keywords

# -------------- ARTICLE GENERATION ----------------
def call_claude(prompt):
    try:
        response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        st.error(f"Error calling Claude API: {str(e)}")
        return None

# -------------- EXPORT TO DOCX ----------------
def export_docx(title, article_uk, article_us, keywords, document_analysis=""):
    # Create UK version
    doc_uk = Document()
    doc_uk.add_heading(f"{title} (UK English)", 0)
    doc_uk.add_paragraph(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    doc_uk.add_paragraph(f"Word Count: {len(article_uk.split())}")
    doc_uk.add_paragraph(f"Keywords Used: {', '.join(keywords)}")
    doc_uk.add_paragraph(f"Language: UK English")
    if document_analysis:
        doc_uk.add_paragraph(f"Document Analysis: Yes")
    doc_uk.add_paragraph("")
    doc_uk.add_paragraph(article_uk)
    
    # Create US version
    doc_us = Document()
    doc_us.add_heading(f"{title} (US English)", 0)
    doc_us.add_paragraph(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    doc_us.add_paragraph(f"Word Count: {len(article_us.split())}")
    doc_us.add_paragraph(f"Keywords Used: {', '.join(keywords)}")
    doc_us.add_paragraph(f"Language: US English")
    if document_analysis:
        doc_us.add_paragraph(f"Document Analysis: Yes")
    doc_us.add_paragraph("")
    doc_us.add_paragraph(article_us)
    
    # Save files
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
    safe_title = safe_title.replace(' ', '_')
    
    os.makedirs("exports", exist_ok=True)
    filename_uk = f"exports/{safe_title}_UK_{timestamp}.docx"
    filename_us = f"exports/{safe_title}_US_{timestamp}.docx"
    
    doc_uk.save(filename_uk)
    doc_us.save(filename_us)
    
    return filename_uk, filename_us

# -------------- MAIN EXECUTION ----------------
if submitted and blog_title:
    if not (generate_uk or generate_us):
        st.error("Please select at least one language version to generate.")
    else:
        client_cfg = load_client_config(client_name)
        
        # Process uploaded file
        document_content = ""
        if uploaded_file:
            with st.spinner("Analyzing uploaded document..."):
                document_content = process_uploaded_file(uploaded_file)
                st.session_state.generation_stats['files_processed'] += 1
        
        # Show document analysis if requested
        if show_analysis and document_content:
            st.markdown("### Document Analysis")
            with st.expander("View Document Content Summary", expanded=False):
                st.text_area("Extracted Content", document_content[:1000] + "..." if len(document_content) > 1000 else document_content, height=200)
        
        articles = {}
        
        # Generate UK version
        if generate_uk:
            with st.spinner("Generating UK English version..."):
                full_prompt, all_keywords = generate_prompt(
                    blog_title, pasted_facts, pasted_quotes, ai_friendly, 
                    client_cfg, extra_keywords, document_content, "UK"
                )
                article_uk = call_claude(full_prompt)
                if article_uk:
                    articles['UK'] = article_uk
        
        # Generate US version
        if generate_us:
            with st.spinner("Generating US English version..."):
                full_prompt, all_keywords = generate_prompt(
                    blog_title, pasted_facts, pasted_quotes, ai_friendly, 
                    client_cfg, extra_keywords, document_content, "US"
                )
                article_us = call_claude(full_prompt)
                if article_us:
                    articles['US'] = article_us
        
        if articles:
            # Update stats
            st.session_state.generation_stats['total_blogs'] += len(articles)
            total_words = sum(len(article.split()) for article in articles.values())
            st.session_state.generation_stats['total_words'] += total_words
            
            # Export files
            if len(articles) == 2:
                filename_uk, filename_us = export_docx(blog_title, articles['UK'], articles['US'], all_keywords, document_content)
            elif 'UK' in articles:
                filename_uk, _ = export_docx(blog_title, articles['UK'], "", all_keywords, document_content)
            else:
                _, filename_us = export_docx(blog_title, "", articles['US'], all_keywords, document_content)
            
            # Success message
            st.markdown("""
            <div class="success-message">
                <h4>Blog articles generated successfully!</h4>
                <p>Your content has been created and is ready for download.</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Download buttons
            st.markdown("### Download Options")
            download_col1, download_col2 = st.columns(2)
            
            with download_col1:
                if 'UK' in articles:
                    st.download_button(
                        "Download UK Version",
                        data=open(filename_uk, "rb").read(),
                        file_name=os.path.basename(filename_uk),
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
            
            with download_col2:
                if 'US' in articles:
                    st.download_button(
                        "Download US Version",
                        data=open(filename_us, "rb").read(),
                        file_name=os.path.basename(filename_us),
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
            
            # Preview sections
            st.markdown("---")
            st.markdown("### Article Preview")
            
            # Create tabs for different versions
            if len(articles) == 2:
                tab1, tab2 = st.tabs(["UK English", "US English"])
                
                with tab1:
                    if show_word_count:
                        st.info(f"Word Count: {len(articles['UK'].split())} words")
                    if show_keywords:
                        st.info(f"Keywords: {', '.join(all_keywords)}")
                    st.markdown(articles['UK'])
                
                with tab2:
                    if show_word_count:
                        st.info(f"Word Count: {len(articles['US'].split())} words")
                    if show_keywords:
                        st.info(f"Keywords: {', '.join(all_keywords)}")
                    st.markdown(articles['US'])
            
            elif 'UK' in articles:
                if show_word_count:
                    st.info(f"Word Count: {len(articles['UK'].split())} words")
                if show_keywords:
                    st.info(f"Keywords: {', '.join(all_keywords)}")
                st.markdown(articles['UK'])
            
            else:
                if show_word_count:
                    st.info(f"Word Count: {len(articles['US'].split())} words")
                if show_keywords:
                    st.info(f"Keywords: {', '.join(all_keywords)}")
                st.markdown(articles['US'])
        
        else:
            st.error("Failed to generate articles. Please try again.")

elif submitted:
    st.warning("Please enter a blog title before generating articles.")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 2rem; color: #6c757d; font-size: 0.9rem;">
    <p>Powered by Claude AI | Enhanced Blog Writer Pro | Built with Streamlit</p>
</div>
""", unsafe_allow_html=True)