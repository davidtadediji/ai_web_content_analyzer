from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, HttpUrl
from logger import configured_logger
from main import SummaryGenerator, SummaryOutputStrategy, openai, MODEL, get_summary_user_prompt
from dotenv import load_dotenv
import os
from prompt import system_prompt_for_summary

load_dotenv()

app_name = os.getenv("APP_NAME")
router = APIRouter(
    prefix="/api",
    tags=[app_name],
    responses={404: {"description": "Not found"}},
)

# Define the expected JSON body schema
class Request(BaseModel):
    company_name: str
    url: HttpUrl
    openai_secret_key: str
    gpt_model: str


class APIStreamingOutputStrategy(SummaryOutputStrategy):
    async def handle_output(self, messages):
        """
        Streams output directly to the FastAPI client as it is being generated.

        Args:
            messages (list): The messages to send to OpenAI.

        Returns:
            StreamingResponse: A FastAPI StreamingResponse object.
        """
        try:
            # Initialize the OpenAI API stream using the environment variables set earlier
            response = openai.chat.completions.create(
                model=MODEL,  # This will be set dynamically based on the request
                messages=messages,
                stream=True,
            )

            async def stream_generator():
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content is not None:
                        content = chunk.choices[0].delta.content
                        yield content

            # Return the stream generator as a FastAPI StreamingResponse
            return StreamingResponse(stream_generator(), media_type="text/plain")

        except Exception as e:
            configured_logger.error(f"Error in APIStreamingOutputStrategy --> {str(e)}", exc_info=True)
            raise RuntimeError(f"Error in APIStreamingOutputStrategy --> {str(e)}")

@router.post("/analyze/")
async def generate_summary(
    request: Request, # Accept GPT model name from the request
):
    """
    Generate a summary for the given website URL and stream the result.
    Args:
        request (Request): JSON object with an "url" key.
    Returns:
        StreamingResponse: Streamed summary result.
    """
    try:
        # Set the OpenAI secret key and GPT model dynamically based on the request
        if request.openai_secret_key:
            os.environ["OPENAI_API_KEY"] = request.openai_secret_key
        if request.gpt_model:
            os.environ["MODEL"] = request.gpt_model

        website_url = request.url
        configured_logger.info("Received Website URL: %s", website_url)

        # Create the appropriate output strategy for streaming
        strategy = APIStreamingOutputStrategy()

        # Prepare the messages for the OpenAI API
        messages = [
            {"role": "system", "content": system_prompt_for_summary},
            {"role": "user", "content": get_summary_user_prompt(request.company_name, website_url)},
        ]

        # Use the strategy to generate the streamed response
        return await strategy.handle_output(messages)

    except Exception as e:
        # Handle errors gracefully
        configured_logger.error(f"Error generating summary --> {str(e)}")
        return JSONResponse(
            content={"error": f"Failed to generate summary: {str(e)}"},
            status_code=500,
        )
