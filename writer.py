import streamlit as st
import yaml
import anthropic
import datetime
from docx import Document
import os

# -------------- CONFIG ----------------
ANTHROPIC_KEY = st.secrets["api_keys"]["anthropic_api_key"]

anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

def load_client_config(client_name):
    with open(f"clients/{client_name}.yaml", "r") as file:
        return yaml.safe_load(file)

# -------------- STREAMLIT UI ----------------
st.set_page_config(page_title="AI Blog Writer", layout="centered")
st.title("The Marketing Junction – AI Blog Writer")

with st.form("blog_form"):
    blog_title = st.text_input("Enter Blog Title:")
    client_name = st.selectbox("Client", ["marketing_junction"])
    pasted_facts = st.text_area("Paste any important facts or figures:")
    pasted_quotes = st.text_area("Paste any quotes or original thoughts:")
    ai_friendly = st.checkbox("Make AI Friendly (AEO Optimized)")
    submitted = st.form_submit_button("Generate Blog")

# -------------- CLAUDE PROMPT HELPER ----------------
def generate_prompt(title, facts, quotes, ai_opt, client_cfg):
    keywords = ", ".join(client_cfg.get("keywords", []))
    prompt = f'''
Write a blog article in UK English about: "{title}"

Audience: knowledgeable professionals.
Tone: {client_cfg.get("tone", "informative")}.
Perspective: Recruitment agency (don't mention this explicitly).
Avoid: Em/En dashes, phrases like 'in the world of', conclusions.

Include SEO-friendly headings and structure.
Keywords to use: {keywords}
Facts: {facts}
Quotes: {quotes}

{'Format for AI-Friendliness: use H2s as questions, give short answers first, then elaborate.' if ai_opt else ''}
Do not invent stats. You may create quotes but not fake events.
'''
    return prompt

# -------------- ARTICLE GENERATION ----------------
def call_claude(prompt):
    response = anthropic_client.messages.create(
        model = "claude-3-5-sonnet-20241022",
        max_tokens=1024*4,
        temperature=0.7,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return response.content[0].text

# -------------- EXPORT TO DOCX ----------------
def export_docx(title, article, keywords):
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph(f"Word Count: {len(article.split())}")
    doc.add_paragraph(f"Keywords Used: {', '.join(keywords)}")
    doc.add_paragraph("Language: UK English")
    doc.add_paragraph("")
    doc.add_paragraph(article)

    filename = f"exports/{title.replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d')}.docx"
    os.makedirs("exports", exist_ok=True)
    doc.save(filename)
    return filename

# -------------- MAIN EXECUTION ----------------
if submitted and blog_title:
    client_cfg = load_client_config(client_name)
    with st.spinner("Generating your blog with Claude..."):
        full_prompt = generate_prompt(blog_title, pasted_facts, pasted_quotes, ai_friendly, client_cfg)
        article = call_claude(full_prompt)
        filepath = export_docx(blog_title, article, client_cfg.get("keywords", []))

    st.success("✅ Blog generated!")
    st.download_button("Download DOCX", open(filepath, "rb"), file_name=os.path.basename(filepath))
    st.markdown("---")
    st.subheader("📄 Preview")
    st.write(article)

elif submitted:
    st.warning("Please enter a blog title before generating.")
