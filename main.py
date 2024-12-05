import json
import os
from abc import ABC
from urllib.parse import urljoin
import requests
from IPython.display import Markdown, display
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
from logger import configured_logger
from prompt import (
    user_prompt_for_relevant_links,
    system_prompt_for_summary,
    system_prompt_for_relevant_links,
    user_prompt_for_summary,
)

load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("MODEL")
COMPANY_NAME = os.getenv("COMPANY_NAME")
URL = os.getenv("WEBSITE_URL")

if API_KEY and API_KEY.startswith("sk-proj-") and len(API_KEY) > 10:
    configured_logger.info("API key looks good so far")
else:
    configured_logger.warning(
        "There might be a problem with your API key, it is not prefixed with 'sk-proj-'"
    )

openai = OpenAI()



def log_content_summarizer(func):

    def wrapper(*args, **kwargs):
        try:
            configured_logger.info(f"Attempting to summarize web content for {COMPANY_NAME}: {URL}")
            result = func(*args, **kwargs)
            configured_logger.info(f"Successfully summarized web content for {COMPANY_NAME}: {URL}")
            return result
        except Exception as e:
            configured_logger.error(f"Error summarizing web content for {COMPANY_NAME}: {URL} --> Error: {e}")

    return wrapper


class Website:
    """
    A utility class to represent a Website that we have scraped, now with links.
    """

    def __init__(self, url, max_depth=3):
        self.url = url
        self.visited = []  # Track visited URLs
        self.links = []  # Store links
        self.title = "No title found"  # Default title
        self.text = ""  # Default text content
        self.max_depth = max_depth  # Maximum depth for recursion
        self.initialize(url)  # Fetch and parse the page
        self.scrape(url, 1)  # Start scraping at depth 1

    def initialize(self, url):
        """
        Initializes the BeautifulSoup object, title, and text before scraping.
        """
        try:
            # Fetch the content of the page
            response = requests.get(url)
            response.raise_for_status()  # Raise an exception for bad responses (404, etc.)
            body = response.content
            soup = BeautifulSoup(body, "html.parser")

            # Extract the title of the page
            if soup.title:
                self.title = soup.title.string.strip()

            # Clean and extract text from the body (excluding irrelevant tags)
            if soup.body:
                for irrelevant in soup.body(["script", "style", "img", "input"]):
                    irrelevant.decompose()
                self.text = soup.body.get_text(separator="\n", strip=True)
            else:
                self.text = ""
        except requests.exceptions.RequestException as e:
            print(f"Error initializing {url}: {e}")

    def scrape(self, url, depth):
        """
        Scrapes the website, extracts links recursively up to the maximum depth.
        """
        # Avoid revisiting the same URL
        if url in self.visited:
            return

        # Mark the current URL as visited
        self.visited.append(url)

        # Stop recursion if maximum depth is reached
        if depth > self.max_depth:
            return

        try:
            # Fetch the content of the page
            response = requests.get(url)
            response.raise_for_status()  # Raise an exception for bad responses (404, etc.)
            body = response.content
            soup = BeautifulSoup(body, "html.parser")

            # Extract all anchor tags (links)
            links = [link.get("href") for link in soup.find_all("a", recursive=True)]
            self.links.extend(
                [urljoin(url, link) for link in links if link]
            )  # Add full URLs

            # Recursively scrape all links at the next depth level
            for link in self.links:
                self.scrape(link, depth + 1)

        except requests.exceptions.RequestException as e:
            # Handle request exceptions (e.g., network issues, invalid URLs)
            print(f"Error requesting {url}: {e}")

    def get_contents(self):
        """
        Return the title and contents of the website as a formatted string.
        """
        return f"Webpage Title:\n{self.title}\nWebpage Contents:\n{self.text}\n\n"

    def get_all_links(self):
        """
        Return all the links found on the website.
        """
        return self.links


def get_links_user_prompt(website):
    prompt = user_prompt_for_relevant_links.format(website_url=website.url)
    prompt += "\n".join(website.links)
    return prompt


def get_relevant_links(url):
    website = Website(url)
    response = openai.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt_for_relevant_links},
            {"role": "user", "content": get_links_user_prompt(website)},
        ],
        response_format={"type": "json_object"},
    )
    result = response.choices[0].message.content
    return json.loads(result)


def get_content_from_relevant_links(url):
    result = "Landing page:\n"
    result += Website(url).get_contents()
    links = get_relevant_links(url)
    configured_logger.info(f"Found relevant links: {str(links)} \n")
    for link in links["links"]:
        result += f"\n\n{link['type']}\n"
        result += Website(link["url"]).get_contents()
    return result


def get_summary_user_prompt(company_name, url):
    prompt = user_prompt_for_summary.format(company_name=company_name) + get_content_from_relevant_links(url)
    user_prompt = prompt[:20_000]  # Truncate if more than 20,000 characters
    return user_prompt


def generate_summary(company_name, url):
    response = openai.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt_for_summary},
            {"role": "user", "content": get_summary_user_prompt(company_name, url)},
        ],
    )
    result = response.choices[0].message.content
    display(Markdown(result))


class SummaryOutputStrategy(ABC):
    def handle_output(self, messages):
        raise NotImplementedError("Subclasses should implement this!")


class StandardOutputStrategy(SummaryOutputStrategy):
    def handle_output(self, messages):
        response = openai.chat.completions.create(
            model=MODEL,
            messages=messages,
        )

        # Initialize rich console for dynamic output
        console = Console()

        result = response.choices[0].message.content
        console.print(Markdown(result))

class StreamingOutputStrategy(SummaryOutputStrategy):
    def handle_output(self, messages):
        # Initialize the OpenAI API stream
        stream = openai.chat.completions.create(
            model=MODEL,
            messages=messages,
            stream=True,
        )

        # Initialize rich console for dynamic output
        console = Console()
        response = ""

        # Process the stream in chunks and display incrementally
        for chunk in stream:
            content = chunk.choices[0].delta.content or ""
            response += content

            response = str(response)

            # Clean markdown artifacts (if needed)
            response = response.replace("```", "").replace("markdown", "")

            # Display the output dynamically in the console using rich Markdown
            console.clear()  # Optional: Clears the screen to update in place
            console.print(Markdown(response))  # Print as rich markdown

        return response


class SummaryGenerator:
    def __init__(self, output_strategy: SummaryOutputStrategy):
        self.output_strategy = output_strategy

    # @log_content_summarizer
    def create_summary(self, company_name, url):
        messages = [
            {"role": "system", "content": system_prompt_for_summary},
            {"role": "user", "content": get_summary_user_prompt(company_name, url)},
        ]
        self.output_strategy.handle_output(messages)


SummaryGenerator(StandardOutputStrategy()).create_summary(
    COMPANY_NAME, URL)
