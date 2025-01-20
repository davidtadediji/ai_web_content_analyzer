system_prompt_for_relevant_links = """You are an assistant that analyzes the contents of several relevant pages from a company website \
and creates a short summary about the company for prospective customers, investors, and recruits. Respond in markdown. \
Include details of company culture, customers, and careers/jobs if you have the information.\
such as links to an About page, or a Company page, or Careers/Jobs pages.\n"""
system_prompt_for_relevant_links += """You should respond in JSON as in this example:"""
system_prompt_for_relevant_links += """
{
    "links": [
        {"type": "about page", "url": "https://full.url/goes/here/about"},
        {"type": "careers page": "url": "https://another.full.url/careers"}
    ]
}
"""

user_prompt_for_relevant_links = (
    """Here is the list of links on the website of {website_url} - """
)
user_prompt_for_relevant_links += """please decide which of these are relevant web links for a summary about the company, respond with the full https URL in JSON format. \
Do not include Terms of Service, Privacy, email links.\n"""
user_prompt_for_relevant_links += """Links (some might be relative links):\n"""


system_prompt_for_summary = "You are an assistant that analyzes the contents of several relevant pages from a company website \
and creates a summary about the company for prospective customers, investors and recruits. Respond in markdown.\
Include details of company culture, customers and careers/jobs if you have the information."

# Or uncomment the lines below for a more humorous summary - this demonstrates how easy it is to incorporate 'tone':

# system_prompt_for_analysis = "You are an assistant that analyzes the contents of several relevant pages from a company website \
# and creates a short humorous, entertaining, jokey summary about the company for prospective customers, investors and recruits. Respond in markdown.\
# Include details of company culture, customers and careers/jobs if you have the information."

user_prompt_for_summary = """You are looking at a company called: {company_name}\n"""
user_prompt_for_summary += """Here are the contents of its landing page and other relevant pages; use this information to build a summary of the company in markdown.\n"""
