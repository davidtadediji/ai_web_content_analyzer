import json
import os
from abc import ABC
from io import StringIO
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
            configured_logger.info(
                f"Attempting to summarize web content for {COMPANY_NAME}: {URL}"
            )
            result = func(*args, **kwargs)
            configured_logger.info(
                f"Successfully summarized web content for {COMPANY_NAME}: {URL}"
            )
            return result
        except Exception as e:
            configured_logger.error(
                f"Error summarizing web content for {COMPANY_NAME}: {URL} --> Error: {e}"
            )
            raise

    return wrapper


import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


class Website:
    """
    A utility class to represent a Website that we have scraped, now with links.
    """

    def __init__(self, url, max_depth=1):
        self.url = url
        self.visited = []  # Track visited URLs
        self.links = []  # Store links
        self.title = "No title found"  # Default title
        self.text = ""  # Default text content
        self.max_depth = max_depth  # Maximum depth for recursion

        try:
            self.initialize(url)  # Fetch and parse the page
            self.scrape(url, 1)  # Start scraping at depth 1
        except Exception as e:
            print(f"Website initialization error: {e}")
            # Optionally, you can re-raise or handle differently
            raise

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

        print(depth, url)

        try:
            # Fetch the content of the page
            response = requests.get(url)
            response.raise_for_status()  # Raise an exception for bad responses (404, etc.)
            body = response.content
            soup = BeautifulSoup(body, "html.parser")

            # Extract all anchor tags (links)
            links = soup.find_all("a", href=True)  # Only find links with href attribute

            # Carefully process links
            processed_links = []
            for link in links:
                try:
                    # Get href as a string explicitly
                    href = link.get('href', '').strip()

                    # Skip empty or javascript links
                    if not href or href.startswith(('javascript:', '#')):
                        continue

                    # Ensure href is a full URL
                    if href.startswith(('http://', 'https://')):
                        full_url = href
                    else:
                        full_url = urljoin(url, href)

                    # Optional: Add some filtering criteria
                    if full_url not in processed_links and full_url not in self.visited:
                        processed_links.append(full_url)

                except Exception as link_error:
                    print(f"Error processing individual link {link}: {link_error}")
                    continue

            self.links.extend(processed_links)

            # Recursively scrape all links at the next depth level
            for link in processed_links:
                self.scrape(link, depth + 1)

        except requests.exceptions.RequestException as e:
            # Handle request exceptions (e.g., network issues, invalid URLs)
            print(f"Error requesting {url}: {e}")


    def get_contents(self):
        """
        Return the title and contents of the website as a formatted string.
        """
        try:
            # Ensure title and text are strings
            title = str(self.title) if self.title else "No Title"
            text = str(self.text) if self.text else "No Content"

            # Add extra debug information
            print(f"DEBUG: Webpage title: {title}")
            print(f"DEBUG: Webpage text length: {len(text)}")

            return f"Webpage Title:\n{title}\nWebpage Contents:\n{text}\n\n"
        except Exception as e:
            print(f"DEBUG: get_contents error: {e}")
            print(traceback.format_exc())
            return f"Error fetching webpage contents: {e}"

    def get_all_links(self):
        """
        Return all the links found on the website.
        """
        return self.links


def get_links_user_prompt(website):
    """Generate a user prompt with website links."""
    links_str = "\n".join(website.links) if website.links else "No links found"
    return f"Website URL: {website.url}\n\nLinks found:\n{links_str}"


def get_relevant_links(url):
    """
    Fetches relevant links from the given URL using the OpenAI API.
    """
    try:
        website = Website(url)

        # Log the links found
        print(f"DEBUG: Total links found: {len(website.links)}")
        configured_logger.info(f"Total links found: {len(website.links)}")

        response = openai.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt_for_relevant_links},
                {"role": "user", "content": get_links_user_prompt(website)},
            ],
            response_format={"type": "json_object"},
        )

        result = response.choices[0].message.content

        # Extensive logging
        print(f"DEBUG: Raw API response: {result}")
        configured_logger.info(f"Raw API response: {result}")

        try:
            parsed_links = json.loads(result)
            print(f"DEBUG: Parsed links: {parsed_links}")
            configured_logger.info(f"Parsed links: {parsed_links}")

            # Validate the structure
            if not isinstance(parsed_links, dict) or 'links' not in parsed_links:
                raise ValueError("Invalid links structure")

            return parsed_links

        except json.JSONDecodeError as json_err:
            print(f"DEBUG: JSON Parsing Error: {json_err}")
            configured_logger.error(f"JSON Parsing Error: {json_err}")
            raise
        except ValueError as val_err:
            print(f"DEBUG: Links Validation Error: {val_err}")
            configured_logger.error(f"Links Validation Error: {val_err}")
            raise

    except Exception as e:
        print(f"DEBUG: Error in get_relevant_links: {e}")
        print(traceback.format_exc())
        configured_logger.error(f"Error in get_relevant_links: {str(e)}")
        raise
