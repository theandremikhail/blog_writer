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
import json
import re

# -------------- CONFIG ----------------
ANTHROPIC_KEY = st.secrets["api_keys"]["anthropic_api_key"]
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

def load_client_config(client_name):
    with open(f"clients/{client_name}.yaml", "r") as file:
        return yaml.safe_load(file)

# -------------- HISTORY MANAGEMENT ----------------
def save_to_history(title, articles, keywords, timestamp):
    """Save generated blog to history"""
    if 'blog_history' not in st.session_state:
        st.session_state.blog_history = []
    
    history_entry = {
        'timestamp': timestamp,
        'title': title,
        'articles': articles,
        'keywords': keywords,
        'id': len(st.session_state.blog_history)
    }
    
    st.session_state.blog_history.insert(0, history_entry)  # Add to beginning
    
    # Keep only last 10 entries
    if len(st.session_state.blog_history) > 10:
        st.session_state.blog_history = st.session_state.blog_history[:10]

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
    page_title="AIvan, The Marketing Junction", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'blog_history' not in st.session_state:
    st.session_state.blog_history = []
if 'current_articles' not in st.session_state:
    st.session_state.current_articles = {}
if 'editing_mode' not in st.session_state:
    st.session_state.editing_mode = False

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
    
    .history-item {
        background: #f8f9fa;
        padding: 0.8rem;
        margin: 0.5rem 0;
        border-radius: 4px;
        border-left: 3px solid #6c757d;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .history-item:hover {
        background: #e9ecef;
        border-left-color: #3498db;
    }
    
    .edit-section {
        background: #fff3cd;
        padding: 1.5rem;
        border-radius: 6px;
        border: 1px solid #ffeaa7;
        margin: 1.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>Hi, I am "AI-van"!</h1>
    <p>The Marketing Junction's advanced AI-powered blog writing tool based on the human inputs and approaches of Evan.</p>
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
    generate_uk = st.checkbox("Generate UK English Version", value=False)
    generate_us = st.checkbox("Generate US English Version", value=False)
    
    # SEO Settings
    st.markdown("### SEO Settings")
    
    # Specific Keywords moved up
    extra_keywords = st.text_input(
        "Any specific Keywords",
        placeholder="keyword1, keyword2, keyword3",
        help="Comma-separated keywords to include"
    )
    
    ai_friendly = st.checkbox(
        "AI-Friendly Formatting (AEO Optimized)",
        help="Format content for AI search engines with Q&A structure"
    )
    
    # Word count setting
    st.markdown("### Content Settings")
    word_count_range = st.text_input(
        "Word Count Range",
        value="750-1500",
        help="Enter desired word count range (e.g., 750-1500)"
    )
    
    # Hiring impact section
    include_hiring_section = st.checkbox(
        "Include section on impact on hiring?",
        value=False,
        help="Add a dedicated section discussing how this topic affects recruitment and talent acquisition"
    )
    
    # Export options
    st.markdown("### Export Options")
    export_format = st.selectbox(
        "Export Format",
        ["DOCX", "PDF", "Both"],
        help="Choose export format for generated content"
    )
    
    # Blog History
    st.markdown("### Blog History")
    if st.session_state.blog_history:
        st.markdown("<small>Click to view previous blogs:</small>", unsafe_allow_html=True)
        for entry in st.session_state.blog_history[:5]:  # Show last 5
            if st.button(f"📄 {entry['title'][:30]}...", key=f"history_{entry['id']}"):
                st.session_state.current_articles = entry['articles']
                st.session_state.loaded_from_history = True
                st.rerun()
    else:
        st.info("No history yet. Generate your first blog!")

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
def generate_prompt(title, facts, quotes, ai_opt, client_cfg, custom_keywords="", document_content="", language="UK", word_range="750-1500", include_hiring_impact=False):
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
    
    # Parse word range
    try:
        min_words, max_words = map(int, word_range.split('-'))
    except:
        min_words, max_words = 750, 1500
    
    hiring_impact_section = ""
    if include_hiring_impact:
        hiring_impact_section = """
REQUIRED SECTION - Impact on Hiring:
You MUST include a dedicated section titled "**The Impact on Hiring**" or "**How This Affects Recruitment**" that discusses:
- How the topic relates to talent acquisition and recruitment
- What it means for hiring managers and HR professionals
- How it might change recruitment strategies or candidate expectations
- The implications for employer branding and talent attraction
- Specific recruitment challenges or opportunities this creates
This section alone should be at least 200-300 words.
"""
    
    prompt = f'''
CRITICAL INSTRUCTION: This article MUST be between {min_words} and {max_words} words. You are writing for a professional blog that requires substantial, in-depth content. Short articles are not acceptable.

Write a comprehensive, in-depth, and sophisticated blog article in {language_instruction} {spelling_note} about: "{title}"

WORD COUNT ENFORCEMENT:
- The TOTAL article must be {min_words}-{max_words} words
- This is MANDATORY - do not write less than {min_words} words
- Each main section should be 200-400 words minimum
- The introduction should be 150-200 words
- The final section should be 200-300 words
- If you're below {min_words} words, expand sections with more examples, analysis, and detail

Audience: knowledgeable professionals in the industry.
Tone: {client_cfg.get("tone", "informative and engaging")}.
Perspective: Professional recruitment agency (don't mention this explicitly).
Avoid: Em/En dashes, clichéd phrases like 'in the world of', generic conclusions.

QUALITY AND LENGTH REQUIREMENTS:
- Write with sophistication and depth - this is for a professional audience
- Each paragraph should be 3-5 sentences minimum
- Include detailed analysis, not just surface-level observations
- Provide specific examples, case studies, or scenarios in EVERY section
- Explore multiple angles and perspectives on the topic
- Include statistics, data points, or research findings where relevant
- Discuss implications, consequences, and future considerations
- Add context, background, and thorough explanations
- Include actionable insights and practical applications
- Use varied sentence structures and rich vocabulary
- DO NOT write brief overviews - write comprehensive explorations

FORMATTING REQUIREMENTS:
- All headings and subheadings MUST be in bold using **text** markdown formatting
- Main headings should be: **## Heading Text**
- Subheadings should be: **### Subheading Text**

STRUCTURE REQUIREMENTS:
1. Introduction (150-200 words): Set context, explain importance, preview main points
2. First main section (250-400 words): Deep dive into primary aspect
3. Second main section (250-400 words): Explore secondary considerations
4. Third main section (250-400 words): Analyze implications or applications
{f"5. Hiring Impact section (200-300 words): As specified below" if include_hiring_impact else ""}
{f"{5 if include_hiring_impact else 4}." if include_hiring_impact else "4."} Final forward-looking section (200-300 words): Future outlook and actionable takeaways

CRITICAL INSTRUCTION: DO NOT end the article with a section called "Conclusion" or "In Summary". End with an engaging final section with a creative title like "**The Path Forward**", "**Embracing Tomorrow's Opportunities**", "**Your Next Strategic Move**", "**Building on These Foundations**", etc.

{hiring_impact_section}

DOCUMENT ANALYSIS:
{f"Supporting Document Content: {document_content}" if document_content else "No supporting document provided."}

CONTENT REQUIREMENTS:
- Include SEO-friendly headings and subheadings (all in bold)
- Use proper {language_instruction} grammar and spelling
- Keywords to naturally incorporate: {keywords}
- Key facts to include: {facts}
- Quotes to incorporate: {quotes}

{'AI-FRIENDLY FORMATTING: Use H2 headings as questions, provide brief answers first, then elaborate with detailed explanations of at least 200 words per section.' if ai_opt else 'Use traditional blog formatting with descriptive headings.'}

FINAL REMINDER: 
- This article MUST be {min_words}-{max_words} words total
- Each section needs substantial content with examples and analysis
- Do not submit a brief article - it will not meet client requirements
- Count your words and ensure you meet the minimum before finalizing

Please generate a well-structured, informative, and COMPREHENSIVE blog article that meets ALL word count requirements.
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

# -------------- ARTICLE REVISION ----------------
def revise_article(original_article, revision_request, language="UK"):
    language_instruction = "UK English" if language == "UK" else "US English"
    
    prompt = f'''
Please revise the following blog article based on the specific request below.

ORIGINAL ARTICLE:
{original_article}

REVISION REQUEST:
{revision_request}

IMPORTANT GUIDELINES:
- Maintain the same {language_instruction} and style as the original
- Only make the requested changes
- Keep all other content intact unless the revision specifically requires broader changes
- Ensure the article remains coherent after revisions
- Do not add a conclusion section - maintain the forward-looking final section

Please provide the revised article with the requested changes implemented.
'''
    
    return call_claude(prompt)

# -------------- CONVERT MARKDOWN TO DOCX ----------------
def markdown_to_docx(content, title):
    """Convert markdown content to DOCX format matching the preview"""
    doc = Document()
    
    # Add title
    doc.add_heading(title, 0)
    
    # Process the content line by line
    lines = content.split('\n')
    current_paragraph = []
    
    for line in lines:
        line = line.strip()
        
        if not line:
            # Empty line - add accumulated paragraph if any
            if current_paragraph:
                doc.add_paragraph(' '.join(current_paragraph))
                current_paragraph = []
            continue
        
        # Check for headings with bold markers
        if line.startswith('**### ') and line.endswith('**'):
            if current_paragraph:
                doc.add_paragraph(' '.join(current_paragraph))
                current_paragraph = []
            heading_text = line[6:-2]  # Remove **### and **
            h = doc.add_heading(heading_text, level=3)
            h.runs[0].bold = True
        elif line.startswith('**## ') and line.endswith('**'):
            if current_paragraph:
                doc.add_paragraph(' '.join(current_paragraph))
                current_paragraph = []
            heading_text = line[5:-2]  # Remove **## and **
            h = doc.add_heading(heading_text, level=2)
            h.runs[0].bold = True
        elif line.startswith('**# ') and line.endswith('**'):
            if current_paragraph:
                doc.add_paragraph(' '.join(current_paragraph))
                current_paragraph = []
            heading_text = line[4:-2]  # Remove **# and **
            h = doc.add_heading(heading_text, level=1)
            h.runs[0].bold = True
        # Also check for headings without bold markers (fallback)
        elif line.startswith('### '):
            if current_paragraph:
                doc.add_paragraph(' '.join(current_paragraph))
                current_paragraph = []
            h = doc.add_heading(line[4:], level=3)
            h.runs[0].bold = True
        elif line.startswith('## '):
            if current_paragraph:
                doc.add_paragraph(' '.join(current_paragraph))
                current_paragraph = []
            h = doc.add_heading(line[3:], level=2)
            h.runs[0].bold = True
        elif line.startswith('# '):
            if current_paragraph:
                doc.add_paragraph(' '.join(current_paragraph))
                current_paragraph = []
            h = doc.add_heading(line[2:], level=1)
            h.runs[0].bold = True
        else:
            # Regular text - accumulate
            current_paragraph.append(line)
    
    # Add any remaining paragraph
    if current_paragraph:
        doc.add_paragraph(' '.join(current_paragraph))
    
    return doc

# -------------- EXPORT TO DOCX ----------------
def export_docx(title, article_uk, article_us, keywords, document_analysis=""):
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
    safe_title = safe_title.replace(' ', '_')
    
    os.makedirs("exports", exist_ok=True)
    filenames = {}
    
    # Create UK version
    if article_uk:
        doc_uk = markdown_to_docx(article_uk, f"{title} (UK English)")
        
        # Add metadata at the end
        doc_uk.add_paragraph("")
        doc_uk.add_paragraph("---")
        doc_uk.add_paragraph(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        doc_uk.add_paragraph(f"Word Count: {len(article_uk.split())}")
        doc_uk.add_paragraph(f"Keywords Used: {', '.join(keywords)}")
        doc_uk.add_paragraph(f"Language: UK English")
        if document_analysis:
            doc_uk.add_paragraph(f"Document Analysis: Yes")
        
        filename_uk = f"exports/{safe_title}_UK_{timestamp}.docx"
        doc_uk.save(filename_uk)
        filenames['UK'] = filename_uk
    
    # Create US version
    if article_us:
        doc_us = markdown_to_docx(article_us, f"{title} (US English)")
        
        # Add metadata at the end
        doc_us.add_paragraph("")
        doc_us.add_paragraph("---")
        doc_us.add_paragraph(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        doc_us.add_paragraph(f"Word Count: {len(article_us.split())}")
        doc_us.add_paragraph(f"Keywords Used: {', '.join(keywords)}")
        doc_us.add_paragraph(f"Language: US English")
        if document_analysis:
            doc_us.add_paragraph(f"Document Analysis: Yes")
        
        filename_us = f"exports/{safe_title}_US_{timestamp}.docx"
        doc_us.save(filename_us)
        filenames['US'] = filename_us
    
    return filenames

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
                    client_cfg, extra_keywords, document_content, "UK", word_count_range, include_hiring_section
                )
                article_uk = call_claude(full_prompt)
                if article_uk:
                    articles['UK'] = article_uk
        
        # Generate US version
        if generate_us:
            with st.spinner("Generating US English version..."):
                full_prompt, all_keywords = generate_prompt(
                    blog_title, pasted_facts, pasted_quotes, ai_friendly, 
                    client_cfg, extra_keywords, document_content, "US", word_count_range, include_hiring_section
                )
                article_us = call_claude(full_prompt)
                if article_us:
                    articles['US'] = article_us
        
        if articles:
            # Save to session state and history
            st.session_state.current_articles = articles
            st.session_state.current_keywords = all_keywords
            st.session_state.current_title = blog_title
            st.session_state.document_content = document_content
            
            # Update stats
            st.session_state.generation_stats['total_blogs'] += len(articles)
            total_words = sum(len(article.split()) for article in articles.values())
            st.session_state.generation_stats['total_words'] += total_words
            
            # Save to history
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            save_to_history(blog_title, articles, all_keywords, timestamp)

elif submitted:
    st.warning("Please enter a blog title before generating articles.")

# Display generated articles or loaded from history
if st.session_state.current_articles:
    articles = st.session_state.current_articles
    
    # Success message
    st.markdown("""
    <div class="success-message">
        <h4>Blog articles ready!</h4>
        <p>Review your content below. You can request revisions before downloading.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Revision section
    st.markdown("### Request Revisions")
    with st.container():
        revision_request = st.text_area(
            "What would you like to change?",
            placeholder="e.g., 'Make the introduction more engaging', 'Add more statistics in the second section', 'Change the tone to be more formal'",
            help="Describe specific changes you'd like to make to the article"
        )
        
        if revision_request:
            col1, col2 = st.columns(2)
            with col1:
                if 'UK' in articles and st.button("Revise UK Version", type="secondary"):
                    with st.spinner("Revising UK version..."):
                        revised_uk = revise_article(articles['UK'], revision_request, "UK")
                        if revised_uk:
                            st.session_state.current_articles['UK'] = revised_uk
                            st.success("UK version revised!")
                            st.rerun()
            
            with col2:
                if 'US' in articles and st.button("Revise US Version", type="secondary"):
                    with st.spinner("Revising US version..."):
                        revised_us = revise_article(articles['US'], revision_request, "US")
                        if revised_us:
                            st.session_state.current_articles['US'] = revised_us
                            st.success("US version revised!")
                            st.rerun()
    
    st.markdown("---")
    
    # Export files for download
    filenames = export_docx(
        st.session_state.get('current_title', 'Blog Article'),
        articles.get('UK', ''),
        articles.get('US', ''),
        st.session_state.get('current_keywords', []),
        st.session_state.get('document_content', '')
    )
    
    # Download buttons
    st.markdown("### Download Final Articles")
    download_col1, download_col2 = st.columns(2)
    
    with download_col1:
        if 'UK' in articles and 'UK' in filenames:
            st.download_button(
                "📥 Download UK Version",
                data=open(filenames['UK'], "rb").read(),
                file_name=os.path.basename(filenames['UK']),
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
    
    with download_col2:
        if 'US' in articles and 'US' in filenames:
            st.download_button(
                "📥 Download US Version",
                data=open(filenames['US'], "rb").read(),
                file_name=os.path.basename(filenames['US']),
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
            if show_keywords and 'current_keywords' in st.session_state:
                st.info(f"Keywords: {', '.join(st.session_state.current_keywords)}")
            st.markdown(articles['UK'])
        
        with tab2:
            if show_word_count:
                st.info(f"Word Count: {len(articles['US'].split())} words")
            if show_keywords and 'current_keywords' in st.session_state:
                st.info(f"Keywords: {', '.join(st.session_state.current_keywords)}")
            st.markdown(articles['US'])
    
    elif 'UK' in articles:
        if show_word_count:
            st.info(f"Word Count: {len(articles['UK'].split())} words")
        if show_keywords and 'current_keywords' in st.session_state:
            st.info(f"Keywords: {', '.join(st.session_state.current_keywords)}")
        st.markdown(articles['UK'])
    
    else:
        if show_word_count:
            st.info(f"Word Count: {len(articles['US'].split())} words")
        if show_keywords and 'current_keywords' in st.session_state:
            st.info(f"Keywords: {', '.join(st.session_state.current_keywords)}")
        st.markdown(articles['US'])

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 2rem; color: #6c757d; font-size: 0.9rem;">
    <p>Powered by Claude AI | Enhanced Blog Writing Tool | The Marketing Junction</p>
</div>
""", unsafe_allow_html=True)
