# Web Content Analyzer  

A powerful tool designed to recursively scrape websites, extract relevant links, and generate structured content summaries or analyses tailored to customizable requirements.

---

## Features  

- **Recursive Web Scraping**  
  Crawl websites thoroughly, retrieving accessible links to ensure comprehensive analysis of web structures.  

- **Smart Link Filtering**  
  Automatically identify and prioritize key pages, such as "About Us" or "Careers," while excluding irrelevant content like terms and privacy policies.  

- **Automated Content Summarization**  
  Transform extracted information into detailed, well-structured content summaries or analyses based on defined prompts.  

- **Flexible Use Cases**  
  - Generate company overviews  
  - Perform market research  
  - Analyze user-relevant content for targeted applications  

- **Plug-and-Play Modular Design**  
  Easily integrate with other projects or extend functionality to suit unique workflows.  

---

## Installation  

Follow these steps to set up the tool locally:  

1. **Clone the Repository**  
   ```bash  
   git clone https://github.com/davidtadediji/web-content-analyzer.git  
   cd web-content-analyzer  


# API Documentation for `/api/analyze/`

## Overview

This API endpoint generates a summary for a given website URL using OpenAI's GPT models. It streams the summary back to the client as it is being generated, providing an efficient and real-time user experience.

---

## Endpoint: `/api/analyze/`

### Method: `POST`

### Request Body

The body of the request should be a JSON object containing the following fields:

| Field               | Type    | Description                                                                 |
|---------------------|---------|-----------------------------------------------------------------------------|
| `company_name`      | `string`| The name of the company for which the summary is being generated.           |
| `url`               | `string` (URL) | The URL of the website to analyze. Must be a valid URL.                      |
| `openai_secret_key` | `string`| The OpenAI API secret key used for authenticating requests.                  |
| `gpt_model`         | `string`| The GPT model name to use for generating the summary (e.g., `gpt-4`).       |

### Example Request Body:

```json
{
  "company_name": "Example Corp",
  "url": "https://example.com",
  "openai_secret_key": "your-openai-api-key",
  "gpt_model": "gpt-4"
}