import traceback


def get_content_from_relevant_links(url):
    """
    Fetches the content from the landing page and relevant links.
    """
    try:
        # Extra debug logging
        print("DEBUG: Entering get_content_from_relevant_links")
        configured_logger.info("DEBUG: Entering get_content_from_relevant_links")

        # Create result as a list for safe concatenation
        result = []

        # Fetch and log landing page contents
        try:
            landing_page = Website(url)
            print(f"DEBUG: Landing page title: {landing_page.title}")
            configured_logger.info(f"DEBUG: Landing page title: {landing_page.title}")

            landing_contents = landing_page.get_contents()
            result.append(str(landing_contents))
        except Exception as landing_page_error:
            print(f"DEBUG: Landing page error: {landing_page_error}")
            configured_logger.error(f"Landing page error: {landing_page_error}")
            result.append("Could not fetch landing page contents")

        # Debug relevant links
        try:
            links = get_relevant_links(url)
            print(f"DEBUG: Raw links: {links}")
            configured_logger.info(f"DEBUG: Raw links: {links}")
        except Exception as links_error:
            print(f"DEBUG: Links retrieval error: {links_error}")
            configured_logger.error(f"Links retrieval error: {links_error}")
            return "Could not retrieve relevant links"

        # Validate links structure
        if not isinstance(links, dict) or 'links' not in links:
            error_msg = f"Invalid links structure: {links}"
            print(f"DEBUG: {error_msg}")
            configured_logger.error(error_msg)
            return error_msg

        # Process each link
        for link in links.get('links', []):
            try:
                # Validate link structure
                if not isinstance(link, dict) or 'url' not in link:
                    print(f"DEBUG: Skipping invalid link: {link}")
                    configured_logger.warning(f"Skipping invalid link: {link}")
                    continue

                link_url = link['url']
                link_type = link.get('type', 'Unknown Type')

                print(f"DEBUG: Processing link: {link_url}")
                configured_logger.info(f"Processing link: {link_url}")

                # Fetch link contents
                link_website = Website(link_url)
                result.append(f"\n\n{str(link_type)}")
                result.append(str(link_website.get_contents()))

            except Exception as link_error:
                print(f"DEBUG: Link processing error: {link_error}")
                print(traceback.format_exc())
                configured_logger.error(f"Link processing error: {link_error}")
                configured_logger.error(traceback.format_exc())
                continue

        # Join and return results
        final_result = "\n".join(result)
        print(f"DEBUG: Final result length: {len(final_result)}")
        configured_logger.info(f"DEBUG: Final result length: {len(final_result)}")

        return final_result

    except Exception as e:
        print(f"DEBUG: Comprehensive error: {e}")
        print(traceback.format_exc())
        configured_logger.error(f"Comprehensive error: {e}")
        configured_logger.error(traceback.format_exc())
        raise

def get_summary_user_prompt(company_name, url):
    prompt = user_prompt_for_summary.format(
        company_name=company_name
    ) + get_content_from_relevant_links(url)
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
        try:
            # Attempt to send the request to OpenAI API
            response = openai.chat.completions.create(
                model=MODEL,
                messages=messages,
            )

            # Initialize rich console for dynamic output
            console = Console()

            result = response.choices[0].message.content
            console.print(Markdown(result))

        except Exception as e:
            # Log and raise an error with the updated message format
            error_message = f"Error in StandardOutputStrategy error --> {str(e)}"
            configured_logger.error(error_message)
            raise Exception(error_message)


class StreamingOutputStrategy(SummaryOutputStrategy):
    def handle_output(self, messages):
        try:
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

        except Exception as e:
            # Log and raise an error with the updated message format
            error_message = f"Error in StreamingOutputStrategy error --> {str(e)}"
            configured_logger.error(error_message)
            raise Exception(error_message)

from io import StringIO


class SummaryGenerator:
    def __init__(self, output_strategy: SummaryOutputStrategy):
        self.output_strategy = output_strategy

    @log_content_summarizer
    def create_summary(self, company_name, url):
        messages = [
            {"role": "system", "content": system_prompt_for_summary},
            {"role": "user", "content": get_summary_user_prompt(company_name, url)},
        ]

        self.output_strategy.handle_output(messages)


# SummaryGenerator(StandardOutputStrategy()).create_summary(COMPANY_NAME, URL)
